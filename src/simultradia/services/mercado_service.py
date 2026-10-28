"""Casos de uso de la pantalla Mercado: listar, buscar, filtrar, ordenar y consultar un activo.

Con 20 a 30 activos es más simple y fácil de probar filtrar y ordenar aquí en Python que
escribir una consulta SQL distinta para cada combinación.
"""
from datetime import datetime
from typing import List, Optional

from simultradia.core.exceptions import ErrorOperacionInvalida
from simultradia.domain.entities.cotizacion_entity import ActivoCotizado, PanelMercado
from simultradia.domain.enums import TipoActivo

FILTROS = ("todos", "ganadores", "perdedores")
ORDENES = ("ticker", "nombre", "precio", "variacion", "volumen")


def _valor(item: ActivoCotizado, orden: str):
    """Lo que se compara al ordenar. None si el activo aún no tiene precio."""
    c = item.cotizacion
    if orden == "ticker":
        return item.activo.ticker
    if orden == "nombre":
        return item.activo.nombre.lower()
    if c is None:
        return None
    return {"precio": c.precio, "variacion": c.variacion_pct_dia, "volumen": c.volumen_dia}[orden]


class MercadoService:
    def __init__(self, db, activo_repository):
        self._db = db
        self._activos = activo_repository

    def obtener_panel(self, texto: str = "", filtro: str = "todos", orden: str = "ticker",
                      descendente: bool = False, tipo: Optional[TipoActivo] = None) -> PanelMercado:
        with self._db.obtener_conexion() as conn:
            todos = self._activos.listar_cotizados(conn, solo_activos=True)

        items = self._buscar(todos, (texto or "").strip().lower())
        if tipo is not None:
            items = [i for i in items if i.activo.tipo == tipo]
        if filtro == "ganadores":
            items = [i for i in items if i.cotizacion and (i.cotizacion.variacion_pct_dia or 0) > 0]
        elif filtro == "perdedores":
            items = [i for i in items if i.cotizacion and (i.cotizacion.variacion_pct_dia or 0) < 0]

        return PanelMercado(
            items=self._ordenar(items, orden, descendente),
            actualizado_en=self._ultima_actualizacion(todos),
        )

    def obtener_activo(self, id_activo: int) -> ActivoCotizado:
        """Un activo habilitado, con su cotización de ahora (lo que muestra el encabezado del gráfico)."""
        with self._db.obtener_conexion() as conn:
            item = self._activos.buscar_cotizado(conn, id_activo)
        if item is None or not item.activo.activo:
            raise ErrorOperacionInvalida("Ese activo no existe o está deshabilitado.")
        return item

    # --------------------------------------------------------------- interno
    @staticmethod
    def _buscar(items: List[ActivoCotizado], texto: str) -> List[ActivoCotizado]:
        if not texto:
            return list(items)
        return [i for i in items
                if texto in i.activo.ticker.lower() or texto in i.activo.nombre.lower()]

    @staticmethod
    def _ordenar(items: List[ActivoCotizado], orden: str, descendente: bool) -> List[ActivoCotizado]:
        if orden not in ORDENES:
            orden = "ticker"
        con_dato = [i for i in items if _valor(i, orden) is not None]
        sin_dato = [i for i in items if _valor(i, orden) is None]   # siempre al final
        con_dato.sort(key=lambda i: _valor(i, orden), reverse=descendente)
        return con_dato + sin_dato

    @staticmethod
    def _ultima_actualizacion(items: List[ActivoCotizado]) -> Optional[datetime]:
        momentos = [i.cotizacion.actualizado_en for i in items
                    if i.cotizacion and i.cotizacion.actualizado_en]
        return max(momentos) if momentos else None
