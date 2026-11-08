"""Casos de uso de Operar: órdenes a mercado y límite, stop-loss / take-profit, posiciones e historial.

- Orden a MERCADO: se ejecuta en el acto contra la cotización guardada (cotizaciones_actuales), dentro de
  UNA transacción que bloquea la cuenta: si algo falla, no queda nada a medias.
- Orden LÍMITE: queda PENDIENTE. El worker (`evaluar_pendientes`) la ejecuta cuando el precio llega al límite
  (la compra espera a que baje; la venta, a que suba). No reserva saldo: se comprueba al enviarla y otra vez
  al ejecutarla; si entonces ya no se puede, queda RECHAZADA con su motivo.
- STOP-LOSS / TAKE-PROFIT: son niveles de la POSICIÓN (no órdenes aparte). Cuando el precio los toca, el worker
  vende toda la posición. Se ponen al comprar o con `editar_proteccion`; si la posición se cierra, desaparecen.

`estimar` y `cantidad_para` no tocan la base: trabajan con el `ResumenOperar` ya leído, para que la pantalla
pueda mostrar el costo mientras el usuario escribe. El precio ya lo dejó el worker en la base: aquí no se llama
a ninguna API externa.

La cuenta opera en su moneda y no hay conversión: un activo que cotiza en otra moneda
(p. ej. USDJPY=X en JPY) todavía no se puede operar.
"""
import logging
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from decimal import ROUND_DOWN, Decimal, InvalidOperation
from typing import Callable, Dict, List, NamedTuple, Optional, Tuple

from simultradia.core.exceptions import DatosInvalidos, ErrorAplicacion, ErrorOperacionInvalida
from simultradia.domain.entities.cotizacion_entity import ActivoCotizado
from simultradia.domain.entities.cuenta_simulada_entity import CuentaSimulada
from simultradia.domain.entities.orden_entity import Ejecucion, Orden
from simultradia.domain.entities.posicion_entity import Posicion
from simultradia.domain.entities.usuario_entity import Usuario
from simultradia.domain.enums import EstadoOrden, LadoOrden, TipoOrden
from simultradia.domain.reglas.operaciones import (
    Estimacion, aplicar_compra, aplicar_venta, cantidad_maxima_compra, estimar_orden, limite_alcanzado,
    precio_de_ejecucion, proteccion_alcanzada, valorar_posicion)
from simultradia.services.permisos import exigir_operador
from simultradia.services.validacion import lanzar_si_hay_errores

_log = logging.getLogger(__name__)
_DECIMALES_CANTIDAD = Decimal(1).scaleb(-10)    # la base guarda 10 decimales de cantidad...
_DECIMALES_PRECIO = Decimal(1).scaleb(-8)       # ...y 8 de precio
_CANTIDAD_MAXIMA = Decimal(10) ** 12
_LIMITE_HISTORIAL = 50


def _ahora_utc() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class SolicitudOrden:
    """Lo que el usuario escribió en el ticket, tal cual (como texto)."""
    lado: LadoOrden
    tipo: TipoOrden
    cantidad: str
    precio_limite: str = ""
    stop_loss: str = ""
    take_profit: str = ""


@dataclass(frozen=True)
class ResultadoOrden:
    """O la orden se ejecutó ya (`ejecucion`) o quedó esperando su precio (`pendiente`)."""
    ejecucion: Optional[Ejecucion] = None
    pendiente: Optional[Orden] = None


@dataclass(frozen=True)
class ResumenOperar:
    """Lo que la pantalla Operar sabe del activo elegido y de la cuenta."""
    item: ActivoCotizado
    saldo_disponible: Decimal
    moneda: str
    comision_pct: Decimal
    deslizamiento_pct: Decimal
    posicion: Optional[Posicion]        # None si no tiene nada de ese activo
    ganancia: Optional[Decimal] = None      # ganancia NO realizada de esa posición (None sin posición o sin precio)
    ganancia_pct: Optional[Decimal] = None


@dataclass(frozen=True)
class PosicionValorada:
    """Una posición abierta con su valor y su ganancia NO realizada al precio de ahora."""
    posicion: Posicion
    ticker: str
    moneda: str
    precio_actual: Optional[Decimal]    # None si el activo aún no tiene precio
    valor: Optional[Decimal]
    ganancia: Optional[Decimal]
    ganancia_pct: Optional[Decimal]


@dataclass(frozen=True)
class EstadoOperar:
    """Todo lo que la pantalla refresca de una vez (una sola conexión a la base)."""
    resumen: Optional[ResumenOperar]    # None si no hay activo elegido
    posiciones: List[PosicionValorada]
    pendientes: List[Orden]
    historial: List[Orden]


@dataclass(frozen=True)
class ResultadoCierre:
    cerradas: int
    fallidas: List[str]                 # "BTC/USDT: motivo"


@dataclass(frozen=True)
class ResultadoEvaluacion:
    ejecutadas: int = 0
    rechazadas: int = 0


class _Preparada(NamedTuple):
    cantidad: Decimal
    limite: Optional[Decimal]
    stop_loss: Optional[Decimal]
    take_profit: Optional[Decimal]
    estimacion: Estimacion


class OperarService:
    def __init__(self, db, cuenta_repository, posicion_repository, orden_repository, activo_repository,
                 reloj: Callable[[], datetime] = _ahora_utc):
        self._db = db
        self._cuentas = cuenta_repository
        self._posiciones = posicion_repository
        self._ordenes = orden_repository
        self._activos = activo_repository
        self._reloj = reloj

    # ------------------------------------------------------------- consultas
    def obtener_estado(self, actor: Usuario, id_activo: Optional[int]) -> EstadoOperar:
        """Resumen del activo elegido, posiciones, órdenes pendientes e historial, en una sola consulta."""
        exigir_operador(actor)
        with self._db.obtener_conexion() as conn:
            cuenta = self._cuenta_de(conn, actor)
            try:
                resumen = None if id_activo is None else self._leer_resumen(conn, cuenta, id_activo)
            except ErrorOperacionInvalida:      # el activo elegido ya no está disponible: no se rompe todo el panel
                resumen = None
            posiciones = self._leer_posiciones(conn, cuenta)
            pendientes = self._ordenes.listar_pendientes(conn, cuenta.id_cuenta)
            historial = self._ordenes.listar_ordenes(conn, cuenta.id_cuenta, _LIMITE_HISTORIAL)
        return EstadoOperar(resumen, posiciones, pendientes, historial)

    def obtener_resumen(self, actor: Usuario, id_activo: int) -> ResumenOperar:
        exigir_operador(actor)
        with self._db.obtener_conexion() as conn:
            return self._leer_resumen(conn, self._cuenta_de(conn, actor), id_activo)

    def listar_posiciones(self, actor: Usuario) -> List[PosicionValorada]:
        """Las posiciones abiertas con su ganancia no realizada, de la más antigua a la más nueva."""
        exigir_operador(actor)
        with self._db.obtener_conexion() as conn:
            return self._leer_posiciones(conn, self._cuenta_de(conn, actor))

    def listar_historial(self, actor: Usuario, limite: int = _LIMITE_HISTORIAL) -> List[Orden]:
        """Las últimas órdenes ya resueltas (ejecutadas, rechazadas, canceladas), de la más nueva a la más vieja."""
        exigir_operador(actor)
        with self._db.obtener_conexion() as conn:
            cuenta = self._cuenta_de(conn, actor)
            return self._ordenes.listar_ordenes(conn, cuenta.id_cuenta, limite)

    # ------------------------------------------- cálculos para la pantalla (sin BD)
    def estimar(self, resumen: ResumenOperar, solicitud: SolicitudOrden) -> Estimacion:
        """Lo que costaría o dejaría la orden. Lanza el mismo error que daría al enviarla."""
        return self._preparar(resumen.item, resumen, resumen.posicion, solicitud, self._reloj()).estimacion

    def cantidad_para(self, resumen: ResumenOperar, solicitud: SolicitudOrden, porcentaje: int) -> Decimal:
        """El `porcentaje` (1 a 100) de lo máximo que se puede comprar con el saldo, o de lo que se tiene al vender.
        En una compra límite se calcula al precio límite escrito (si lo hay)."""
        self._exigir_operable(resumen.item, resumen.moneda)
        if solicitud.lado == LadoOrden.COMPRA:
            precio = self._limite_si_es_valido(solicitud) or precio_de_ejecucion(
                resumen.item.cotizacion.precio, LadoOrden.COMPRA, resumen.deslizamiento_pct)
            maxima = cantidad_maxima_compra(resumen.saldo_disponible, precio, resumen.comision_pct)
            vacio = "No tienes saldo suficiente para comprar."
        else:
            maxima = resumen.posicion.cantidad if resumen.posicion else Decimal(0)
            vacio = "No tienes este activo para vender."
        cantidad = (maxima * porcentaje / 100).quantize(_DECIMALES_CANTIDAD, rounding=ROUND_DOWN)
        if cantidad <= 0:
            raise ErrorOperacionInvalida(vacio)
        return cantidad

    # ---------------------------------------------------------------- órdenes
    def enviar(self, actor: Usuario, id_activo: int, solicitud: SolicitudOrden) -> ResultadoOrden:
        """Envía una orden: a mercado se ejecuta ya; límite queda pendiente hasta que el precio llegue."""
        exigir_operador(actor)
        ahora = self._reloj()
        with self._db.obtener_conexion() as conn:
            cuenta = self._cuenta_de(conn, actor, bloquear=True)
            item = self._buscar_activo(conn, id_activo)
            posicion = self._posiciones.buscar(conn, cuenta.id_cuenta, id_activo)
            p = self._preparar(item, cuenta, posicion, solicitud, ahora)
            if p.limite is None:
                return ResultadoOrden(ejecucion=self._ejecutar(
                    conn, cuenta, item, posicion, solicitud.lado, p.cantidad, TipoOrden.MERCADO, ahora,
                    p.stop_loss, p.take_profit))
            orden = self._ordenes.insertar_orden(conn, Orden(
                id_cuenta=cuenta.id_cuenta, id_activo=id_activo, lado=solicitud.lado, tipo=TipoOrden.LIMITE,
                estado=EstadoOrden.PENDIENTE, cantidad=p.cantidad, precio_limite=p.limite,
                stop_loss=p.stop_loss, take_profit=p.take_profit))
            orden.ticker = item.activo.ticker
            return ResultadoOrden(pendiente=orden)

    def comprar(self, actor: Usuario, id_activo: int, cantidad: str) -> Ejecucion:
        """Atajo: compra a mercado. `cantidad` llega como texto, tal como se escribe."""
        return self.enviar(actor, id_activo, SolicitudOrden(LadoOrden.COMPRA, TipoOrden.MERCADO, cantidad)).ejecucion

    def vender(self, actor: Usuario, id_activo: int, cantidad: str) -> Ejecucion:
        """Atajo: venta a mercado."""
        return self.enviar(actor, id_activo, SolicitudOrden(LadoOrden.VENTA, TipoOrden.MERCADO, cantidad)).ejecucion

    def vender_todo(self, actor: Usuario, id_activo: int) -> Ejecucion:
        """Cierra la posición de un activo: vende todo lo que se tiene, a mercado."""
        exigir_operador(actor)
        ahora = self._reloj()
        with self._db.obtener_conexion() as conn:
            cuenta = self._cuenta_de(conn, actor, bloquear=True)
            item = self._buscar_activo(conn, id_activo)
            posicion = self._posiciones.buscar(conn, cuenta.id_cuenta, id_activo)
            if posicion is None:
                raise ErrorOperacionInvalida("No tienes este activo para vender.")
            return self._ejecutar(conn, cuenta, item, posicion, LadoOrden.VENTA, posicion.cantidad,
                                  TipoOrden.MERCADO, ahora)

    def cerrar_todas(self, actor: Usuario) -> ResultadoCierre:
        """Cierra todas las posiciones, una por una. Si alguna no se puede cerrar, las demás siguen."""
        cerradas, fallidas = 0, []
        for valorada in self.listar_posiciones(actor):
            try:
                self.vender_todo(actor, valorada.posicion.id_activo)
                cerradas += 1
            except ErrorAplicacion as error:
                fallidas.append("%s: %s" % (valorada.ticker, error))
        return ResultadoCierre(cerradas, fallidas)

    def cancelar_orden(self, actor: Usuario, id_orden: int) -> None:
        """Cancela una orden pendiente (solo si es de la cuenta del usuario)."""
        exigir_operador(actor)
        ahora = self._reloj()
        with self._db.obtener_conexion() as conn:
            cuenta = self._cuenta_de(conn, actor, bloquear=True)     # primero la cuenta: mismo orden que el worker
            orden = self._ordenes.buscar(conn, id_orden, bloquear=True)
            if orden is None or orden.id_cuenta != cuenta.id_cuenta:
                raise ErrorOperacionInvalida("Esa orden no existe.")
            if not self._ordenes.cancelar(conn, id_orden, ahora):
                raise ErrorOperacionInvalida("Esa orden ya no está pendiente.")

    def editar_proteccion(self, actor: Usuario, id_activo: int, stop_loss: str, take_profit: str) -> None:
        """Pone, cambia o quita (texto vacío) el stop-loss y el take-profit de una posición."""
        exigir_operador(actor)
        nuevo_sl = self._a_decimal(stop_loss, "stop_loss", "stop-loss")
        nuevo_tp = self._a_decimal(take_profit, "take_profit", "take-profit")
        with self._db.obtener_conexion() as conn:
            cuenta = self._cuenta_de(conn, actor, bloquear=True)
            item = self._buscar_activo(conn, id_activo)
            posicion = self._posiciones.buscar(conn, cuenta.id_cuenta, id_activo)
            if posicion is None:
                raise ErrorOperacionInvalida("No tienes este activo.")
            if item.cotizacion is None:
                raise ErrorOperacionInvalida("Ese activo todavía no tiene precio.")
            precio = item.cotizacion.precio
            lanzar_si_hay_errores({
                "stop_loss": ("El stop-loss debe estar por debajo del precio actual."
                              if nuevo_sl is not None and nuevo_sl >= precio else None),
                "take_profit": ("El take-profit debe estar por encima del precio actual."
                                if nuevo_tp is not None and nuevo_tp <= precio else None),
            })
            self._posiciones.actualizar(conn, replace(posicion, stop_loss=nuevo_sl, take_profit=nuevo_tp))

    # ------------------------------------------------------- para el worker (sin actor)
    def evaluar_pendientes(self) -> ResultadoEvaluacion:
        """Ejecuta las órdenes límite cuyo precio ya llegó y vende las posiciones cuyo stop-loss o
        take-profit se disparó. Cada una va en su propia transacción: si una falla, las demás siguen."""
        with self._db.obtener_conexion() as conn:
            pendientes = self._ordenes.listar_pendientes_todas(conn)
            protegidas = self._posiciones.listar_protegidas(conn)
            precios = {i.activo.id_activo: i.cotizacion.precio
                       for i in self._activos.listar_cotizados(conn, solo_activos=True) if i.cotizacion}
        ejecutadas = rechazadas = 0
        for orden in pendientes:
            precio = precios.get(orden.id_activo)
            if precio is not None and limite_alcanzado(orden.lado, orden.precio_limite, precio):
                hechas, rechazos = self._ejecutar_pendiente(orden)
                ejecutadas, rechazadas = ejecutadas + hechas, rechazadas + rechazos
        for posicion in protegidas:
            precio = precios.get(posicion.id_activo)
            if precio is not None and proteccion_alcanzada(posicion.stop_loss, posicion.take_profit, precio):
                ejecutadas += self._ejecutar_proteccion(posicion)
        return ResultadoEvaluacion(ejecutadas, rechazadas)

    # --------------------------------------------------------------- interno
    def _ejecutar_pendiente(self, listada: Orden) -> Tuple[int, int]:
        """(ejecutadas, rechazadas) tras intentar ejecutar una orden límite cuyo precio llegó."""
        ahora = self._reloj()
        with self._db.obtener_conexion() as conn:
            cuenta = self._cuentas.buscar_por_id(conn, listada.id_cuenta, bloquear=True)
            orden = self._ordenes.buscar(conn, listada.id_orden, bloquear=True)
            if cuenta is None or orden is None or orden.estado != EstadoOrden.PENDIENTE:
                return 0, 0       # el usuario la canceló mientras tanto
            item = self._activos.buscar_cotizado(conn, orden.id_activo)
            if item is None or not item.activo.activo or item.cotizacion is None:
                return 0, 0
            if not limite_alcanzado(orden.lado, orden.precio_limite, item.cotizacion.precio):
                return 0, 0       # el precio ya se movió
            posicion = self._posiciones.buscar(conn, cuenta.id_cuenta, orden.id_activo)
            try:
                self._ejecutar(conn, cuenta, item, posicion, orden.lado, orden.cantidad, orden.tipo, ahora,
                               orden.stop_loss, orden.take_profit, id_orden=orden.id_orden)
            except ErrorOperacionInvalida as error:
                # Todas las validaciones ocurren ANTES de escribir nada: no hay nada que deshacer.
                self._ordenes.marcar_rechazada(conn, orden.id_orden, str(error))
                return 0, 1
            return 1, 0

    def _ejecutar_proteccion(self, listada: Posicion) -> int:
        """1 si se vendió la posición porque su stop-loss o take-profit se disparó."""
        ahora = self._reloj()
        with self._db.obtener_conexion() as conn:
            cuenta = self._cuentas.buscar_por_id(conn, listada.id_cuenta, bloquear=True)
            posicion = self._posiciones.buscar(conn, listada.id_cuenta, listada.id_activo)
            item = self._activos.buscar_cotizado(conn, listada.id_activo)
            if cuenta is None or posicion is None or item is None or item.cotizacion is None:
                return 0
            tipo = proteccion_alcanzada(posicion.stop_loss, posicion.take_profit, item.cotizacion.precio)
            if tipo is None:
                return 0          # la editaron mientras tanto
            try:
                self._ejecutar(conn, cuenta, item, posicion, LadoOrden.VENTA, posicion.cantidad, tipo, ahora)
            except ErrorOperacionInvalida as error:
                _log.warning("No se pudo ejecutar el %s de %s: %s", tipo.value, item.activo.ticker, error)
                return 0
            return 1

    def _ejecutar(self, conn, cuenta: CuentaSimulada, item: ActivoCotizado, posicion: Optional[Posicion],
                  lado: LadoOrden, cantidad: Decimal, tipo: TipoOrden, ahora: datetime,
                  stop_loss: Optional[Decimal] = None, take_profit: Optional[Decimal] = None,
                  id_orden: Optional[int] = None) -> Ejecucion:
        """Ejecuta ya, al precio de mercado: valida, mueve saldo y posición y deja constancia.
        `id_orden` es la orden pendiente que se está cumpliendo (si no, se crea una nueva ya ejecutada).
        El deslizamiento solo afecta lo que se ejecuta "a lo que haya" (mercado y stop-loss), no las órdenes
        con precio fijado (límite y take-profit)."""
        deslizamiento = Decimal(0) if tipo in (TipoOrden.LIMITE, TipoOrden.TAKE_PROFIT) else cuenta.deslizamiento_pct
        estimacion = self._estimar(item, cuenta, posicion, lado, cantidad, ahora, deslizamiento=deslizamiento)
        if lado == LadoOrden.COMPRA:
            self._comprar(conn, cuenta, posicion, item.activo.id_activo, cantidad, estimacion, ahora,
                          stop_loss, take_profit)
        else:
            self._vender(conn, cuenta, posicion, cantidad, estimacion, ahora)
        return self._registrar(conn, cuenta, item, lado, tipo, cantidad, estimacion, ahora, id_orden)

    def _preparar(self, item: ActivoCotizado, cuenta, posicion: Optional[Posicion], s: SolicitudOrden,
                  ahora: datetime) -> _Preparada:
        """Valida lo escrito en el ticket y calcula la orden. `cuenta` es la cuenta o el resumen: ambos traen
        saldo_disponible, moneda, comision_pct y deslizamiento_pct."""
        cantidad = self._leer_cantidad(s.cantidad)
        limite = self._leer_limite(s)
        self._exigir_operable(item, cuenta.moneda)
        mercado = item.cotizacion.precio
        if limite is not None:
            if s.lado == LadoOrden.COMPRA and limite >= mercado:
                raise DatosInvalidos({"precio_limite": "Un límite de compra debe estar por debajo del precio actual. "
                                                       "Si quieres comprar ya, usa una orden a mercado."})
            if s.lado == LadoOrden.VENTA and limite <= mercado:
                raise DatosInvalidos({"precio_limite": "Un límite de venta debe estar por encima del precio actual. "
                                                       "Si quieres vender ya, usa una orden a mercado."})
        estimacion = self._estimar(item, cuenta, posicion, s.lado, cantidad, ahora,
                                   precio_base=limite if limite is not None else mercado,
                                   deslizamiento=Decimal(0) if limite is not None else cuenta.deslizamiento_pct)
        stop_loss, take_profit = self._leer_niveles(s, estimacion.precio)
        return _Preparada(cantidad, limite, stop_loss, take_profit, estimacion)

    def _estimar(self, item: ActivoCotizado, cuenta, posicion: Optional[Posicion], lado: LadoOrden,
                 cantidad: Decimal, ahora: datetime, precio_base: Optional[Decimal] = None,
                 deslizamiento: Optional[Decimal] = None) -> Estimacion:
        """Valida (activo operable, saldo, cantidad en posición) y calcula una orden. Sin `precio_base` se usa el
        de mercado; sin `deslizamiento`, el de la cuenta."""
        self._exigir_operable(item, cuenta.moneda)
        if lado == LadoOrden.VENTA and (posicion is None or posicion.cantidad < cantidad):
            raise ErrorOperacionInvalida("No tienes tanta cantidad de este activo para vender.")
        estimacion = estimar_orden(
            lado, cantidad, item.cotizacion.precio if precio_base is None else precio_base,
            cuenta.saldo_disponible, posicion, cuenta.comision_pct,
            cuenta.deslizamiento_pct if deslizamiento is None else deslizamiento, ahora)
        if lado == LadoOrden.COMPRA and estimacion.saldo_despues < 0:
            raise ErrorOperacionInvalida("Saldo insuficiente para esta compra (incluye la comisión).")
        return estimacion

    def _comprar(self, conn, cuenta: CuentaSimulada, posicion: Optional[Posicion], id_activo: int,
                 cantidad: Decimal, estimacion: Estimacion, ahora: datetime,
                 stop_loss: Optional[Decimal], take_profit: Optional[Decimal]) -> None:
        base = posicion or Posicion(cuenta.id_cuenta, id_activo, Decimal(0), Decimal(0), abierta_en=ahora)
        nueva = aplicar_compra(base, cantidad, estimacion.precio, estimacion.comision)
        if stop_loss is not None:         # sin niveles nuevos se conservan los que ya tenía la posición
            nueva = replace(nueva, stop_loss=stop_loss)
        if take_profit is not None:
            nueva = replace(nueva, take_profit=take_profit)
        if posicion is None:
            self._posiciones.insertar(conn, nueva)
        else:
            self._posiciones.actualizar(conn, nueva)
        self._cuentas.actualizar_saldo(conn, cuenta.id_cuenta, estimacion.saldo_despues)

    def _vender(self, conn, cuenta: CuentaSimulada, posicion: Posicion, cantidad: Decimal,
                estimacion: Estimacion, ahora: datetime) -> None:
        resultado = aplicar_venta(posicion, cantidad, estimacion.precio, cuenta.comision_pct, ahora)
        if resultado.posicion is None:
            self._posiciones.borrar(conn, posicion.id_posicion)
        else:
            self._posiciones.actualizar(conn, resultado.posicion)
        self._posiciones.insertar_operacion_cerrada(conn, resultado.operacion)
        self._cuentas.actualizar_saldo(conn, cuenta.id_cuenta, estimacion.saldo_despues)

    def _registrar(self, conn, cuenta: CuentaSimulada, item: ActivoCotizado, lado: LadoOrden, tipo: TipoOrden,
                   cantidad: Decimal, estimacion: Estimacion, ahora: datetime,
                   id_orden: Optional[int]) -> Ejecucion:
        """Deja constancia: la orden (ya ejecutada) y su ejecución."""
        id_activo = item.activo.id_activo
        if id_orden is None:
            id_orden = self._ordenes.insertar_orden(conn, Orden(
                id_cuenta=cuenta.id_cuenta, id_activo=id_activo, lado=lado, tipo=tipo,
                estado=EstadoOrden.EJECUTADA, cantidad=cantidad, precio_promedio=estimacion.precio,
                comision_total=estimacion.comision, ejecutada_en=ahora)).id_orden
        else:
            self._ordenes.marcar_ejecutada(conn, id_orden, estimacion.precio, estimacion.comision, ahora)
        return self._ordenes.insertar_ejecucion(conn, Ejecucion(
            id_orden=id_orden, id_cuenta=cuenta.id_cuenta, id_activo=id_activo, lado=lado,
            cantidad=cantidad, precio=estimacion.precio, comision=estimacion.comision,
            ejecutada_en=ahora, ticker=item.activo.ticker))

    def _leer_resumen(self, conn, cuenta: CuentaSimulada, id_activo: int) -> ResumenOperar:
        item = self._buscar_activo(conn, id_activo)
        posicion = self._posiciones.buscar(conn, cuenta.id_cuenta, id_activo)
        ganancia = ganancia_pct = None
        if posicion is not None and item.cotizacion is not None:
            _valor, ganancia, ganancia_pct = valorar_posicion(posicion, item.cotizacion.precio)
        return ResumenOperar(item, cuenta.saldo_disponible, cuenta.moneda, cuenta.comision_pct,
                             cuenta.deslizamiento_pct, posicion, ganancia, ganancia_pct)

    def _leer_posiciones(self, conn, cuenta: CuentaSimulada) -> List[PosicionValorada]:
        posiciones = self._posiciones.listar(conn, cuenta.id_cuenta)
        items: Dict[int, ActivoCotizado] = {
            i.activo.id_activo: i for i in self._activos.listar_cotizados(conn, solo_activos=False)}
        return [self._valorar(p, items.get(p.id_activo)) for p in posiciones]

    @staticmethod
    def _valorar(posicion: Posicion, item: Optional[ActivoCotizado]) -> PosicionValorada:
        ticker = item.activo.ticker if item else str(posicion.id_activo)
        moneda = item.activo.moneda if item else ""
        if item is None or item.cotizacion is None:
            return PosicionValorada(posicion, ticker, moneda, None, None, None, None)
        valor, ganancia, pct = valorar_posicion(posicion, item.cotizacion.precio)
        return PosicionValorada(posicion, ticker, moneda, item.cotizacion.precio, valor, ganancia, pct)

    def _cuenta_de(self, conn, actor: Usuario, bloquear: bool = False) -> CuentaSimulada:
        cuenta = self._cuentas.buscar_de_usuario(conn, actor.id_usuario, bloquear=bloquear)
        if cuenta is None:
            raise ErrorOperacionInvalida("No tienes una cuenta simulada activa.")
        return cuenta

    def _buscar_activo(self, conn, id_activo: int) -> ActivoCotizado:
        item = self._activos.buscar_cotizado(conn, id_activo)
        if item is None or not item.activo.activo:
            raise ErrorOperacionInvalida("Ese activo no existe o está deshabilitado.")
        return item

    @staticmethod
    def _exigir_operable(item: ActivoCotizado, moneda_cuenta: str) -> None:
        if item.cotizacion is None:
            raise ErrorOperacionInvalida("Ese activo todavía no tiene precio.")
        if item.activo.moneda != moneda_cuenta:
            raise ErrorOperacionInvalida(
                "%s cotiza en %s y tu cuenta está en %s: todavía no se puede operar con cambio de moneda."
                % (item.activo.ticker, item.activo.moneda, moneda_cuenta))

    # ---------------------------------------------------------- lectura de lo escrito
    def _leer_limite(self, s: SolicitudOrden) -> Optional[Decimal]:
        """El precio límite (None si la orden es a mercado)."""
        if s.tipo == TipoOrden.MERCADO:
            return None
        if s.tipo != TipoOrden.LIMITE:
            raise ErrorOperacionInvalida("Ese tipo de orden no está disponible: el stop-loss y el take-profit "
                                         "se ponen en la posición.")
        limite = self._a_decimal(s.precio_limite, "precio_limite", "precio límite")
        if limite is None:
            raise DatosInvalidos({"precio_limite": "Ingresa el precio límite."})
        return limite

    def _limite_si_es_valido(self, s: SolicitudOrden) -> Optional[Decimal]:
        """El precio límite escrito, o None si no es una orden límite o aún no está bien escrito."""
        if s.tipo != TipoOrden.LIMITE:
            return None
        try:
            return self._a_decimal(s.precio_limite, "precio_limite", "precio límite")
        except DatosInvalidos:
            return None

    def _leer_niveles(self, s: SolicitudOrden, referencia: Decimal) -> Tuple[Optional[Decimal], Optional[Decimal]]:
        """Stop-loss y take-profit de una COMPRA, respecto del precio al que se comprará."""
        if s.lado == LadoOrden.VENTA:
            if s.stop_loss.strip() or s.take_profit.strip():
                raise ErrorOperacionInvalida("El stop-loss y el take-profit se ponen al comprar o con "
                                             "«Editar SL/TP» en la posición.")
            return None, None
        stop_loss = self._a_decimal(s.stop_loss, "stop_loss", "stop-loss")
        take_profit = self._a_decimal(s.take_profit, "take_profit", "take-profit")
        lanzar_si_hay_errores({
            "stop_loss": ("El stop-loss debe estar por debajo del precio de compra."
                          if stop_loss is not None and stop_loss >= referencia else None),
            "take_profit": ("El take-profit debe estar por encima del precio de compra."
                            if take_profit is not None and take_profit <= referencia else None),
        })
        return stop_loss, take_profit

    @staticmethod
    def _numero(texto: str) -> str:
        return (texto or "").replace("\u00a0", "").replace(" ", "").replace(",", ".")

    @classmethod
    def _a_decimal(cls, texto: str, campo: str, nombre: str) -> Optional[Decimal]:
        """Un precio escrito (acepta coma o punto). None si está vacío; DatosInvalidos si no es válido."""
        texto = cls._numero(texto)
        if not texto:
            return None
        error = DatosInvalidos({campo: "Ingresa un %s válido, mayor que cero (por ejemplo: 123,45)." % nombre})
        try:
            valor = Decimal(texto)
        except InvalidOperation:
            raise error
        if not valor.is_finite() or valor <= 0 or valor >= _CANTIDAD_MAXIMA:
            raise error
        valor = valor.quantize(_DECIMALES_PRECIO, rounding=ROUND_DOWN)
        if valor == 0:
            raise error
        return valor

    @classmethod
    def _leer_cantidad(cls, texto: str) -> Decimal:
        """Convierte lo escrito (acepta coma o punto decimal y espacios de miles) en una cantidad válida."""
        texto = cls._numero(texto)
        if not texto:
            raise DatosInvalidos({"cantidad": "Ingresa la cantidad."})
        try:
            valor = Decimal(texto)
        except InvalidOperation:
            valor = None
        if valor is None or not valor.is_finite():
            raise DatosInvalidos({"cantidad": "Ingresa una cantidad válida (por ejemplo: 0,5)."})
        if valor <= 0:
            raise DatosInvalidos({"cantidad": "La cantidad debe ser mayor que cero."})
        if valor >= _CANTIDAD_MAXIMA:
            raise DatosInvalidos({"cantidad": "La cantidad es demasiado grande."})
        valor = valor.quantize(_DECIMALES_CANTIDAD, rounding=ROUND_DOWN)
        if valor == 0:
            raise DatosInvalidos({"cantidad": "La cantidad es demasiado pequeña (máximo 10 decimales)."})
        return valor
