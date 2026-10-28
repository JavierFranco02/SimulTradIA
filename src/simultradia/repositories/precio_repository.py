"""Acceso a "precios_velas" y "cotizaciones_actuales". Aquí vive el SQL de precios."""
from datetime import datetime
from typing import Dict, List, Optional

from psycopg2.extras import execute_values

from simultradia.domain.entities.cotizacion_entity import Cotizacion
from simultradia.domain.entities.vela_entity import Vela
from simultradia.domain.enums import IntervaloVela


class PrecioRepository:
    # ------------------------------------------------------------ cotizaciones
    def guardar_cotizacion(self, conn, c: Cotizacion) -> None:
        """PostgreSQL 9.3 no tiene ON CONFLICT: se intenta actualizar y, si no había fila, se inserta."""
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE cotizaciones_actuales
                   SET precio = %s, cierre_anterior = %s, variacion_pct_dia = %s,
                       maximo_dia = %s, minimo_dia = %s, volumen_dia = %s, actualizado_en = now()
                   WHERE id_activo = %s""",
                (c.precio, c.cierre_anterior, c.variacion_pct_dia, c.maximo_dia,
                 c.minimo_dia, c.volumen_dia, c.id_activo),
            )
            if cur.rowcount == 0:
                cur.execute(
                    """INSERT INTO cotizaciones_actuales
                           (id_activo, precio, cierre_anterior, variacion_pct_dia,
                            maximo_dia, minimo_dia, volumen_dia)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (c.id_activo, c.precio, c.cierre_anterior, c.variacion_pct_dia,
                     c.maximo_dia, c.minimo_dia, c.volumen_dia),
                )

    def borrar_precios(self, conn, id_activo: int) -> None:
        """Borra las velas y la cotización de un activo (para empezar limpio con otra fuente)."""
        with conn.cursor() as cur:
            cur.execute("DELETE FROM precios_velas WHERE id_activo = %s", (id_activo,))
            cur.execute("DELETE FROM cotizaciones_actuales WHERE id_activo = %s", (id_activo,))

    def ultima_actualizacion(self, conn) -> Optional[datetime]:
        with conn.cursor() as cur:
            cur.execute("SELECT max(actualizado_en) AS ultima FROM cotizaciones_actuales")
            return cur.fetchone().ultima

    # ------------------------------------------------------------------ velas
    def ultimo_momento(self, conn, id_activo: int, intervalo: IntervaloVela) -> Optional[datetime]:
        with conn.cursor() as cur:
            cur.execute("SELECT max(momento) AS ultimo FROM precios_velas "
                        "WHERE id_activo = %s AND intervalo = %s", (id_activo, intervalo.value))
            return cur.fetchone().ultimo

    def reemplazar_velas(self, conn, id_activo: int, intervalo: IntervaloVela,
                         velas: List[Vela]) -> None:
        """Guarda las velas; si alguna ya existía, la reemplaza (borrar el rango e insertar,
        dentro de la misma transacción: en 9.3 es la forma de hacer un "upsert" en bloque)."""
        if not velas:
            return
        with conn.cursor() as cur:
            cur.execute("DELETE FROM precios_velas WHERE id_activo = %s AND intervalo = %s "
                        "AND momento >= %s", (id_activo, intervalo.value, min(v.momento for v in velas)))
            execute_values(
                cur,
                """INSERT INTO precios_velas
                       (id_activo, intervalo, momento, apertura, maximo, minimo, cierre, volumen)
                   VALUES %s""",
                [(id_activo, intervalo.value, v.momento, v.apertura, v.maximo, v.minimo,
                  v.cierre, v.volumen) for v in velas],
                template="(%s, %s::intervalo_vela, %s, %s, %s, %s, %s, %s)",
            )

    def buscar_velas(self, conn, id_activo: int, intervalo: IntervaloVela, limite: int) -> List[Vela]:
        """Las últimas `limite` velas, de la más vieja a la más nueva."""
        with conn.cursor() as cur:
            cur.execute(
                """SELECT momento, apertura, maximo, minimo, cierre, volumen FROM (
                       SELECT momento, apertura, maximo, minimo, cierre, volumen
                       FROM precios_velas
                       WHERE id_activo = %s AND intervalo = %s
                       ORDER BY momento DESC LIMIT %s
                   ) ultimas ORDER BY momento""",
                (id_activo, intervalo.value, limite),
            )
            return [Vela(f.momento, f.apertura, f.maximo, f.minimo, f.cierre, f.volumen)
                    for f in cur.fetchall()]

    def contar_velas_por_intervalo(self, conn) -> Dict[str, int]:
        with conn.cursor() as cur:
            cur.execute("SELECT intervalo::text AS intervalo, COUNT(*) AS total "
                        "FROM precios_velas GROUP BY intervalo")
            return {f.intervalo: f.total for f in cur.fetchall()}
