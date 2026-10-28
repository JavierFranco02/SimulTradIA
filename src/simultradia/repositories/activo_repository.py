"""Acceso a la tabla "activos" (y su cotización actual). Aquí vive el SQL de activos."""
from typing import List, Optional

import psycopg2

from simultradia.core.exceptions import DatosInvalidos
from simultradia.domain.entities.activo_entity import Activo
from simultradia.domain.entities.cotizacion_entity import ActivoCotizado, Cotizacion
from simultradia.domain.enums import TipoActivo

_COLUMNAS_ACTIVO = ("a.id_activo, a.ticker, a.nombre, a.tipo, a.moneda, a.activo, a.creado_en, "
                    "a.id_fuente, f.nombre AS fuente")
_DESDE_ACTIVO = " FROM activos a JOIN fuentes_datos f ON f.id_fuente = a.id_fuente"
_SELECT_COTIZADO = """
    SELECT a.id_activo, a.ticker, a.nombre, a.tipo, a.moneda, a.activo, a.creado_en,
           a.id_fuente, f.nombre AS fuente,
           c.precio, c.cierre_anterior, c.variacion_pct_dia, c.maximo_dia,
           c.minimo_dia, c.volumen_dia, c.actualizado_en
    FROM activos a
    JOIN fuentes_datos f ON f.id_fuente = a.id_fuente
    LEFT JOIN cotizaciones_actuales c ON c.id_activo = a.id_activo"""


class ActivoRepository:
    """Cada método recibe la conexión que presta el servicio. Filas leídas por nombre."""

    def listar_cotizados(self, conn, solo_activos: bool = True) -> List[ActivoCotizado]:
        sql = _SELECT_COTIZADO + (" WHERE a.activo" if solo_activos else "") + " ORDER BY a.ticker"
        with conn.cursor() as cur:
            cur.execute(sql)
            return [self._a_cotizado(fila) for fila in cur.fetchall()]

    def buscar_cotizado(self, conn, id_activo: int) -> Optional[ActivoCotizado]:
        with conn.cursor() as cur:
            cur.execute(_SELECT_COTIZADO + " WHERE a.id_activo = %s", (id_activo,))
            fila = cur.fetchone()
        return self._a_cotizado(fila) if fila else None

    def listar_activos(self, conn, solo_activos: bool = True) -> List[Activo]:
        sql = ("SELECT " + _COLUMNAS_ACTIVO + _DESDE_ACTIVO
               + (" WHERE a.activo" if solo_activos else "") + " ORDER BY a.ticker")
        with conn.cursor() as cur:
            cur.execute(sql)
            return [self._a_activo(fila) for fila in cur.fetchall()]

    def buscar_por_ticker(self, conn, ticker: str) -> Optional[Activo]:
        with conn.cursor() as cur:
            cur.execute("SELECT " + _COLUMNAS_ACTIVO + _DESDE_ACTIVO
                        + " WHERE upper(a.ticker) = upper(%s)", (ticker,))
            fila = cur.fetchone()
        return self._a_activo(fila) if fila else None

    def insertar(self, conn, activo: Activo) -> Activo:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO activos (ticker, nombre, tipo, moneda, activo, id_fuente)
                       VALUES (%s, %s, %s, %s, %s, %s)
                       RETURNING id_activo, creado_en""",
                    (activo.ticker, activo.nombre, activo.tipo.value, activo.moneda,
                     activo.activo, activo.id_fuente),
                )
                fila = cur.fetchone()
        except psycopg2.IntegrityError as error:
            if error.pgcode == "23505":   # dos administradores agregando el mismo par a la vez
                raise DatosInvalidos({"ticker": "Ese activo ya está en el catálogo."}) from error
            raise
        activo.id_activo = fila.id_activo
        activo.creado_en = fila.creado_en
        return activo

    def establecer_activo(self, conn, id_activo: int, activo: bool) -> bool:
        """Habilita o deshabilita un activo. Devuelve False si no existe."""
        with conn.cursor() as cur:
            cur.execute("UPDATE activos SET activo = %s WHERE id_activo = %s", (activo, id_activo))
            return cur.rowcount > 0

    def actualizar(self, conn, id_activo: int, nombre: str, moneda: str) -> bool:
        with conn.cursor() as cur:
            cur.execute("UPDATE activos SET nombre = %s, moneda = %s WHERE id_activo = %s",
                        (nombre, moneda, id_activo))
            return cur.rowcount > 0

    def cambiar_fuente(self, conn, id_activo: int, id_fuente: int) -> bool:
        with conn.cursor() as cur:
            cur.execute("UPDATE activos SET id_fuente = %s WHERE id_activo = %s", (id_fuente, id_activo))
            return cur.rowcount > 0

    @staticmethod
    def _a_activo(fila) -> Activo:
        return Activo(
            id_activo=fila.id_activo, ticker=fila.ticker, nombre=fila.nombre,
            tipo=TipoActivo(fila.tipo), moneda=fila.moneda.strip(),   # CHAR(3) puede traer relleno
            activo=fila.activo, creado_en=fila.creado_en,
            id_fuente=fila.id_fuente, fuente=fila.fuente,
        )

    @classmethod
    def _a_cotizado(cls, fila) -> ActivoCotizado:
        cotizacion = None
        if fila.precio is not None:   # LEFT JOIN: sin cotización todas sus columnas vienen vacías
            cotizacion = Cotizacion(
                id_activo=fila.id_activo, precio=fila.precio,
                cierre_anterior=fila.cierre_anterior, variacion_pct_dia=fila.variacion_pct_dia,
                maximo_dia=fila.maximo_dia, minimo_dia=fila.minimo_dia,
                volumen_dia=fila.volumen_dia, actualizado_en=fila.actualizado_en,
            )
        return ActivoCotizado(activo=cls._a_activo(fila), cotizacion=cotizacion)
