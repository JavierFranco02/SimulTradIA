"""Casos de uso de Portafolio: cómo le va a la cuenta (patrimonio, curva de capital, métricas, operaciones cerradas).

- La CURVA se arma con las fotos guardadas (`snapshots_portafolio`, una por minuto). Si la primera foto es
  posterior a la creación de la cuenta, la curva arranca con el capital inicial en ese momento.
- Fotos: `guardar_snapshots` lo llama el worker cada minuto (sin actor) para todas las cuentas, y
  `obtener_portafolio` guarda además la del minuto actual al abrir la pantalla: así la curva tiene puntos
  aunque el worker esté apagado (con el worker apagado los precios no cambian, solo las operaciones).
- Compactación: lo que tiene más de 7 días se reduce a UNA foto por hora (la última), para que la tabla no crezca sin límite.
- Las posiciones sin precio se valoran a lo que costaron (igual que Operar).
- Solo para usuarios que operan: el administrador no tiene cuenta simulada.

Python puro respecto de la interfaz; los cálculos viven en `analisis/metricas.py` y `domain/reglas/portafolio.py`.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Callable, Dict, List, NamedTuple, Optional, Tuple

from simultradia.analisis import metricas
from simultradia.core.exceptions import ErrorOperacionInvalida
from simultradia.domain.entities.cotizacion_entity import ActivoCotizado
from simultradia.domain.entities.cuenta_simulada_entity import CuentaSimulada
from simultradia.domain.entities.operacion_cerrada_entity import OperacionCerrada
from simultradia.domain.entities.posicion_entity import Posicion
from simultradia.domain.entities.snapshot_entity import SnapshotPortafolio
from simultradia.domain.entities.usuario_entity import Usuario
from simultradia.domain.reglas.operaciones import redondear_dinero, valorar_posicion
from simultradia.domain.reglas.portafolio import (
    EstadisticasOperaciones, estadisticas_operaciones, exposicion_pct, ganancia_pct, rentabilidad_pct)
from simultradia.services.permisos import exigir_operador


_DIAS_SIN_COMPACTAR = 7     # las fotos más recientes se guardan todas (una por minuto); las anteriores, una por hora


def _ahora_utc() -> datetime:
    return datetime.now(timezone.utc)


def _minuto(momento: datetime) -> datetime:
    return momento.replace(second=0, microsecond=0)


class OperacionResultado(NamedTuple):
    """Una operación cerrada con su ganancia en % (lo que se ve en la tabla)."""
    operacion: OperacionCerrada
    ganancia_pct: Decimal


@dataclass(frozen=True)
class ResumenPortafolio:
    """Todo lo que la pantalla Portafolio muestra, leído en una sola conexión."""
    moneda: str
    capital_inicial: Decimal
    patrimonio: Decimal
    rentabilidad_pct: Decimal
    saldo_disponible: Decimal
    valor_posiciones: Decimal
    pnl_no_realizado: Decimal           # lo que se ganaría o perdería si se vendieran las posiciones ahora
    pnl_realizado: Decimal              # suma de las ganancias de las operaciones cerradas
    exposicion_pct: Decimal
    puntos: List[SnapshotPortafolio]    # la curva, de la más vieja a la de este minuto
    caidas: List[float]                 # caída desde el máximo en cada punto, en % (0 o negativo)
    caida_maxima: float
    volatilidad_anual: Optional[float]  # None con poco historial
    sharpe: Optional[float]             # None con poco historial
    estadisticas: EstadisticasOperaciones
    comisiones_pagadas: Decimal         # las de las operaciones cerradas + las de compra de lo que aún se tiene
    operaciones: List[OperacionResultado]   # de la más nueva a la más vieja


class PortafolioService:
    def __init__(self, db, cuenta_repository, posicion_repository, activo_repository, snapshot_repository,
                 reloj: Callable[[], datetime] = _ahora_utc):
        self._db = db
        self._cuentas = cuenta_repository
        self._posiciones = posicion_repository
        self._activos = activo_repository
        self._snapshots = snapshot_repository
        self._reloj = reloj
        self._hora_compactada: Optional[datetime] = None    # la última hora en que se compactó (para hacerlo una vez por hora)

    # ------------------------------------------------------------- consulta
    def obtener_portafolio(self, actor: Usuario) -> ResumenPortafolio:
        exigir_operador(actor)
        ahora = self._reloj()
        with self._db.obtener_conexion() as conn:
            cuenta = self._cuentas.buscar_de_usuario(conn, actor.id_usuario)
            if cuenta is None:
                raise ErrorOperacionInvalida("No tienes una cuenta simulada activa.")
            posiciones = self._posiciones.listar(conn, cuenta.id_cuenta)
            items = self._cotizados(conn)
            cerradas = self._posiciones.listar_operaciones_cerradas(conn, cuenta.id_cuenta)
            valor, pnl_no_realizado = self._valorar(posiciones, items)
            patrimonio = redondear_dinero(cuenta.saldo_disponible + valor)
            # La foto del minuto actual se guarda al abrir (y en cada refresco: se reescribe la misma fila),
            # así la curva termina siempre en "ahora" y avanza aunque el worker esté apagado.
            self._snapshots.guardar(conn, SnapshotPortafolio(
                cuenta.id_cuenta, _minuto(ahora), cuenta.saldo_disponible, valor, patrimonio))
            guardadas = self._snapshots.listar(conn, cuenta.id_cuenta)

        puntos = self._curva(cuenta, guardadas)
        valores = [float(p.patrimonio_total) for p in puntos]   # float solo para métricas y dibujo, nunca para dinero
        retornos = metricas.retornos_diarios([p.momento for p in puntos], valores)
        caidas = metricas.caidas(valores)
        estadisticas = estadisticas_operaciones(cerradas)
        return ResumenPortafolio(
            moneda=cuenta.moneda, capital_inicial=cuenta.capital_inicial, patrimonio=patrimonio,
            rentabilidad_pct=rentabilidad_pct(patrimonio, cuenta.capital_inicial),
            saldo_disponible=cuenta.saldo_disponible, valor_posiciones=valor,
            pnl_no_realizado=pnl_no_realizado, pnl_realizado=estadisticas.ganancia_total,
            exposicion_pct=exposicion_pct(valor, patrimonio),
            puntos=puntos, caidas=caidas, caida_maxima=min(caidas, default=0.0),
            volatilidad_anual=metricas.volatilidad_anual(retornos), sharpe=metricas.sharpe(retornos),
            estadisticas=estadisticas,
            comisiones_pagadas=estadisticas.comisiones + sum((p.comisiones_pagadas for p in posiciones), Decimal(0)),
            operaciones=[OperacionResultado(o, ganancia_pct(o)) for o in cerradas])

    # ------------------------------------------------- para el worker (sin actor)
    def guardar_snapshots(self) -> int:
        """Guarda la foto del minuto actual de cada cuenta con la que se opera (y, una vez por hora, compacta
        lo antiguo). Devuelve cuántas cuentas."""
        ahora = self._reloj()
        momento = _minuto(ahora)
        with self._db.obtener_conexion() as conn:
            cuentas = self._cuentas.listar_operables(conn)
            items = self._cotizados(conn)
            for cuenta in cuentas:
                valor, _pnl = self._valorar(self._posiciones.listar(conn, cuenta.id_cuenta), items)
                self._snapshots.guardar(conn, SnapshotPortafolio(
                    cuenta.id_cuenta, momento, cuenta.saldo_disponible, valor,
                    redondear_dinero(cuenta.saldo_disponible + valor)))
            hora = momento.replace(minute=0)
            if hora != self._hora_compactada:
                self._snapshots.compactar(conn, hora - timedelta(days=_DIAS_SIN_COMPACTAR))
                self._hora_compactada = hora
        return len(cuentas)

    # --------------------------------------------------------------- interno
    def _cotizados(self, conn) -> Dict[int, ActivoCotizado]:
        return {i.activo.id_activo: i for i in self._activos.listar_cotizados(conn, solo_activos=False)}

    @staticmethod
    def _valorar(posiciones: List[Posicion], items: Dict[int, ActivoCotizado]) -> Tuple[Decimal, Decimal]:
        """(valor de mercado de las posiciones, ganancia no realizada). Sin precio: se valora a lo que costó."""
        valor = pnl = Decimal(0)
        for p in posiciones:
            item = items.get(p.id_activo)
            if item is None or item.cotizacion is None:
                valor += p.cantidad * p.precio_promedio_entrada
            else:
                v, ganancia, _pct = valorar_posicion(p, item.cotizacion.precio)
                valor += v
                pnl += ganancia
        return redondear_dinero(valor), pnl

    @staticmethod
    def _curva(cuenta: CuentaSimulada, guardadas: List[SnapshotPortafolio]) -> List[SnapshotPortafolio]:
        puntos = list(guardadas)
        if cuenta.creada_en is not None and (not puntos or puntos[0].momento > cuenta.creada_en):
            puntos.insert(0, SnapshotPortafolio(cuenta.id_cuenta, cuenta.creada_en, cuenta.capital_inicial,
                                                Decimal(0), cuenta.capital_inicial))
        return puntos
