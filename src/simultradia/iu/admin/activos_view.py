"""Administración · Activos: catálogo de lo que se puede ver y operar, y de dónde viene cada uno.

Agregar y editar se hacen en ventanas emergentes (activo_dialogs.py): esta vista las abre y les
reenvía los errores y mensajes que ordena el controlador.
"""
import tkinter as tk
from tkinter import messagebox
from typing import Callable, Dict, List, Optional, Tuple

import ttkbootstrap as ttk

from simultradia.domain.entities.cotizacion_entity import ActivoCotizado
from simultradia.domain.entities.fuente_entity import Fuente
from simultradia.iu.admin.activo_dialogs import AgregarActivoDialog, EditarActivoDialog
from simultradia.iu.base.panel_view import PanelView
from simultradia.iu.components import ActionButton, DataTable, SelectField
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
        self._opciones_fuentes: List[Tuple[str, str]] = []
        self._dialogo_agregar: Optional[AgregarActivoDialog] = None
        self._dialogo_editar: Optional[EditarActivoDialog] = None

        filtros = ttk.Frame(self)
        filtros.pack(fill="x", pady=(0, Spacing.SM))
        ttk.Label(filtros, text="Buscar", font=Fonts.BODY).pack(side="left", padx=(0, Spacing.SM))
        self._busqueda = tk.StringVar(master=self)
        ttk.Entry(filtros, textvariable=self._busqueda, width=22, font=Fonts.BODY).pack(side="left")
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
        ActionButton(filtros, "+ Agregar activo", self._abrir_agregar).pack(side="right")

        barra = ttk.Frame(self)
        barra.pack(fill="x", pady=(0, Spacing.SM))
        self._boton_editar = ActionButton(barra, "Editar activo", self._abrir_editar)
        self._boton_editar.pack(side="left")
        self._boton_editar.configure(state="disabled")
        self._boton_estado = ActionButton(barra, "Deshabilitar activo", self._pulsar_estado)
        self._boton_estado.pack(side="left", padx=(Spacing.SM, 0))
        self._boton_estado.configure(state="disabled")

        self._boton_fuente = ActionButton(barra, "Cambiar fuente", self._pulsar_fuente,
                                          estilo=ButtonStyle.DANGER_OUTLINE)
        self._boton_fuente.pack(side="right")
        self._boton_fuente.configure(state="disabled")
        self._fuente_nueva = SelectField(barra, None, ancho=14)
        self._fuente_nueva.pack(side="right", padx=(0, Spacing.SM))
        ttk.Label(barra, text="Pasar a:", font=Fonts.BODY,
                  bootstyle=Colors.MUTED).pack(side="right", padx=(0, Spacing.SM))
        self._boton_probar_fuente = ActionButton(barra, "Probar", self._pulsar_probar_fuente,
                                                 estilo=ButtonStyle.LINK)
        self._boton_probar_fuente.pack(side="right", padx=(0, Spacing.SM))
        self._boton_probar_fuente.configure(state="disabled")

        self._tabla = DataTable(self, _COLUMNAS)
        self._tabla.pack(fill="both", expand=True)
        self._tabla.al_seleccionar(lambda _iid: self._actualizar_botones())
        self._tabla.al_doble_clic(lambda _iid: self._abrir_editar())
        ttk.Label(self, text="Doble clic en un activo para editarlo. Un activo deshabilitado deja de actualizarse "
                             "y de aparecer en Mercado. Al cambiar su fuente se borran sus velas guardadas y "
                             "se descargan de nuevo.",
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

    # --------------------------------------------- ventanas emergentes
    @staticmethod
    def _vivo(dialogo) -> bool:
        return dialogo is not None and dialogo.esta_viva()

    def _abrir_agregar(self) -> None:
        self._mensaje.limpiar()
        self._dialogo_agregar = AgregarActivoDialog(
            self, [(t.value, texto) for t, texto in TIPO_SINGULAR.items()], self._opciones_fuentes,
            al_agregar=self._pulsar_agregar, al_probar=self._pulsar_probar_ticker)

    def _abrir_editar(self) -> None:
        elegido = self._elegido()
        if elegido is None:
            return
        self._mensaje.limpiar()
        a = elegido.activo
        self._dialogo_editar = EditarActivoDialog(
            self, a.id_activo, a.ticker, a.nombre, a.moneda, al_guardar=self._pulsar_editar)

    def _destino(self):
        """Los mensajes van a la ventana emergente abierta; si no hay ninguna, al panel."""
        for dialogo in (self._dialogo_agregar, self._dialogo_editar):
            if self._vivo(dialogo):
                return dialogo.mensaje
        return self._mensaje

    def mostrar_error(self, texto: str) -> None:
        self._destino().mostrar_error(texto)

    def mostrar_exito(self, texto: str) -> None:
        self._destino().mostrar_exito(texto)

    def limpiar_mensaje(self) -> None:
        self._destino().limpiar()

    # --------------------------------------------- lo que el controlador lee
    def valores(self) -> Dict[str, str]:
        if self._vivo(self._dialogo_agregar):
            return self._dialogo_agregar.valores()
        return {"ticker": "", "nombre": "", "tipo": "", "fuente": ""}

    def filtros(self) -> Tuple[str, Optional[str], Optional[bool]]:
        """(texto buscado, tipo o None, estado como True/False o None)."""
        tipo = self._tipo_filtro.obtener()
        return (self._busqueda.get(), None if tipo in (None, "todos") else tipo,
                {"habilitados": True, "deshabilitados": False}.get(self._estado_filtro.obtener()))

    @property
    def ocupado(self) -> bool:
        return self._vivo(self._dialogo_agregar) and self._dialogo_agregar.boton_agregar.ocupado

    # ------------------------------------------- lo que el controlador ordena
    def establecer_ocupado(self, ocupado: bool) -> None:
        if self._vivo(self._dialogo_agregar):
            self._dialogo_agregar.boton_agregar.establecer_ocupado(ocupado)

    def establecer_fuentes(self, fuentes: List[Fuente]) -> None:
        self._opciones_fuentes = [(str(f.id_fuente), f.nombre) for f in fuentes]
        self._fuente_nueva.establecer_opciones(self._opciones_fuentes)
        if self._vivo(self._dialogo_agregar):
            self._dialogo_agregar.establecer_fuentes(self._opciones_fuentes)

    def mostrar_errores_campos(self, errores: Dict[str, str]) -> None:
        if self._vivo(self._dialogo_agregar):
            self._dialogo_agregar.mostrar_errores(errores)
        else:
            for texto in errores.values():
                self.mostrar_error(texto)

    def limpiar_errores(self) -> None:
        if self._vivo(self._dialogo_agregar):
            self._dialogo_agregar.limpiar_errores()

    def limpiar_formulario(self) -> None:
        """Se agregó el activo: se cierra la ventana."""
        if self._vivo(self._dialogo_agregar):
            self._dialogo_agregar.destroy()
        self._dialogo_agregar = None

    def mostrar_errores_edicion(self, errores: Dict[str, str]) -> None:
        if self._vivo(self._dialogo_editar):
            self._dialogo_editar.mostrar_errores(errores)
        else:
            for texto in errores.values():
                self.mostrar_error(texto)

    def limpiar_errores_edicion(self) -> None:
        if self._vivo(self._dialogo_editar):
            self._dialogo_editar.limpiar_errores()

    def cerrar_edicion(self) -> None:
        if self._vivo(self._dialogo_editar):
            self._dialogo_editar.destroy()
        self._dialogo_editar = None

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

    def _actualizar_botones(self) -> None:
        elegido = self._elegido()
        hay = elegido is not None
        estado = "normal" if hay else "disabled"
        self._boton_fuente.configure(state=estado)
        self._boton_probar_fuente.configure(state=estado)
        self._boton_editar.configure(state=estado)
        if not hay:
            self._boton_estado.configure(state="disabled", text="Deshabilitar activo",
                                         bootstyle=ButtonStyle.PRIMARY)
        elif elegido.activo.activo:
            self._boton_estado.configure(state="normal", text="Deshabilitar activo",
                                         bootstyle=ButtonStyle.DANGER_OUTLINE)
        else:
            self._boton_estado.configure(state="normal", text="Habilitar activo",
                                         bootstyle=ButtonStyle.SUCCESS_OUTLINE)

    # --------------------------------------------------------- eventos de la UI
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

    def _pulsar_editar(self, id_activo: int, nombre: str, moneda: str) -> None:
        if self._al_editar:
            self._al_editar(id_activo, nombre, moneda)

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
