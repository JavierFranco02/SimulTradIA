"""Acceso a la tabla "fuentes_datos" (de dónde vienen los precios). Aquí vive su SQL."""
from typing import List, Optional

from simultradia.domain.entities.fuente_entity import Fuente

_SELECT = """
    SELECT f.id_fuente, f.nombre, f.activa,
           COUNT(a.id_activo) AS total_activos,
           MAX(c.actualizado_en) AS ultima_cotizacion
    FROM fuentes_datos f
    LEFT JOIN activos a ON a.id_fuente = f.id_fuente AND a.activo
    LEFT JOIN cotizaciones_actuales c ON c.id_activo = a.id_activo"""
_AGRUPAR = " GROUP BY f.id_fuente, f.nombre, f.activa"


class FuenteRepository:
    def listar(self, conn) -> List[Fuente]:
        with conn.cursor() as cur:
            cur.execute(_SELECT + _AGRUPAR + " ORDER BY f.nombre")
            return [self._a_entidad(fila) for fila in cur.fetchall()]

    def buscar_por_id(self, conn, id_fuente: int) -> Optional[Fuente]:
        with conn.cursor() as cur:
            cur.execute(_SELECT + " WHERE f.id_fuente = %s" + _AGRUPAR, (id_fuente,))
            fila = cur.fetchone()
        return self._a_entidad(fila) if fila else None

    def establecer_activa(self, conn, id_fuente: int, activa: bool) -> bool:
        with conn.cursor() as cur:
            cur.execute("UPDATE fuentes_datos SET activa = %s WHERE id_fuente = %s", (activa, id_fuente))
            return cur.rowcount > 0

    @staticmethod
    def _a_entidad(fila) -> Fuente:
        return Fuente(id_fuente=fila.id_fuente, nombre=fila.nombre, activa=fila.activa,
                      total_activos=fila.total_activos, ultima_cotizacion=fila.ultima_cotizacion)
