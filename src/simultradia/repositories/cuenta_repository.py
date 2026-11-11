"""Acceso a la tabla "cuentas_simuladas". Aquí vive TODO el SQL de cuentas."""
from decimal import Decimal
from typing import Optional

from simultradia.domain.entities.cuenta_simulada_entity import CuentaSimulada

_COLUMNAS = ("id_cuenta, id_usuario, nombre, moneda, capital_inicial, saldo_disponible, "
             "comision_pct, deslizamiento_pct, creada_en")


class CuentaRepository:
    """Igual que UsuarioRepository: recibe la conexión que presta el servicio."""

    def insertar(self, conn, cuenta: CuentaSimulada) -> CuentaSimulada:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO cuentas_simuladas
                       (id_usuario, nombre, moneda, capital_inicial, saldo_disponible)
                   VALUES (%s, %s, %s, %s, %s)
                   RETURNING id_cuenta, creada_en""",
                (cuenta.id_usuario, cuenta.nombre, cuenta.moneda,
                 cuenta.capital_inicial, cuenta.saldo_disponible),
            )
            fila = cur.fetchone()
        cuenta.id_cuenta = fila.id_cuenta
        cuenta.creada_en = fila.creada_en
        return cuenta

    def buscar_de_usuario(self, conn, id_usuario: int, bloquear: bool = False) -> Optional[CuentaSimulada]:
        """La cuenta con la que opera el usuario (activa y no de replay).

        Con `bloquear=True` la fila queda bloqueada hasta que termine la transacción (FOR UPDATE):
        dos operaciones a la vez sobre la misma cuenta se hacen una tras otra, no mezcladas."""
        return self._buscar(
            conn, "WHERE id_usuario = %s AND activa AND NOT es_replay ORDER BY id_cuenta LIMIT 1",
            (id_usuario,), bloquear)

    def buscar_por_id(self, conn, id_cuenta: int, bloquear: bool = False) -> Optional[CuentaSimulada]:
        """Para el worker, que ejecuta órdenes pendientes de cuentas sin tener a su usuario delante."""
        return self._buscar(conn, "WHERE id_cuenta = %s", (id_cuenta,), bloquear)

    def actualizar_saldo(self, conn, id_cuenta: int, saldo: Decimal) -> bool:
        with conn.cursor() as cur:
            cur.execute("UPDATE cuentas_simuladas SET saldo_disponible = %s WHERE id_cuenta = %s",
                        (saldo, id_cuenta))
            return cur.rowcount > 0

    @staticmethod
    def _buscar(conn, condicion: str, parametros, bloquear: bool) -> Optional[CuentaSimulada]:
        sql = "SELECT " + _COLUMNAS + " FROM cuentas_simuladas " + condicion + (" FOR UPDATE" if bloquear else "")
        with conn.cursor() as cur:
            cur.execute(sql, parametros)
            fila = cur.fetchone()
        if fila is None:
            return None
        return CuentaSimulada(
            id_cuenta=fila.id_cuenta, id_usuario=fila.id_usuario, nombre=fila.nombre,
            moneda=fila.moneda.strip(),            # CHAR(3) puede traer relleno
            capital_inicial=fila.capital_inicial, saldo_disponible=fila.saldo_disponible,
            comision_pct=fila.comision_pct, deslizamiento_pct=fila.deslizamiento_pct,
            creada_en=fila.creada_en)
