"""Lista de activos de Mercado (el panel izquierdo): buscador, categoría, pestañas y tabla.

Vista pasiva: dibuja y expone métodos; ListaController decide qué pedir y cuándo.
"""
import tkinter as tk
from typing import Callable, Dict, Optional

import ttkbootstrap as ttk

from simultradia.domain.entities.cotizacion_entity import PanelMercado
from simultradia.domain.enums import TipoActivo
from simultradia.iu.base.panel_view import PanelView
from simultradia.iu.components import DataTable, SelectField
from simultradia.iu.formato import TIPO_PLURAL, hace, porcentaje, precio
from simultradia.iu.styles import ButtonStyle, Colors, Fonts, Spacing

_PESTANAS = (("todos", "Todos"), ("ganadores", "Suben"), ("perdedores", "Bajan"), ("volumen", "Volumen"))
_COLUMNAS = (
    ("ticker", "Activo", 120, "w"),
    ("precio", "Precio", 110, "e"),
    ("variacion", "Var. %", 90, "e"),
)


class ListaActivosView(PanelView):
    def __init__(self, parent):
        super().__init__(parent, padding=Spacing.SM)
        self._al_filtrar: Optional[Callable[[], None]] = None
        self._al_elegir_pestana: Optional[Callable[[str], None]] = None
        self._al_ordenar: Optional[Callable[[str], None]] = None
        self._al_elegir_activo: Optional[Callable[[int], None]] = None

        fila = ttk.Frame(self)
        fila.pack(fill="x", pady=(0, Spacing.SM))
        ttk.Label(fila, text="Buscar", font=Fonts.BODY).pack(side="left", padx=(0, Spacing.SM))
        self._busqueda = tk.StringVar(master=self)
        ttk.Entry(fila, textvariable=self._busqueda, font=Fonts.BODY).pack(side="left", fill="x", expand=True)
        self._busqueda.trace_add("write", lambda *_args: self._pulsar_filtrar())

        self._categoria = SelectField(
            self, None, [("todas", "Todas las categorías")]
            + [(tipo.value, texto) for tipo, texto in TIPO_PLURAL.items()])
        self._categoria.pack(fill="x", pady=(0, Spacing.SM))
        self._categoria.al_cambiar(self._pulsar_filtrar)

        pestanas = ttk.Frame(self)
        pestanas.pack(fill="x", pady=(0, Spacing.SM))
        self._pestana = tk.StringVar(master=self, value="todos")
        for columna, (clave, texto) in enumerate(_PESTANAS):
            pestanas.columnconfigure(columna, weight=1, uniform="pestana")
            ttk.Radiobutton(pestanas, text=texto, value=clave, variable=self._pestana,
                            command=self._pulsar_pestana, bootstyle=ButtonStyle.TOGGLE
                            ).grid(row=0, column=columna, sticky="ew")

        self._tabla = DataTable(self, _COLUMNAS)
        self._tabla.pack(fill="both", expand=True)
        self._tabla.al_seleccionar(self._pulsar_activo)
        self._tabla.al_clic_encabezado(self._pulsar_encabezado)
        self._pie = ttk.Label(self, text="", font=Fonts.SMALL, bootstyle=Colors.MUTED)
        self._pie.pack(anchor="w", pady=(Spacing.SM, 0))

    def vincular_acciones(self, al_filtrar: Callable[[], None],
                          al_elegir_pestana: Callable[[str], None],
                          al_ordenar: Callable[[str], None],
                          al_elegir_activo: Callable[[int], None]) -> None:
        self._al_filtrar = al_filtrar
        self._al_elegir_pestana = al_elegir_pestana
        self._al_ordenar = al_ordenar
        self._al_elegir_activo = al_elegir_activo

    # --------------------------------------------- lo que el controlador lee
    def texto_busqueda(self) -> str:
        return self._busqueda.get()

    def categoria(self) -> Optional[TipoActivo]:
        clave = self._categoria.obtener()
        return None if clave in (None, "todas") else TipoActivo(clave)

    # ------------------------------------------- lo que el controlador ordena
    def mostrar_panel(self, panel: PanelMercado, orden: str, descendente: bool) -> None:
        filas = []
        for item in panel.items:
            c = item.cotizacion
            if c is None:
                valores, etiqueta = (item.activo.ticker, "—", "—"), ""
            else:
                v = c.variacion_pct_dia
                valores = (item.activo.ticker, precio(c.precio),
                           porcentaje(v, con_signo=True) if v is not None else "—")
                etiqueta = "alza" if v and v > 0 else "baja" if v and v < 0 else ""
            filas.append((str(item.activo.id_activo), valores, etiqueta))
        self._tabla.establecer_filas(filas)
        self._tabla.marcar_orden(orden, descendente)

        if panel.actualizado_en is None:
            self.mostrar_error("Aún no hay precios guardados. Abre otra terminal y ejecuta: python worker.py")
            self._pie.configure(text="")
        else:
            self.limpiar_mensaje()
            self._pie.configure(text="%d activos · actualizado %s" % (len(panel.items), hace(panel.actualizado_en)))

    def seleccionar(self, id_activo: int) -> None:
        self._tabla.seleccionar(str(id_activo))

    # --------------------------------------------------------- eventos de la UI
    def _pulsar_filtrar(self) -> None:
        if self._al_filtrar:
            self._al_filtrar()

    def _pulsar_pestana(self) -> None:
        if self._al_elegir_pestana:
            self._al_elegir_pestana(self._pestana.get())

    def _pulsar_encabezado(self, clave: str) -> None:
        if self._al_ordenar:
            self._al_ordenar(clave)

    def _pulsar_activo(self, iid: Optional[str]) -> None:
        if iid is not None and self._al_elegir_activo:
            self._al_elegir_activo(int(iid))
