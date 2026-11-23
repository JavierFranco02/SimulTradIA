"""Predicciones de volatilidad: generarlas cada día, evaluarlas al vencer y leerlas para las pantallas.

- GENERAR (worker): para el modelo ACTIVO y cada activo habilitado, UNA predicción por día con la última vela
  diaria CERRADA: el rango esperado de mañana, un intervalo de ~80 %, el nivel (baja/normal/alta) y los factores
  que más pesaron. También se guardan lo de hoy, lo «normal» y los umbrales, para evaluar con las mismas
  reglas. Un activo sin velas al día se omite (no se predice a ciegas).
- EVALUAR (worker): cuando existe la vela objetivo, mira su rango REAL, su nivel real y si el nivel se acertó.
- LEER (pantallas): el escáner, el historial, los factores y los resultados REALES en vivo.

Nada de aquí llama a APIs externas ni entrena: el entrenamiento está en `ModeloVolatilidadService`.
"""
import logging
import math
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Callable, List, Optional, Tuple

from simultradia.analisis.montecarlo import Proyeccion, proyectar as proyectar_precio
from simultradia.analisis.velas import velas_cerradas
from simultradia.analisis.volatilidad import INDICE_NORMAL, NOMBRES_FEATURES, calcular_features, rango_de, rangos
from simultradia.core.exceptions import ErrorOperacionInvalida
from simultradia.domain.entities.modelo_ia_entity import ModeloIA
from simultradia.domain.entities.prediccion_volatilidad_entity import (
    EstadoCiclo, Factor, PrecisionVivo, PrediccionVolatilidad, SenalVolatilidad)
from simultradia.domain.entities.usuario_entity import Usuario
from simultradia.domain.enums import IntervaloVela, TipoActivo, TipoModeloIA
from simultradia.domain.reglas.volatilidad import (
    VENTANA_NIVEL, dia_utc, fecha_objetivo, intervalo_80, nivel_de, umbrales_de)
from simultradia.ia.volatilidad import explicar, predecir
from simultradia.services.permisos import exigir_admin

_log = logging.getLogger(__name__)
_VELAS_A_LEER = 500                       # de sobra para las medias de hasta 120 velas
_ANTIGUEDAD_MAXIMA_CRIPTO = timedelta(days=2)   # la última vela cerrada debe ser la de ayer
_ANTIGUEDAD_MAXIMA = timedelta(days=5)          # lo demás: cubre fin de semana y algún feriado
_FACTORES = 5
_HISTORIAL = 30                         # predicciones pasadas que se muestran por activo
_DIAS_GRAFICO = 30                      # rangos recientes que dibuja la pestaña Volatilidad
_VELAS_PROYECCION = 300


@dataclass(frozen=True)
class ResultadoGeneracion:
    generadas: int = 0
    omitidas: int = 0         # activos sin velas al día o sin historia suficiente


@dataclass(frozen=True)
class ResumenVolatilidad:
    modelo: Optional[ModeloIA]            # None = no hay modelo activo
    senales: List[SenalVolatilidad]       # de más a menos agitado esperado (vs lo normal)
    precision: PrecisionVivo


@dataclass(frozen=True)
class DetalleActivoVolatilidad:
    vigente: Optional[PrediccionVolatilidad]   # la predicción de hoy (None si no hay)
    historial: List[PrediccionVolatilidad]     # de la más nueva a la más vieja
    rangos_recientes: List[float] = field(default_factory=list)   # rango de las últimas velas cerradas (la última es «hoy»)
    fechas_recientes: List[date] = field(default_factory=list)    # el día (UTC) de cada una de esas velas


class PrediccionVolatilidadService:
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
            modelos = self._modelos.listar_activos(conn, TipoModeloIA.VOLATILIDAD)
            if not modelos:
                return ResultadoGeneracion()
            activos = self._activos.listar_activos(conn)
            velas = {a.id_activo: self._precios.buscar_velas(conn, a.id_activo, IntervaloVela.D1, _VELAS_A_LEER)
                     for a in activos}
            hechas = {m.id_modelo: self._predicciones.objetivos_pendientes(conn, m.id_modelo)
                      for m in modelos}

        cargados = self._cargar_modelos(modelos)
        nuevas: List[PrediccionVolatilidad] = []
        omitidas = 0
        for activo in activos:
            cerradas = velas_cerradas(velas[activo.id_activo], ahora)
            if not cerradas or not self._al_dia(activo.tipo, cerradas[-1].momento, ahora):
                omitidas += 1
                continue
            fila = calcular_features(cerradas)[-1]
            umbrales = umbrales_de(rangos(cerradas)[-VENTANA_NIVEL:])
            if fila is None or umbrales is None:
                omitidas += 1
                continue
            objetivo = fecha_objetivo(cerradas[-1].momento, activo.tipo)
            if objetivo <= ahora:
                omitidas += 1                    # la vela objetivo ya habría cerrado: no es una predicción
                continue
            for modelo, entrenado in cargados:
                if (activo.id_activo, objetivo) in hechas[modelo.id_modelo]:
                    continue                     # ya hay una pendiente para esa misma vela objetivo
                try:
                    nuevas.append(self._predecir(activo, modelo, entrenado, cerradas[-1], fila, umbrales, ahora))
                except Exception:       # un activo o un modelo con problemas no frena a los demás
                    _log.exception("No se pudo predecir %s con el modelo %s", activo.ticker, modelo.nombre)

        if nuevas:
            with self._db.obtener_conexion() as conn:
                for prediccion in nuevas:
                    self._predicciones.insertar(conn, prediccion)
        return ResultadoGeneracion(generadas=len(nuevas), omitidas=omitidas)

    def evaluar_vencidas(self) -> int:
        """Completa las predicciones cuya vela objetivo ya cerró. Devuelve cuántas evaluó."""
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
            siguiente = len(al_predecir)                       # la vela que seguía a la de referencia
            if siguiente >= len(cerradas):
                continue                                       # esa vela todavía no cerró
            real = rango_de(cerradas[siguiente])
            nivel_real = nivel_de(real, p.umbral_bajo, p.umbral_alto)
            resultados.append((p.id_prediccion, real, nivel_real, nivel_real == p.nivel))
        if resultados:
            with self._db.obtener_conexion() as conn:
                for id_prediccion, real, nivel_real, acierto in resultados:
                    self._predicciones.registrar_resultado(conn, id_prediccion, real, nivel_real, acierto, ahora)
        return len(resultados)

    # ------------------------------------------------------------ lecturas de las pantallas
    def resumen(self) -> ResumenVolatilidad:
        """Lo que la pantalla necesita: el modelo activo, el escáner y los resultados reales."""
        ahora = self._ahora()
        with self._db.obtener_conexion() as conn:
            modelo = next(iter(self._modelos.listar_activos(conn, TipoModeloIA.VOLATILIDAD)), None)
            senales = self._predicciones.ultimas_por_activo(conn) if modelo else []
            precision = self._predicciones.precision(conn, ahora)
        return ResumenVolatilidad(modelo, sorted(senales, key=lambda s: -s.prediccion.veces_lo_normal), precision)

    def detalle(self, id_activo: int) -> DetalleActivoVolatilidad:
        """La predicción vigente de un activo y su historial (lo predicho contra lo ocurrido)."""
        with self._db.obtener_conexion() as conn:
            vigente = next((s.prediccion for s in self._predicciones.ultimas_por_activo(conn)
                            if s.prediccion.id_activo == id_activo), None)
            historial = self._predicciones.historial(conn, id_activo, _HISTORIAL)
            velas = self._precios.buscar_velas(conn, id_activo, IntervaloVela.D1, _VELAS_A_LEER)
        cerradas = velas_cerradas(velas, self._ahora())[-_DIAS_GRAFICO:]
        fechas = [dia_utc(v.momento) for v in cerradas]
        return DetalleActivoVolatilidad(vigente, historial, rangos(cerradas), fechas)

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
            if list(modelo.parametros.get("features", [])) != list(NOMBRES_FEATURES):
                _log.warning("El modelo %s %s se entrenó con otras features: se omite. Hay que reentrenarlo.",
                             modelo.nombre, modelo.version)
                continue
            try:
                cargados.append((modelo, self._almacen.cargar(modelo.ruta_artefacto)))
            except Exception:
                _log.exception("No se pudo cargar el modelo %s (%s)", modelo.nombre, modelo.ruta_artefacto)
        return cargados

    @staticmethod
    def _predecir(activo, modelo: ModeloIA, entrenado, vela, fila: List[float], umbrales,
                  ahora: datetime) -> PrediccionVolatilidad:
        rango = predecir(entrenado, fila)
        sigma = float(modelo.metricas.get("sigma", 0.0))
        bajo, alto = intervalo_80(rango, sigma)
        try:
            aportes = explicar(entrenado, fila, _FACTORES)
        except Exception:               # los factores son un extra: sin ellos la predicción igual vale
            _log.warning("No se pudieron calcular los factores de %s", activo.ticker, exc_info=True)
            aportes = []
        factores: List[Factor] = [(nombre, aporte, fila[NOMBRES_FEATURES.index(nombre)]) for nombre, aporte in aportes]
        return PrediccionVolatilidad(
            id_activo=activo.id_activo, id_modelo=modelo.id_modelo, generada_en=ahora,
            fecha_objetivo=fecha_objetivo(vela.momento, activo.tipo), precio_referencia=vela.cierre,
            rango_predicho=round(rango, 6), rango_bajo=round(bajo, 6), rango_alto=round(alto, 6),
            rango_hoy=round(math.exp(fila[0]), 6), rango_normal=round(math.exp(fila[INDICE_NORMAL]), 6),
            umbral_bajo=round(umbrales[0], 6), umbral_alto=round(umbrales[1], 6),
            nivel=nivel_de(rango, umbrales[0], umbrales[1]), factores=factores)
