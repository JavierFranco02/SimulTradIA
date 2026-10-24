"""Acceso a la tabla "cuentas_simuladas". Aquí vive TODO el SQL de cuentas."""
from simultradia.domain.entities.cuenta_simulada_entity import CuentaSimulada


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
