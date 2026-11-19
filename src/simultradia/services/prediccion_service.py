"""Predicciones de dirección: generarlas cada día, evaluarlas al vencer y leerlas para las pantallas.

- GENERAR (worker): para cada modelo ACTIVO (uno por horizonte) y cada activo habilitado, UNA predicción por
  día con la última vela diaria CERRADA. Se guardan el precio de referencia (su cierre), la fecha en que se
  podrá evaluar y los factores que más pesaron. Un activo sin velas al día se omite (no se predice a ciegas).
- EVALUAR (worker): al vencer, mira qué pasó `horizonte` velas después de la de referencia y con el MISMO
  umbral del entrenamiento decide la dirección real y si se acertó. Espera a que exista esa vela.
- LEER (pantallas): el escáner, el historial, los factores y el acierto REAL en vivo.

Nada de aquí llama a APIs externas ni entrena: el entrenamiento está en `ModeloIAService`.
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, List, Optional, Tuple

from simultradia.analisis.montecarlo import Proyeccion, proyectar as proyectar_precio
from simultradia.analisis.features import NOMBRES_FEATURES, calcular_features, etiquetar, velas_cerradas
from simultradia.core.exceptions import ErrorOperacionInvalida
from simultradia.domain.entities.modelo_ia_entity import ModeloIA
from simultradia.domain.entities.prediccion_entity import EstadoCiclo, PrecisionVivo, Prediccion, SenalActivo
from simultradia.domain.entities.usuario_entity import Usuario
from simultradia.domain.enums import IntervaloVela, TipoActivo
from simultradia.domain.reglas.prediccion import ALCISTA, BAJISTA, DIRECCIONES, LATERAL, fecha_objetivo
from simultradia.ia.entrenamiento import explicar, predecir
from simultradia.services.permisos import exigir_admin

_log = logging.getLogger(__name__)
_VELAS_A_LEER = 500                       # de sobra para que EMA, RSI y ATR se asienten igual que al entrenar
_ANTIGUEDAD_MAXIMA_CRIPTO = timedelta(days=2)   # la última vela cerrada debe ser la de ayer
_ANTIGUEDAD_MAXIMA = timedelta(days=5)          # lo demás: cubre fin de semana y algún feriado
_FACTORES = 5
_HISTORIAL = 30                         # predicciones pasadas que se muestran por activo
_VELAS_PROYECCION = 300


@dataclass(frozen=True)
class ResultadoGeneracion:
    generadas: int = 0
    omitidas: int = 0         # activos sin velas al día o sin historia suficiente


@dataclass(frozen=True)
class ResumenIA:
    horizonte: int
    modelo: Optional[ModeloIA]            # None = ese horizonte no tiene modelo activo
    senales: List[SenalActivo]            # de mayor a menor confianza
    precision: PrecisionVivo


@dataclass(frozen=True)
class DetalleActivoIA:
    vigente: Optional[Prediccion]         # la predicción de hoy (None si no hay)
    factores: List[Tuple[str, float, Optional[float]]]
    historial: List[Prediccion]           # de la más nueva a la más vieja


class PrediccionService:
    def __init__(self, db, activo_repository, precio_repository, modelo_repository, prediccion_repository,
                 almacen, ahora: Callable[[], datetime] = lambda: datetime.now(timezone.utc)):
        self._db = db
        self._activos = activo_repository
        self._precios = precio_repository
        self._modelos = modelo_repository
        self._predicciones = prediccion_repository
        self._almacen = almacen
        self._ahora = ahora

    # ------------------------------------------------------------ tareas del worker
    def generar_predicciones(self) -> ResultadoGeneracion:
        ahora = self._ahora()
        with self._db.obtener_conexion() as conn:
            modelos = self._modelos.listar_activos(conn)
            if not modelos:
                return ResultadoGeneracion()
            activos = self._activos.listar_activos(conn)
            velas = {a.id_activo: self._precios.buscar_velas(conn, a.id_activo, IntervaloVela.D1, _VELAS_A_LEER)
                     for a in activos}
            hechas = {m.id_modelo: self._predicciones.activos_con_prediccion_de_hoy(conn, m.id_modelo, ahora)
                      for m in modelos}

        cargados = self._cargar_modelos(modelos)
        nuevas: List[Tuple[Prediccion, List[Tuple[str, float, Optional[float]]]]] = []
        omitidas = 0
        for activo in activos:
            cerradas = velas_cerradas(velas[activo.id_activo], ahora)
            if not cerradas or not self._al_dia(activo.tipo, cerradas[-1].momento, ahora):
                omitidas += 1
                continue
            fila = calcular_features(cerradas)[-1]
            if fila is None:
                omitidas += 1
                continue
            for modelo, entrenado in cargados:
                if activo.id_activo in hechas[modelo.id_modelo]:
                    continue
                try:
                    nuevas.append(self._predecir(activo, modelo, entrenado, cerradas[-1], fila, ahora))
                except Exception:       # un activo o un modelo con problemas no frena a los demás
                    _log.exception("No se pudo predecir %s con el modelo %s", activo.ticker, modelo.nombre)

        if nuevas:
            with self._db.obtener_conexion() as conn:
                for prediccion, factores in nuevas:
                    self._predicciones.insertar(conn, prediccion)
                    self._predicciones.insertar_explicaciones(conn, prediccion.id_prediccion, factores)
        return ResultadoGeneracion(generadas=len(nuevas), omitidas=omitidas)

    def evaluar_vencidas(self) -> int:
        """Completa las predicciones cuya fecha objetivo ya pasó. Devuelve cuántas evaluó."""
        ahora = self._ahora()
        with self._db.obtener_conexion() as conn:
            vencidas = self._predicciones.vencidas(conn, ahora)
            if not vencidas:
                return 0
            velas = {i: self._precios.buscar_velas(conn, i, IntervaloVela.D1, _VELAS_A_LEER)
                     for i in {p.id_activo for p in vencidas}}

        resultados = []
        for p in vencidas:
            todas = velas[p.id_activo]
            cerradas = velas_cerradas(todas, ahora)
            al_predecir = velas_cerradas(todas, p.generada_en)
            if not al_predecir:
                continue
            referencia = len(al_predecir) - 1                  # la vela con la que se predijo
            if referencia + p.horizonte_dias >= len(cerradas):
                continue                                       # la vela objetivo todavía no existe
            clase = etiquetar([float(v.cierre) for v in cerradas], p.horizonte_dias)[referencia]
            if clase is None:
                continue
            real = DIRECCIONES[clase]
            resultados.append((p.id_prediccion, cerradas[referencia + p.horizonte_dias].cierre, real,
                               real == p.direccion))
        if resultados:
            with self._db.obtener_conexion() as conn:
                for id_prediccion, precio, real, acierto in resultados:
                    self._predicciones.registrar_resultado(conn, id_prediccion, precio, real, acierto, ahora)
        return len(resultados)

    # ------------------------------------------------------------ lecturas de las pantallas
    def resumen(self, horizonte: int) -> "ResumenIA":
        """Lo que la pantalla necesita de un horizonte: su modelo activo, el escáner y el acierto real."""
        ahora = self._ahora()
        with self._db.obtener_conexion() as conn:
            modelo = next((m for m in self._modelos.listar_activos(conn) if m.horizonte_dias == horizonte), None)
            senales = self._predicciones.ultimas_por_activo(conn, horizonte) if modelo else []
            precision = self._predicciones.precision(conn, horizonte, ahora)
        return ResumenIA(horizonte, modelo, sorted(senales, key=lambda s: -s.prediccion.confianza), precision)

    def detalle(self, id_activo: int, horizonte: int) -> "DetalleActivoIA":
        """Los factores de la predicción vigente de un activo y su historial (lo predicho contra lo ocurrido)."""
        with self._db.obtener_conexion() as conn:
            vigente = next((s.prediccion for s in self._predicciones.ultimas_por_activo(conn, horizonte)
                            if s.prediccion.id_activo == id_activo), None)
            factores = self._predicciones.explicaciones(conn, vigente.id_prediccion) if vigente else []
            historial = self._predicciones.historial(conn, id_activo, horizonte, _HISTORIAL)
        return DetalleActivoIA(vigente, factores, historial)

    def estado_ciclo(self, actor: Usuario) -> EstadoCiclo:
        """Cómo va el ciclo de predicciones (administración)."""
        exigir_admin(actor)
        with self._db.obtener_conexion() as conn:
            return self._predicciones.estado_ciclo(conn, self._ahora())

    def proyectar(self, id_activo: int, dias: int, nivel: Optional[float] = None) -> Proyeccion:
        """Monte Carlo del precio del activo (dispersión posible, NO es la predicción de la IA)."""
        with self._db.obtener_conexion() as conn:
            velas = self._precios.buscar_velas(conn, id_activo, IntervaloVela.D1, _VELAS_PROYECCION)
            cotizado = self._activos.buscar_cotizado(conn, id_activo)
        cierres = [float(v.cierre) for v in velas_cerradas(velas, self._ahora())]
        actual = float(cotizado.cotizacion.precio) if cotizado and cotizado.cotizacion else None
        try:
            return proyectar_precio(cierres, dias, nivel=nivel, precio_actual=actual)
        except ValueError as error:
            raise ErrorOperacionInvalida("Todavía no hay suficientes velas diarias para proyectar.") from error

    # ------------------------------------------------------------ internos
    @staticmethod
    def _al_dia(tipo: TipoActivo, momento_ultima: datetime, ahora: datetime) -> bool:
        limite = _ANTIGUEDAD_MAXIMA_CRIPTO if tipo == TipoActivo.CRIPTO else _ANTIGUEDAD_MAXIMA
        return ahora - momento_ultima <= limite

    def _cargar_modelos(self, modelos: List[ModeloIA]) -> List[Tuple[ModeloIA, object]]:
        cargados = []
        for modelo in modelos:
            try:
                cargados.append((modelo, self._almacen.cargar(modelo.ruta_artefacto)))
            except Exception:
                _log.exception("No se pudo cargar el modelo %s (%s)", modelo.nombre, modelo.ruta_artefacto)
        return cargados

    @staticmethod
    def _predecir(activo, modelo: ModeloIA, entrenado, vela, fila: List[float],
                  ahora: datetime) -> Tuple[Prediccion, List[Tuple[str, float, Optional[float]]]]:
        alcista, lateral, bajista = predecir(entrenado, fila)
        por_clase = {BAJISTA: bajista, LATERAL: lateral, ALCISTA: alcista}
        clase = max(por_clase, key=por_clase.get)
        prediccion = Prediccion(
            id_activo=activo.id_activo, id_modelo=modelo.id_modelo, horizonte_dias=modelo.horizonte_dias,
            generada_en=ahora, fecha_objetivo=fecha_objetivo(vela.momento, modelo.horizonte_dias, activo.tipo),
            direccion=DIRECCIONES[clase], prob_alcista=round(alcista, 4), prob_bajista=round(bajista, 4),
            prob_lateral=round(lateral, 4), confianza=round(por_clase[clase], 4),
            precio_referencia=vela.cierre)
        try:
            aportes = explicar(entrenado, fila, clase, _FACTORES)
        except Exception:               # los factores son un extra: sin ellos la predicción igual vale
            _log.warning("No se pudieron calcular los factores de %s", activo.ticker, exc_info=True)
            aportes = []
        factores = [(nombre, aporte, fila[NOMBRES_FEATURES.index(nombre)]) for nombre, aporte in aportes]
        return prediccion, factores
