"""Acceso a "ordenes" y "ejecuciones" (van juntas: cada orden ejecutada deja su ejecución). Aquí vive su SQL."""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from simultradia.domain.entities.orden_entity import Ejecucion, Orden
from simultradia.domain.enums import EstadoOrden, LadoOrden, TipoOrden

_SELECT = """SELECT o.id_orden, o.id_cuenta, o.id_activo, a.ticker, o.lado, o.tipo, o.estado, o.cantidad,
                    o.precio_promedio, o.precio_limite, o.stop_loss, o.take_profit, o.comision_total,
                    o.motivo_rechazo, o.creada_en, o.ejecutada_en, o.cancelada_en
             FROM ordenes o JOIN activos a ON a.id_activo = o.id_activo"""


class OrdenRepository:
    def insertar_orden(self, conn, o: Orden) -> Orden:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO ordenes (id_cuenta, id_activo, lado, tipo, estado, cantidad, precio_promedio,
                                        precio_limite, stop_loss, take_profit, comision_total, ejecutada_en)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING id_orden, creada_en""",
                (o.id_cuenta, o.id_activo, o.lado.value, o.tipo.value, o.estado.value, o.cantidad,
                 o.precio_promedio, o.precio_limite, o.stop_loss, o.take_profit, o.comision_total,
                 o.ejecutada_en))
            fila = cur.fetchone()
        o.id_orden, o.creada_en = fila.id_orden, fila.creada_en
        return o

    def buscar(self, conn, id_orden: int, bloquear: bool = False) -> Optional[Orden]:
        """Con `bloquear=True` se bloquea SOLO la fila de la orden (no la del activo)."""
        sql = _SELECT + " WHERE o.id_orden = %s" + (" FOR UPDATE OF o" if bloquear else "")
        with conn.cursor() as cur:
            cur.execute(sql, (id_orden,))
            fila = cur.fetchone()
        return self._a_entidad(fila) if fila else None

    def listar_ordenes(self, conn, id_cuenta: int, limite: int) -> List[Orden]:
        """El historial: las últimas `limite` órdenes que ya no están pendientes, de la más nueva a la más vieja."""
        return self._listar(conn, " WHERE o.id_cuenta = %s AND o.estado <> 'pendiente'"
                                  " ORDER BY o.creada_en DESC, o.id_orden DESC LIMIT %s", (id_cuenta, limite))

    def listar_pendientes(self, conn, id_cuenta: int) -> List[Orden]:
        return self._listar(conn, " WHERE o.id_cuenta = %s AND o.estado = 'pendiente'"
                                  " ORDER BY o.creada_en DESC, o.id_orden DESC", (id_cuenta,))

    def listar_pendientes_todas(self, conn) -> List[Orden]:
        """De TODAS las cuentas (lo que revisa el worker)."""
        return self._listar(conn, " WHERE o.estado = 'pendiente' ORDER BY o.id_orden", ())

    def marcar_ejecutada(self, conn, id_orden: int, precio: Decimal, comision: Decimal, ahora: datetime) -> None:
        with conn.cursor() as cur:
            cur.execute("""UPDATE ordenes SET estado = 'ejecutada', precio_promedio = %s, comision_total = %s,
                                              ejecutada_en = %s WHERE id_orden = %s""",
                        (precio, comision, ahora, id_orden))

    def marcar_rechazada(self, conn, id_orden: int, motivo: str) -> None:
        with conn.cursor() as cur:
            cur.execute("UPDATE ordenes SET estado = 'rechazada', motivo_rechazo = %s WHERE id_orden = %s",
                        (motivo, id_orden))

    def cancelar(self, conn, id_orden: int, ahora: datetime) -> bool:
        """Cancela la orden SI sigue pendiente. Devuelve False si ya no lo estaba."""
        with conn.cursor() as cur:
            cur.execute("""UPDATE ordenes SET estado = 'cancelada', cancelada_en = %s
                           WHERE id_orden = %s AND estado = 'pendiente'""", (ahora, id_orden))
            return cur.rowcount > 0

    def insertar_ejecucion(self, conn, e: Ejecucion) -> Ejecucion:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO ejecuciones (id_orden, id_cuenta, id_activo, lado, cantidad, precio,
                                            comision, ejecutada_en)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id_ejecucion""",
                (e.id_orden, e.id_cuenta, e.id_activo, e.lado.value, e.cantidad, e.precio,
                 e.comision, e.ejecutada_en))
            e.id_ejecucion = cur.fetchone().id_ejecucion
        return e

    # --------------------------------------------------------------- interno
    def _listar(self, conn, resto: str, parametros) -> List[Orden]:
        with conn.cursor() as cur:
            cur.execute(_SELECT + resto, parametros)
            return [self._a_entidad(f) for f in cur.fetchall()]

    @staticmethod
    def _a_entidad(f) -> Orden:
        return Orden(
            id_orden=f.id_orden, id_cuenta=f.id_cuenta, id_activo=f.id_activo, ticker=f.ticker,
            lado=LadoOrden(f.lado), tipo=TipoOrden(f.tipo), estado=EstadoOrden(f.estado),
            cantidad=f.cantidad, precio_promedio=f.precio_promedio, precio_limite=f.precio_limite,
            stop_loss=f.stop_loss, take_profit=f.take_profit, comision_total=f.comision_total,
            motivo_rechazo=f.motivo_rechazo, creada_en=f.creada_en, ejecutada_en=f.ejecutada_en,
            cancelada_en=f.cancelada_en)
