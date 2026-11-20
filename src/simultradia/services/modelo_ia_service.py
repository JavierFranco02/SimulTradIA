"""Administración de los modelos de IA: entrenar, ver las versiones y activar una.

Entrenar tarda (minutos): se llama desde un hilo. Se lee el historial en UNA conexión, se entrena SIN
conexión abierta y se guarda en otra. El horizonte (hoy solo 1 día, `HORIZONTES`) llega como dato.
Un modelo solo queda ACTIVO si supera la base en la validación (z >= Z_MINIMO); si no, se guarda como
ARCHIVADO con sus métricas, para poder verlas, y sigue activo el anterior (si lo había).
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional

from simultradia.analisis.features import NOMBRES_FEATURES, velas_cerradas
from simultradia.core.exceptions import ErrorAplicacion, ErrorOperacionInvalida
from simultradia.domain.entities.modelo_ia_entity import ModeloIA
from simultradia.domain.entities.usuario_entity import Usuario
from simultradia.domain.enums import EstadoModelo, EstadoProceso, IntervaloVela, TipoModeloIA
from simultradia.domain.reglas.prediccion import (
    FACTOR_UMBRAL, HORIZONTES, TRAMOS_VALIDACION, VENTANA_VOLATILIDAD)
from simultradia.ia.entrenamiento import (
    Evaluacion, armar_dataset, crear_modelo_lightgbm, crear_modelo_random_forest, entrenar, evaluar)
from simultradia.ia.serializacion import a_dict, desde_dict
from simultradia.services.permisos import exigir_admin

_log = logging.getLogger(__name__)
_VELAS_A_LEER = 4000        # todo el historial diario guardado (3 650 días)


@dataclass(frozen=True)
class ResultadoModelo:
    modelo: ModeloIA
    evaluacion: Evaluacion
    activado: bool


@dataclass(frozen=True)
class ComparacionAlgoritmo:
    algoritmo: str
    evaluacion: Evaluacion


class ModeloIAService:
    def __init__(self, db, activo_repository, precio_repository, modelo_repository, almacen,
                 crear_modelo: Callable[[], object] = crear_modelo_lightgbm,
                 ahora: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
                 algoritmos: Optional[Dict[str, Callable[[], object]]] = None):
        self._db = db
        self._activos = activo_repository
        self._precios = precio_repository
        self._modelos = modelo_repository
        self._almacen = almacen
        self._crear_modelo = crear_modelo
        self._ahora = ahora
        self._algoritmos = algoritmos or {"LightGBM": crear_modelo, "Random forest": crear_modelo_random_forest}

    def entrenar(self, actor: Usuario, horizonte: int) -> ResultadoModelo:
        exigir_admin(actor)
        if horizonte not in HORIZONTES:
            raise ErrorOperacionInvalida("El horizonte debe ser uno de: %s días." % ", ".join(map(str, HORIZONTES)))
        nombre = "direccion_%dd" % horizonte
        ahora = self._ahora()

        with self._db.obtener_conexion() as conn:
            velas: Dict[int, list] = {
                a.id_activo: self._precios.buscar_velas(conn, a.id_activo, IntervaloVela.D1, _VELAS_A_LEER)
                for a in self._activos.listar_activos(conn)}
            modelo = self._modelos.insertar(conn, ModeloIA(
                nombre=nombre, version=self._modelos.siguiente_version(conn, nombre),
                tipo=TipoModeloIA.DIRECCION, algoritmo="LightGBM", horizonte_dias=horizonte,
                estado=EstadoModelo.ENTRENANDO,
                parametros={"factor_umbral": FACTOR_UMBRAL, "ventana_volatilidad": VENTANA_VOLATILIDAD,
                            "tramos": TRAMOS_VALIDACION, "features": list(NOMBRES_FEATURES)}))
            id_entrenamiento = self._modelos.abrir_entrenamiento(conn, modelo.id_modelo, actor.id_usuario)

        try:     # sin conexión abierta: esto es lo que tarda
            dataset = armar_dataset({i: velas_cerradas(v, ahora) for i, v in velas.items()}, horizonte)
            resultado = entrenar(dataset, self._crear_modelo)
            ruta = self._almacen.guardar(resultado.modelo, modelo.id_modelo)
        except Exception as error:
            self._registrar_fallo(modelo.id_modelo, id_entrenamiento, error)
            if isinstance(error, ErrorAplicacion):
                raise
            raise ErrorOperacionInvalida("El entrenamiento falló. Revisa el registro de la aplicación.") from error

        evaluacion = resultado.evaluacion
        metricas = a_dict(evaluacion)
        activar = evaluacion.supera_base
        with self._db.obtener_conexion() as conn:
            self._modelos.completar(conn, modelo.id_modelo, EstadoModelo.ARCHIVADO, metricas, ruta, ahora)
            if activar:
                self._modelos.activar(conn, modelo.id_modelo)
            self._modelos.cerrar_entrenamiento(conn, id_entrenamiento, EstadoProceso.COMPLETADO, metricas, None)
        modelo.estado = EstadoModelo.ACTIVO if activar else EstadoModelo.ARCHIVADO
        modelo.metricas, modelo.ruta_artefacto, modelo.entrenado_en = metricas, ruta, ahora
        return ResultadoModelo(modelo, evaluacion, activar)

    def comparar(self, actor: Usuario, horizonte: int) -> List[ComparacionAlgoritmo]:
        """Valida cada algoritmo con el MISMO walk-forward y los mismos datos. No guarda ni activa nada."""
        exigir_admin(actor)
        if horizonte not in HORIZONTES:
            raise ErrorOperacionInvalida("El horizonte debe ser uno de: %s días." % ", ".join(map(str, HORIZONTES)))
        ahora = self._ahora()
        with self._db.obtener_conexion() as conn:
            velas = {a.id_activo: self._precios.buscar_velas(conn, a.id_activo, IntervaloVela.D1, _VELAS_A_LEER)
                     for a in self._activos.listar_activos(conn)}
        dataset = armar_dataset({i: velas_cerradas(v, ahora) for i, v in velas.items()}, horizonte)
        return [ComparacionAlgoritmo(nombre, evaluar(dataset, crear)) for nombre, crear in self._algoritmos.items()]

    def listar(self, actor: Usuario) -> List[ModeloIA]:
        exigir_admin(actor)
        with self._db.obtener_conexion() as conn:
            return self._modelos.listar(conn)

    def activar(self, actor: Usuario, id_modelo: int) -> None:
        """Vuelve a dejar activa una versión archivada (por ejemplo, para revertir)."""
        exigir_admin(actor)
        with self._db.obtener_conexion() as conn:
            modelo = self._modelos.buscar(conn, id_modelo)
            if modelo is None:
                raise ErrorOperacionInvalida("El modelo no existe.")
            if modelo.estado == EstadoModelo.ACTIVO:
                return
            if modelo.estado != EstadoModelo.ARCHIVADO or not modelo.ruta_artefacto or not modelo.metricas:
                raise ErrorOperacionInvalida("Ese modelo no terminó de entrenarse: no se puede activar.")
            if not desde_dict(modelo.metricas).supera_base:
                raise ErrorOperacionInvalida("Ese modelo no supera la base: no se puede activar.")
            self._modelos.activar(conn, id_modelo)

    def _registrar_fallo(self, id_modelo: int, id_entrenamiento: int, error: Exception) -> None:
        _log.error("Falló el entrenamiento del modelo %s: %r", id_modelo, error)
        try:
            with self._db.obtener_conexion() as conn:
                self._modelos.marcar_fallido(conn, id_modelo)
                self._modelos.cerrar_entrenamiento(conn, id_entrenamiento, EstadoProceso.FALLIDO, {}, str(error))
        except ErrorAplicacion:
            _log.exception("No se pudo registrar el fallo del entrenamiento")
