"""Administración · Activos: catálogo de lo que se puede ver y operar, y de dónde viene cada uno."""
import tkinter as tk
from tkinter import messagebox
from typing import Callable, Dict, List, Optional, Tuple

import ttkbootstrap as ttk

from simultradia.domain.entities.cotizacion_entity import ActivoCotizado
from simultradia.domain.entities.fuente_entity import Fuente
from simultradia.iu.base.panel_view import PanelView
from simultradia.iu.components import ActionButton, DataTable, FormField, SelectField
from simultradia.iu.formato import TIPO_SINGULAR, hace, precio
from simultradia.iu.styles import ButtonStyle, Colors, Fonts, Spacing

_COLUMNAS = (
    ("ticker", "Ticker", 110, "w"),
    ("nombre", "Nombre", 170, "w"),
    ("tipo", "Tipo", 80, "center"),
    ("fuente", "Fuente", 110, "center"),
    ("precio", "Precio", 100, "e"),
    ("actualizado", "Último precio", 100, "center"),
    ("estado", "Estado", 100, "center"),
)


class ActivosAdminView(PanelView):
    def __init__(self, parent):
        super().__init__(parent, "Activos", "Qué activos hay en el simulador y de qué fuente salen sus precios")
        self._al_agregar: Optional[Callable[[], None]] = None
        self._al_cambiar_estado: Optional[Callable[[int, bool], None]] = None
        self._al_cambiar_fuente: Optional[Callable[[int, int], None]] = None
        self._al_probar_ticker: Optional[Callable[[], None]] = None
        self._al_probar_fuente: Optional[Callable[[str, str, int], None]] = None
        self._al_filtrar: Optional[Callable[[], None]] = None
        self._al_editar: Optional[Callable[[int, str, str], None]] = None
        self._items: Dict[str, ActivoCotizado] = {}

        ttk.Label(self, text="Agregar activo", font=Fonts.HEADING).pack(anchor="w")
        formulario = ttk.Frame(self)
        formulario.pack(fill="x", pady=(0, Spacing.MD))
        self._tipo = SelectField(formulario, "Tipo", [(t.value, texto) for t, texto in TIPO_SINGULAR.items()], ancho=16)
        self._fuente = SelectField(formulario, "Fuente de datos", ancho=20)
        self._ticker = FormField(formulario, "Ticker (según la fuente: BTC/USDT, AAPL, EURUSD=X...)", ancho=30)
        self._nombre = FormField(formulario, "Nombre (ej. Apple)", ancho=26)
        self._boton_agregar = ActionButton(formulario, "Agregar", self._pulsar_agregar, "Verificando...")
        self._boton_probar = ActionButton(formulario, "Probar ticker", self._pulsar_probar_ticker,
                                          estilo=ButtonStyle.LINK)
        self._tipo.grid(row=0, column=0, sticky="ew", padx=(0, Spacing.MD))
        self._fuente.grid(row=0, column=1, sticky="ew", padx=(0, Spacing.MD))
        self._ticker.grid(row=1, column=0, columnspan=2, sticky="new", padx=(0, Spacing.MD))
        self._nombre.grid(row=1, column=2, sticky="new", padx=(0, Spacing.MD))
        self._boton_agregar.grid(row=1, column=3, sticky="n", pady=(Spacing.LG, 0))
        self._boton_probar.grid(row=1, column=4, sticky="n", pady=(Spacing.LG, 0))
        self._campos = {"ticker": self._ticker, "nombre": self._nombre}
        self._nombre.al_presionar_enter(self._pulsar_agregar)

        filtros = ttk.Frame(self)
        filtros.pack(fill="x", pady=(0, Spacing.SM))
        ttk.Label(filtros, text="Buscar", font=Fonts.BODY).pack(side="left", padx=(0, Spacing.SM))
        self._busqueda = tk.StringVar(master=self)
        ttk.Entry(filtros, textvariable=self._busqueda, width=26, font=Fonts.BODY).pack(side="left")
        self._busqueda.trace_add("write", lambda *_args: self._pulsar_filtrar())
        self._tipo_filtro = SelectField(filtros, None, [("todos", "Todos los tipos")]
                                        + [(t.value, texto) for t, texto in TIPO_SINGULAR.items()], ancho=16)
        self._tipo_filtro.pack(side="left", padx=(Spacing.MD, 0))
        self._tipo_filtro.al_cambiar(self._pulsar_filtrar)
        self._estado_filtro = SelectField(filtros, None, [("todos", "Cualquier estado"),
                                                          ("habilitados", "Habilitados"),
                                                          ("deshabilitados", "Deshabilitados")], ancho=16)
        self._estado_filtro.pack(side="left", padx=(Spacing.SM, 0))
        self._estado_filtro.al_cambiar(self._pulsar_filtrar)

        barra = ttk.Frame(self)
        barra.pack(fill="x", pady=(0, Spacing.SM))
        self._boton_estado = ActionButton(barra, "Selecciona un activo", self._pulsar_estado)
        self._boton_estado.pack(side="left")
        self._boton_estado.configure(state="disabled")
        self._boton_fuente = ActionButton(barra, "Cambiar fuente", self._pulsar_fuente,
                                          estilo=ButtonStyle.DANGER_OUTLINE)
        self._boton_fuente.pack(side="right")
        self._boton_fuente.configure(state="disabled")
        self._fuente_nueva = SelectField(barra, None, ancho=20)
        self._fuente_nueva.pack(side="right", padx=(0, Spacing.SM))
        ttk.Label(barra, text="Pasar el activo elegido a:", font=Fonts.BODY,
                  bootstyle=Colors.MUTED).pack(side="right", padx=(0, Spacing.SM))

        self._boton_probar_fuente = ActionButton(barra, "Probar", self._pulsar_probar_fuente,
                                                 estilo=ButtonStyle.LINK)
        self._boton_probar_fuente.pack(side="right", padx=(0, Spacing.SM))
        self._boton_probar_fuente.configure(state="disabled")

        edicion = ttk.Frame(self)
        edicion.pack(fill="x", pady=(0, Spacing.SM))
        ttk.Label(edicion, text="Editar el activo elegido:", font=Fonts.BODY,
                  bootstyle=Colors.MUTED).pack(side="left", padx=(0, Spacing.SM))
        self._editar_nombre = FormField(edicion, "Nombre", ancho=28)
        self._editar_nombre.pack(side="left", padx=(0, Spacing.MD))
        self._editar_moneda = FormField(edicion, "Moneda (3 letras)", ancho=8)
        self._editar_moneda.pack(side="left", padx=(0, Spacing.MD))
        self._boton_editar = ActionButton(edicion, "Guardar cambios", self._pulsar_editar)
        self._boton_editar.pack(side="left", pady=(Spacing.LG, 0), anchor="s")
        self._boton_editar.configure(state="disabled")
        self._campos_edicion = {"nombre": self._editar_nombre, "moneda": self._editar_moneda}

        self._tabla = DataTable(self, _COLUMNAS)
        self._tabla.pack(fill="both", expand=True)
        self._tabla.al_seleccionar(lambda _iid: self._al_elegir_fila())
        ttk.Label(self, text="Un activo deshabilitado deja de actualizarse y de aparecer en Mercado. "
                             "Al cambiar su fuente se borran sus velas guardadas y se descargan de nuevo.",
                  font=Fonts.SMALL, bootstyle=Colors.MUTED).pack(anchor="w", pady=(Spacing.SM, 0))

    def vincular_acciones(self, al_agregar: Callable[[], None],
                          al_cambiar_estado: Callable[[int, bool], None],
                          al_cambiar_fuente: Callable[[int, int], None],
                          al_probar_ticker: Callable[[], None],
                          al_probar_fuente: Callable[[str, str, int], None],
                          al_filtrar: Callable[[], None],
                          al_editar: Callable[[int, str, str], None]) -> None:
        self._al_agregar = al_agregar
        self._al_cambiar_estado = al_cambiar_estado
        self._al_cambiar_fuente = al_cambiar_fuente
        self._al_probar_ticker = al_probar_ticker
        self._al_probar_fuente = al_probar_fuente
        self._al_filtrar = al_filtrar
        self._al_editar = al_editar

    def confirmar(self, mensaje: str) -> bool:
        return messagebox.askyesno("Confirmar", mensaje, parent=self)

    # --------------------------------------------- lo que el controlador lee
    def valores(self) -> Dict[str, str]:
        datos = {clave: campo.obtener() for clave, campo in self._campos.items()}
        datos["tipo"] = self._tipo.obtener() or ""
        datos["fuente"] = self._fuente.obtener() or ""
        return datos

    def filtros(self) -> Tuple[str, Optional[str], Optional[bool]]:
        """(texto buscado, tipo o None, estado como True/False o None)."""
        tipo = self._tipo_filtro.obtener()
        return (self._busqueda.get(), None if tipo in (None, "todos") else tipo,
                {"habilitados": True, "deshabilitados": False}.get(self._estado_filtro.obtener()))

    @property
    def ocupado(self) -> bool:
        return self._boton_agregar.ocupado

    # ------------------------------------------- lo que el controlador ordena
    def establecer_ocupado(self, ocupado: bool) -> None:
        self._boton_agregar.establecer_ocupado(ocupado)

    def establecer_fuentes(self, fuentes: List[Fuente]) -> None:
        opciones = [(str(f.id_fuente), f.nombre) for f in fuentes]
        self._fuente.establecer_opciones(opciones)
        self._fuente_nueva.establecer_opciones(opciones)

    def mostrar_errores_campos(self, errores: Dict[str, str]) -> None:
        for clave, texto in errores.items():
            campo = self._campos.get(clave)
            if campo is None:     # "tipo" y "fuente" no tienen línea propia: van al mensaje general
                self.mostrar_error(texto)
            else:
                campo.mostrar_error(texto)

    def limpiar_errores(self) -> None:
        self.limpiar_mensaje()
        for campo in self._campos.values():
            campo.ocultar_error()

    def limpiar_formulario(self) -> None:
        for campo in self._campos.values():
            campo.limpiar()
        self._ticker.enfocar()

    def mostrar_activos(self, items: List[ActivoCotizado]) -> None:
        self._items = {str(i.activo.id_activo): i for i in items}
        self._tabla.establecer_filas([
            (str(i.activo.id_activo),
             (i.activo.ticker, i.activo.nombre, TIPO_SINGULAR[i.activo.tipo], i.activo.fuente,
              precio(i.cotizacion.precio) if i.cotizacion else "—",
              hace(i.cotizacion.actualizado_en) if i.cotizacion else "—",
              "Habilitado" if i.activo.activo else "Deshabilitado"),
             "" if i.activo.activo else "baja")
            for i in items
        ])
        self._actualizar_botones()

    def _elegido(self) -> Optional[ActivoCotizado]:
        iid = self._tabla.seleccionado()
        return self._items.get(iid) if iid is not None else None

    def _al_elegir_fila(self) -> None:
        """Al elegir una fila, sus datos pasan al cuadro de edición."""
        elegido = self._elegido()
        if elegido is not None:
            self._editar_nombre.establecer(elegido.activo.nombre)
            self._editar_moneda.establecer(elegido.activo.moneda)
        self._actualizar_botones()

    def _actualizar_botones(self) -> None:
        elegido = self._elegido()
        hay = elegido is not None
        self._boton_fuente.configure(state="normal" if hay else "disabled")
        self._boton_probar_fuente.configure(state="normal" if hay else "disabled")
        self._boton_editar.configure(state="normal" if hay else "disabled")
        if not hay:
            self._boton_estado.configure(state="disabled", text="Selecciona un activo",
                                         bootstyle=ButtonStyle.PRIMARY)
        elif elegido.activo.activo:
            self._boton_estado.configure(state="normal", text="Deshabilitar activo",
                                         bootstyle=ButtonStyle.DANGER_OUTLINE)
        else:
            self._boton_estado.configure(state="normal", text="Habilitar activo",
                                         bootstyle=ButtonStyle.SUCCESS_OUTLINE)

    def mostrar_errores_edicion(self, errores: Dict[str, str]) -> None:
        for clave, texto in errores.items():
            campo = self._campos_edicion.get(clave)
            if campo is None:
                self.mostrar_error(texto)
            else:
                campo.mostrar_error(texto)

    def limpiar_errores_edicion(self) -> None:
        for campo in self._campos_edicion.values():
            campo.ocultar_error()

    def _pulsar_filtrar(self) -> None:
        if self._al_filtrar:
            self._al_filtrar()

    def _pulsar_probar_ticker(self) -> None:
        if self._al_probar_ticker:
            self._al_probar_ticker()

    def _pulsar_probar_fuente(self) -> None:
        elegido, fuente = self._elegido(), self._fuente_nueva.obtener()
        if elegido is not None and fuente is not None and self._al_probar_fuente:
            self._al_probar_fuente(elegido.activo.ticker, elegido.activo.tipo.value, int(fuente))

    def _pulsar_editar(self) -> None:
        elegido = self._elegido()
        if elegido is not None and self._al_editar:
            self._al_editar(elegido.activo.id_activo, self._editar_nombre.obtener(),
                            self._editar_moneda.obtener())

    def _pulsar_agregar(self) -> None:
        if self._al_agregar:
            self._al_agregar()

    def _pulsar_estado(self) -> None:
        elegido = self._elegido()
        if elegido is not None and self._al_cambiar_estado:
            self._al_cambiar_estado(elegido.activo.id_activo, not elegido.activo.activo)

    def _pulsar_fuente(self) -> None:
        elegido, fuente = self._elegido(), self._fuente_nueva.obtener()
        if elegido is not None and fuente is not None and self._al_cambiar_fuente:
            self._al_cambiar_fuente(elegido.activo.id_activo, int(fuente))
