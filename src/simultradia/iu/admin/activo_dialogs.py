"""Ventanas emergentes de Administración · Activos: agregar y editar un activo.

Son vistas pasivas: no llaman a ningún servicio. ActivosAdminView las abre y les reenvía lo que
ordena el controlador (errores por campo, «ocupado»). Los errores de cada campo salen bajo el
campo; cualquier otro aviso es un diálogo sobre esta misma ventana.
"""
import tkinter as tk
from tkinter import messagebox
from typing import Callable, Dict, Sequence

import ttkbootstrap as ttk

from simultradia.iu.components import ActionButton, FormField, SelectField
from simultradia.iu.components.select_field import Opcion
from simultradia.iu.styles import ButtonStyle, Fonts, Spacing


class _Dialogo(tk.Toplevel):
    """Base: ventana modal centrada sobre la principal, con título y botones."""

    def __init__(self, padre, titulo: str):
        super().__init__(padre)
        self.title(titulo)
        self.resizable(False, False)
        self.transient(padre.winfo_toplevel())
        self.bind("<Escape>", lambda _evento: self.destroy())
        self._campos: Dict[str, FormField] = {}   # clave del servicio -> campo (lo llenan las hijas)

        cuerpo = ttk.Frame(self, padding=Spacing.LG)   # cubre toda la ventana con el fondo del tema
        cuerpo.pack(fill="both", expand=True)
        ttk.Label(cuerpo, text=titulo, font=Fonts.HEADING).pack(anchor="w")
        self.formulario = ttk.Frame(cuerpo)
        self.formulario.pack(fill="x")
        self.botones = ttk.Frame(cuerpo)
        self.botones.pack(fill="x", pady=(Spacing.MD, 0))
        ActionButton(self.botones, "Cancelar", self.destroy, estilo=ButtonStyle.LINK).pack(side="left")

    def _presentar(self) -> None:
        """Se llama al final del constructor de cada hija: centra la ventana y la hace modal."""
        self.update_idletasks()
        ventana = self.master.winfo_toplevel()
        x = ventana.winfo_rootx() + (ventana.winfo_width() - self.winfo_reqwidth()) // 2
        y = ventana.winfo_rooty() + (ventana.winfo_height() - self.winfo_reqheight()) // 3
        self.geometry("+%d+%d" % (max(x, 0), max(y, 0)))
        self.wait_visibility()
        self.grab_set()

    def esta_viva(self) -> bool:
        return bool(self.winfo_exists())

    def mostrar_error(self, texto: str) -> None:
        messagebox.showerror("Error", texto, parent=self)

    def mostrar_errores(self, errores: Dict[str, str]) -> None:
        """Cada mensaje bajo su campo; si no es de un campo de esta ventana, en un diálogo."""
        for clave, texto in errores.items():
            campo = self._campos.get(clave)
            if campo is None:
                self.mostrar_error(texto)
            else:
                campo.mostrar_error(texto)

    def limpiar_errores(self) -> None:
        for campo in self._campos.values():
            campo.ocultar_error()


class AgregarActivoDialog(Dialogo):
    def __init__(self, padre, tipos: Sequence[Opcion], fuentes: Sequence[Opcion],
                 al_agregar: Callable[[], None], al_probar: Callable[[], None]):
        super().__init__(padre, "Agregar activo")
        self._tipo = SelectField(self.formulario, "Tipo", tipos)
        self._fuente = SelectField(self.formulario, "Fuente de datos", fuentes)
        self._ticker = FormField(self.formulario, "Ticker (según la fuente: BTC/USDT, AAPL, EURUSD=X...)", ancho=40)
        self._nombre = FormField(self.formulario, "Nombre (ej. Apple)", ancho=40)
        for campo in (self._tipo, self._fuente, self._ticker, self._nombre):
            campo.pack(fill="x")
        self._campos = {"ticker": self._ticker, "nombre": self._nombre}

        self.boton_agregar = ActionButton(self.botones, "Agregar", al_agregar, "Verificando...")
        self.boton_agregar.pack(side="right")
        ActionButton(self.botones, "Probar ticker", al_probar,
                     estilo=ButtonStyle.LINK).pack(side="right", padx=(0, Spacing.SM))
        self._nombre.al_presionar_enter(al_agregar)
        self._ticker.enfocar()
        self._presentar()

    def valores(self) -> Dict[str, str]:
        datos = {clave: campo.obtener() for clave, campo in self._campos.items()}
        datos["tipo"] = self._tipo.obtener() or ""
        datos["fuente"] = self._fuente.obtener() or ""
        return datos

    def establecer_fuentes(self, fuentes: Sequence[Opcion]) -> None:
        self._fuente.establecer_opciones(fuentes)


class EditarActivoDialog(_Dialogo):
    """Solo se edita el nombre: la moneda no se cambia por activo (no hay conversión)."""

    def __init__(self, padre, id_activo: int, ticker: str, nombre: str,
                 al_guardar: Callable[[int, str], None]):
        super().__init__(padre, "Editar %s" % ticker)
        self._nombre = FormField(self.formulario, "Nombre", ancho=40)
        self._nombre.pack(fill="x")
        self._nombre.establecer(nombre)
        self._campos = {"nombre": self._nombre}

        def guardar() -> None:
            al_guardar(id_activo, self._nombre.obtener())

        ActionButton(self.botones, "Guardar cambios", guardar).pack(side="right")
        self._nombre.al_presionar_enter(guardar)
        self._nombre.enfocar()
        self._presentar()
