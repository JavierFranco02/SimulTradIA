"""Ventanas emergentes de Administración · Activos: agregar y editar un activo.

Son vistas pasivas: no llaman a ningún servicio. ActivosAdminView las abre y les reenvía lo que
ordena el controlador (errores por campo, «ocupado»). Los errores de cada campo salen bajo el
campo; cualquier otro aviso es un diálogo sobre esta misma ventana.
"""
from typing import Callable, Dict, Sequence

from simultradia.iu.components import ActionButton, Dialogo, FormField, SelectField
from simultradia.iu.components.select_field import Opcion
from simultradia.iu.styles import ButtonStyle, Spacing


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


class EditarActivoDialog(Dialogo):
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
