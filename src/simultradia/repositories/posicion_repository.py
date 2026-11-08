"""Acceso a "posiciones" y "operaciones_cerradas" (van juntas: una venta toca ambas). Aquí vive su SQL."""
from typing import List, Optional

from simultradia.domain.entities.operacion_cerrada_entity import OperacionCerrada
from simultradia.domain.entities.posicion_entity import Posicion

_SELECT = """SELECT id_posicion, id_cuenta, id_activo, cantidad, precio_promedio_entrada,
                    comisiones_pagadas, abierta_en, stop_loss, take_profit
             FROM posiciones"""


class PosicionRepository:
    def buscar(self, conn, id_cuenta: int, id_activo: int) -> Optional[Posicion]:
        with conn.cursor() as cur:
            cur.execute(_SELECT + " WHERE id_cuenta = %s AND id_activo = %s", (id_cuenta, id_activo))
            fila = cur.fetchone()
        return self._a_entidad(fila) if fila else None

    def listar(self, conn, id_cuenta: int) -> List[Posicion]:
        with conn.cursor() as cur:
            cur.execute(_SELECT + " WHERE id_cuenta = %s ORDER BY abierta_en, id_posicion", (id_cuenta,))
            return [self._a_entidad(fila) for fila in cur.fetchall()]

    def listar_protegidas(self, conn) -> List[Posicion]:
        """De TODAS las cuentas: las posiciones con stop-loss o take-profit (lo que revisa el worker)."""
        with conn.cursor() as cur:
            cur.execute(_SELECT + " WHERE stop_loss IS NOT NULL OR take_profit IS NOT NULL ORDER BY id_posicion")
            return [self._a_entidad(fila) for fila in cur.fetchall()]

    def insertar(self, conn, p: Posicion) -> Posicion:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO posiciones (id_cuenta, id_activo, cantidad, precio_promedio_entrada,
                                           comisiones_pagadas, abierta_en, stop_loss, take_profit)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING id_posicion""",
                (p.id_cuenta, p.id_activo, p.cantidad, p.precio_promedio_entrada,
                 p.comisiones_pagadas, p.abierta_en, p.stop_loss, p.take_profit))
            p.id_posicion = cur.fetchone().id_posicion
        return p

    def actualizar(self, conn, p: Posicion) -> None:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE posiciones SET cantidad = %s, precio_promedio_entrada = %s,
                                         comisiones_pagadas = %s, stop_loss = %s, take_profit = %s
                   WHERE id_posicion = %s""",
                (p.cantidad, p.precio_promedio_entrada, p.comisiones_pagadas, p.stop_loss, p.take_profit,
                 p.id_posicion))

    def borrar(self, conn, id_posicion: int) -> None:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM posiciones WHERE id_posicion = %s", (id_posicion,))

    def insertar_operacion_cerrada(self, conn, o: OperacionCerrada) -> OperacionCerrada:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO operaciones_cerradas
                       (id_cuenta, id_activo, cantidad, precio_entrada, precio_salida, comisiones,
                        ganancia_realizada, abierta_en, cerrada_en)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING id_operacion_cerrada""",
                (o.id_cuenta, o.id_activo, o.cantidad, o.precio_entrada, o.precio_salida,
                 o.comisiones, o.ganancia_realizada, o.abierta_en, o.cerrada_en))
            o.id_operacion_cerrada = cur.fetchone().id_operacion_cerrada
        return o

    @staticmethod
    def _a_entidad(f) -> Posicion:
        return Posicion(id_posicion=f.id_posicion, id_cuenta=f.id_cuenta, id_activo=f.id_activo,
                        cantidad=f.cantidad, precio_promedio_entrada=f.precio_promedio_entrada,
                        comisiones_pagadas=f.comisiones_pagadas, abierta_en=f.abierta_en,
                        stop_loss=f.stop_loss, take_profit=f.take_profit)
