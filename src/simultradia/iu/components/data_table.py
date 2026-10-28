"""Tabla de datos (Treeview) con encabezados que se pueden pulsar para ordenar.

    tabla = DataTable(padre, [("ticker", "Activo", 200, "w"), ("precio", "Precio", 120, "e")])
    tabla.establecer_filas([("5", ("BTC/USDT", "67 123,45"), "alza")])

Cada fila es (id, textos de cada columna, etiqueta). La etiqueta ("alza", "baja" o "") pinta
el texto de verde o rojo. Al refrescar, las filas se actualizan EN SU LUGAR: no se pierde la
fila seleccionada ni el desplazamiento aunque la tabla se renueve cada pocos segundos.
"""
from typing import Callable, Optional, Sequence, Tuple

import ttkbootstrap as ttk

from simultradia.iu.styles import Palette

Columna = Tuple[str, str, int, str]            # (clave, título, ancho, alineación "w"/"e"/"center")
Fila = Tuple[str, Sequence[str], str]          # (id, textos, etiqueta)


class DataTable(ttk.Frame):
    def __init__(self, parent, columnas: Sequence[Columna]):
        super().__init__(parent)
        self._titulos = {clave: titulo for clave, titulo, _ancho, _ancla in columnas}
        self._tabla = ttk.Treeview(self, columns=[c[0] for c in columnas], show="headings",
                                   selectmode="browse", bootstyle="primary")
        ttk.Style().configure("Treeview", rowheight=30)   # filas más altas = más fáciles de leer
        for clave, titulo, ancho, ancla in columnas:
            self._tabla.heading(clave, text=titulo, anchor=ancla)
            self._tabla.column(clave, width=ancho, anchor=ancla)
        self._tabla.tag_configure("alza", foreground=Palette.ALZA)
        self._tabla.tag_configure("baja", foreground=Palette.BAJA)
        barra = ttk.Scrollbar(self, orient="vertical", command=self._tabla.yview)
        self._tabla.configure(yscrollcommand=barra.set)
        self._tabla.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")

    def establecer_filas(self, filas: Sequence[Fila]) -> None:
        existentes = set(self._tabla.get_children())
        nuevos = {iid for iid, _v, _e in filas}
        for iid in existentes - nuevos:
            self._tabla.delete(iid)
        for posicion, (iid, valores, etiqueta) in enumerate(filas):
            etiquetas = (etiqueta,) if etiqueta else ()
            if iid in existentes:
                self._tabla.item(iid, values=tuple(valores), tags=etiquetas)
                self._tabla.move(iid, "", posicion)
            else:
                self._tabla.insert("", posicion, iid=iid, values=tuple(valores), tags=etiquetas)

    def seleccionado(self) -> Optional[str]:
        seleccion = self._tabla.selection()
        return seleccion[0] if seleccion else None

    def seleccionar(self, iid: str) -> None:
        """Elige una fila (y avisa a quien escuche `al_seleccionar`, como si la hubieran pulsado)."""
        if self._tabla.exists(iid):
            self._tabla.selection_set(iid)
            self._tabla.see(iid)

    def al_seleccionar(self, accion: Callable[[Optional[str]], None]) -> None:
        self._tabla.bind("<<TreeviewSelect>>", lambda _e: accion(self.seleccionado()))

    def al_doble_clic(self, accion: Callable[[str], None]) -> None:
        def _doble_clic(evento) -> None:
            iid = self._tabla.identify_row(evento.y)
            if iid:
                accion(iid)
        self._tabla.bind("<Double-1>", _doble_clic)

    def al_clic_encabezado(self, accion: Callable[[str], None]) -> None:
        for clave in self._titulos:
            self._tabla.heading(clave, command=lambda c=clave: accion(c))

    def marcar_orden(self, clave: Optional[str], descendente: bool) -> None:
        """Pone una flecha ▲/▼ en el encabezado de la columna por la que se ordena."""
        for k, titulo in self._titulos.items():
            flecha = (" ▼" if descendente else " ▲") if k == clave else ""
            self._tabla.heading(k, text=titulo + flecha)
