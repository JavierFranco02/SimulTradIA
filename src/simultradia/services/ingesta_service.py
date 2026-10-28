"""Ingesta de datos de mercado: trae precios y velas de las fuentes y los guarda en la base.

Cada activo tiene una fuente (Binance, Yahoo Finance...) y cada fuente un cliente. Aquí se
agrupan los activos por fuente y se le pide a cada cliente lo suyo, con su propio ritmo: Binance
aguanta precios cada 2 s; Yahoo Finance, cada 30 s. Dos tareas las usa el worker (sin actor) y
dos son para el administrador (con actor). Si una fuente falla, las demás siguen.
"""
import logging
import time
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
from typing import Callable, Dict, List, Optional, Tuple

from simultradia.core.exceptions import ErrorAplicacion, ErrorOperacionInvalida
from simultradia.domain.entities.activo_entity import Activo
from simultradia.domain.reglas.intervalos import GUARDADOS, SEGUNDOS
from simultradia.services.permisos import exigir_admin

_log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResultadoIngesta:
    correctos: int = 0
    fallidos: List[str] = field(default_factory=list)   # "BTC/USDT" o "BTC/USDT 1h"


@dataclass(frozen=True)
class ResultadoPrueba:
    fuente: str
    ok: bool
    milisegundos: int
    mensaje: str


@dataclass(frozen=True)
class EstadoIngesta:
    activos_habilitados: int
    ultima_cotizacion: Optional[datetime]
    velas_por_intervalo: Dict[str, int]


class IngestaService:
    def __init__(self, db, activo_repository, precio_repository, fuente_repository,
                 clientes: Dict[str, object], reloj: Callable[[], float] = time.monotonic):
        self._db = db
        self._activos = activo_repository
        self._precios = precio_repository
        self._fuentes = fuente_repository
        self._clientes = clientes            # nombre de la fuente -> su cliente
        self._reloj = reloj
        self._ultima_vez: Dict[Tuple[str, str], float] = {}   # (tarea, fuente) -> cuándo se hizo

    # ------------------------------------------------- tareas del worker
    def actualizar_cotizaciones(self, forzar: bool = False, id_fuente: Optional[int] = None) -> ResultadoIngesta:
        correctos, fallidos = 0, []
        for nombre, cliente, activos in self._grupos("cotizaciones", "segundos_entre_cotizaciones", forzar, id_fuente):
            try:
                recibidas = cliente.obtener_cotizaciones([a.ticker for a in activos])
            except ErrorAplicacion as error:
                _log.warning("Sin cotizaciones de %s: %s", nombre, error)
                fallidos += [a.ticker for a in activos]
                continue
            with self._db.obtener_conexion() as conn:
                for activo in activos:
                    cotizacion = recibidas.get(activo.ticker)
                    if cotizacion is None:
                        fallidos.append(activo.ticker)
                    else:
                        self._precios.guardar_cotizacion(conn, replace(cotizacion, id_activo=activo.id_activo))
                        correctos += 1
        return ResultadoIngesta(correctos, fallidos)

    def actualizar_velas(self, forzar: bool = False, id_fuente: Optional[int] = None) -> ResultadoIngesta:
        """Descarga las velas que faltan de cada activo e intervalo guardado.

        Si ya hay velas, pide desde 2 periodos antes de la última (para refrescar la que estaba
        abierta). Si no hay ninguna, pide todo el historial configurado en GUARDADOS."""
        ahora = datetime.now(timezone.utc)
        correctos, fallidos = 0, []
        for nombre, cliente, activos in self._grupos("velas", "segundos_entre_velas", forzar, id_fuente):
            for activo in activos:
                for intervalo, dias in GUARDADOS.items():
                    try:
                        with self._db.obtener_conexion() as conn:
                            ultimo = self._precios.ultimo_momento(conn, activo.id_activo, intervalo)
                        desde = (ultimo - timedelta(seconds=2 * SEGUNDOS[intervalo]) if ultimo
                                 else ahora - timedelta(days=dias))
                        velas = cliente.obtener_velas(activo.ticker, intervalo, desde)
                        with self._db.obtener_conexion() as conn:
                            self._precios.reemplazar_velas(conn, activo.id_activo, intervalo, velas)
                        correctos += 1
                    except ErrorAplicacion as error:
                        _log.warning("No se pudieron actualizar las velas de %s %s: %s",
                                     activo.ticker, intervalo.value, error)
                        fallidos.append("%s %s" % (activo.ticker, intervalo.value))
        return ResultadoIngesta(correctos, fallidos)

    # ------------------------------------------------ para el administrador
    def obtener_estado(self, actor) -> EstadoIngesta:
        exigir_admin(actor)
        with self._db.obtener_conexion() as conn:
            return EstadoIngesta(
                activos_habilitados=len(self._activos.listar_activos(conn, solo_activos=True)),
                ultima_cotizacion=self._precios.ultima_actualizacion(conn),
                velas_por_intervalo=self._precios.contar_velas_por_intervalo(conn),
            )

    def ejecutar_manual(self, actor, id_fuente: Optional[int] = None) -> ResultadoIngesta:
        """Lo mismo que hace el worker, pero a pedido y sin esperar el ritmo de cada fuente.
        Con `id_fuente` actualiza solo los activos de esa fuente (que debe estar habilitada)."""
        exigir_admin(actor)
        cotizaciones = self.actualizar_cotizaciones(forzar=True, id_fuente=id_fuente)
        velas = self.actualizar_velas(forzar=True, id_fuente=id_fuente)
        return ResultadoIngesta(cotizaciones.correctos + velas.correctos,
                                cotizaciones.fallidos + velas.fallidos)

    def probar_fuente(self, actor, id_fuente: int) -> ResultadoPrueba:
        """Comprueba que la fuente responde: le pide el precio de un activo de ejemplo y mide cuánto
        tarda. No guarda nada. Un fallo de la fuente NO es un error: se devuelve como resultado."""
        exigir_admin(actor)
        with self._db.obtener_conexion() as conn:
            fuente = self._fuentes.buscar_por_id(conn, id_fuente)
        cliente = self._clientes.get(fuente.nombre) if fuente else None
        if fuente is None:
            raise ErrorOperacionInvalida("Esa fuente no existe.")
        if cliente is None:
            raise ErrorOperacionInvalida("La fuente %s todavía no está programada en la aplicación." % fuente.nombre)
        inicio = self._reloj()
        try:
            recibidas = cliente.obtener_cotizaciones([cliente.EJEMPLO_TICKER])
            ok = cliente.EJEMPLO_TICKER in recibidas
            mensaje = "Responde con datos." if ok else "Respondió, pero sin datos para %s." % cliente.EJEMPLO_TICKER
        except ErrorAplicacion as error:
            ok, mensaje = False, str(error)
        return ResultadoPrueba(fuente.nombre, ok, int((self._reloj() - inicio) * 1000), mensaje)

    # --------------------------------------------------------------- interno
    def _grupos(self, tarea: str, atributo_ritmo: str, forzar: bool,
                id_fuente: Optional[int] = None) -> List[Tuple[str, object, List[Activo]]]:
        """(fuente, cliente, activos) de las fuentes habilitadas a las que ya les toca esta tarea.
        Con `id_fuente` solo esa fuente (si no existe o está deshabilitada, es un error)."""
        with self._db.obtener_conexion() as conn:
            fuentes = self._fuentes.listar(conn)
            activos = self._activos.listar_activos(conn, solo_activos=True)
        if id_fuente is not None:
            fuentes = [f for f in fuentes if f.id_fuente == id_fuente]
            if not fuentes:
                raise ErrorOperacionInvalida("Esa fuente no existe.")
            if not fuentes[0].activa:
                raise ErrorOperacionInvalida("Esa fuente está deshabilitada: habilítala para actualizarla.")
        fuentes = [f for f in fuentes if f.activa]
        grupos = []
        for fuente in fuentes:
            cliente = self._clientes.get(fuente.nombre)
            propios = [a for a in activos if a.id_fuente == fuente.id_fuente]
            if cliente is None:
                if propios:
                    _log.warning("La fuente %r no tiene cliente programado: se ignora.", fuente.nombre)
                continue
            if not propios:
                continue
            clave, ahora = (tarea, fuente.nombre), self._reloj()
            if not forzar and ahora - self._ultima_vez.get(clave, float("-inf")) < getattr(cliente, atributo_ritmo):
                continue
            self._ultima_vez[clave] = ahora
            grupos.append((fuente.nombre, cliente, propios))
        return grupos
