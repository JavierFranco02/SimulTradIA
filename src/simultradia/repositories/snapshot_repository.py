"""Acceso a la tabla "snapshots_portafolio" (la foto del patrimonio de cada cuenta). Aquí vive su SQL."""
from datetime import datetime
from typing import List

from simultradia.domain.entities.snapshot_entity import SnapshotPortafolio


class SnapshotRepository:
    def guardar(self, conn, s: SnapshotPortafolio) -> None:
        """PostgreSQL 9.3 no tiene ON CONFLICT: se intenta actualizar la foto de ese momento y, si no había, se inserta."""
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE snapshots_portafolio
                   SET saldo_disponible = %s, valor_posiciones = %s, patrimonio_total = %s
                   WHERE id_cuenta = %s AND momento = %s""",
                (s.saldo_disponible, s.valor_posiciones, s.patrimonio_total, s.id_cuenta, s.momento))
            if cur.rowcount == 0:
                cur.execute(
                    """INSERT INTO snapshots_portafolio
                           (id_cuenta, momento, saldo_disponible, valor_posiciones, patrimonio_total)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (s.id_cuenta, s.momento, s.saldo_disponible, s.valor_posiciones, s.patrimonio_total))

    def listar(self, conn, id_cuenta: int) -> List[SnapshotPortafolio]:
        """Todas las fotos de la cuenta, de la más vieja a la más nueva."""
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id_cuenta, momento, saldo_disponible, valor_posiciones, patrimonio_total
                   FROM snapshots_portafolio WHERE id_cuenta = %s ORDER BY momento""", (id_cuenta,))
            return [SnapshotPortafolio(f.id_cuenta, f.momento, f.saldo_disponible, f.valor_posiciones,
                                       f.patrimonio_total) for f in cur.fetchall()]

    def compactar(self, conn, antes_de: datetime) -> None:
        """De TODAS las cuentas: lo anterior a `antes_de` se reduce a UNA foto por hora (la última de esa hora).
        Así la tabla no crece sin límite aunque se guarde una foto por minuto."""
        with conn.cursor() as cur:
            cur.execute(
                """DELETE FROM snapshots_portafolio
                   WHERE (id_cuenta, momento) IN (
                       SELECT id_cuenta, momento FROM (
                           SELECT id_cuenta, momento,
                                  row_number() OVER (PARTITION BY id_cuenta, date_trunc('hour', momento)
                                                     ORDER BY momento DESC) AS n
                           FROM snapshots_portafolio WHERE momento < %s) por_hora
                       WHERE n > 1)""", (antes_de,))
