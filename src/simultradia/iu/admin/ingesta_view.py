"""Administración · Ingesta de datos: de dónde vienen los precios, si están al día y actualizar a mano."""
from datetime import datetime, timezone
from tkinter import messagebox
from typing import Callable, Dict, List, Optional

import ttkbootstrap as ttk

from simultradia.domain.entities.fuente_entity import Fuente
from simultradia.iu.base.panel_view import PanelView
from simultradia.iu.components import ActionButton, DataTable
from simultradia.iu.formato import hace
from simultradia.iu.styles import ButtonStyle, Colors, Fonts, Spacing
from simultradia.services.ingesta_service import EstadoIngesta

_FRESCO_SEGUNDOS = 30   # un precio más viejo que esto indica que el worker no está corriendo
_COLUMNAS = (
    ("nombre", "Fuente", 180, "w"),
    ("activos", "Activos", 90, "center"),
    ("ultimo", "Último precio recibido", 180, "center"),
    ("estado", "Estado", 110, "center"),
)


class IngestaView(PanelView):
    def __init__(self, parent):
        super().__init__(parent, "Ingesta de datos", "Fuentes de las que salen los precios y las velas")
        self._al_actualizar: Optional[Callable[[], None]] = None
        self._al_cambiar_fuente: Optional[Callable[[int, bool], None]] = None
        self._al_probar_fuente: Optional[Callable[[int], None]] = None
        self._al_actualizar_fuente: Optional[Callable[[int], None]] = None
        self._activas: Dict[str, bool] = {}
        self._ocupado = False

        # Tres datos sueltos: una fila de texto cada uno (no hace falta una tarjeta para eso).
        resumen = ttk.Frame(self)
        resumen.pack(fill="x", pady=(0, Spacing.MD))
        self._valores = {}
        for fila, (clave, titulo) in enumerate((("ultima", "Último precio recibido"),
                                                ("activos", "Activos habilitados"),
                                                ("velas", "Velas guardadas"))):
            ttk.Label(resumen, text=titulo, font=Fonts.BODY, bootstyle=Colors.MUTED
                      ).grid(row=fila, column=0, sticky="w", padx=(0, Spacing.LG), pady=2)
            self._valores[clave] = ttk.Label(resumen, text="—", font=Fonts.BODY)
            self._valores[clave].grid(row=fila, column=1, sticky="w", pady=2)

        ttk.Label(
            self, font=Fonts.SMALL, bootstyle=Colors.MUTED, justify="left",
            text="El proceso «python worker.py» mantiene los datos al día (cada fuente a su ritmo). Si no está\n"
                 "corriendo, puedes actualizar a mano con el botón de abajo; la primera vez descarga todo\n"
                 "el historial y puede tardar varios minutos.",
        ).pack(anchor="w", pady=(0, Spacing.MD))

        ttk.Label(self, text="Fuentes de datos", font=Fonts.HEADING).pack(anchor="w", pady=(0, Spacing.SM))
        self._tabla = DataTable(self, _COLUMNAS)
        self._tabla.pack(fill="both", expand=True)
        self._tabla.al_seleccionar(lambda _iid: self._actualizar_boton_fuente())

        barra = ttk.Frame(self)
        barra.pack(fill="x", pady=(Spacing.MD, 0))
        self._boton_fuente = ActionButton(barra, "Selecciona una fuente", self._pulsar_fuente)
        self._boton_fuente.pack(side="left")
        self._boton_fuente.configure(state="disabled")
        self._boton_probar = ActionButton(barra, "Probar conexión", self._pulsar_probar,
                                          estilo=ButtonStyle.LINK)
        self._boton_probar.pack(side="left", padx=(Spacing.SM, 0))
        self._boton_probar.configure(state="disabled")
        self._boton_una = ActionButton(barra, "Actualizar esta fuente", self._pulsar_actualizar_una,
                                       estilo=ButtonStyle.LINK)
        self._boton_una.pack(side="left", padx=(Spacing.SM, 0))
        self._boton_una.configure(state="disabled")
        self._boton = ActionButton(barra, "Actualizar todo ahora", self._pulsar_actualizar,
                                   "Actualizando... (puede tardar)")
        self._boton.pack(side="right")

    def vincular_acciones(self, al_actualizar: Callable[[], None],
                          al_cambiar_fuente: Callable[[int, bool], None],
                          al_probar_fuente: Callable[[int], None],
                          al_actualizar_fuente: Callable[[int], None]) -> None:
        self._al_actualizar = al_actualizar
        self._al_cambiar_fuente = al_cambiar_fuente
        self._al_probar_fuente = al_probar_fuente
        self._al_actualizar_fuente = al_actualizar_fuente

    def confirmar(self, mensaje: str) -> bool:
        return messagebox.askyesno("Confirmar", mensaje, parent=self)

    @property
    def ocupado(self) -> bool:
        return self._boton.ocupado

    def establecer_ocupado(self, ocupado: bool) -> None:
        """Mientras algo corre, los demás botones de acción quedan quietos para no lanzar dos cosas a la vez."""
        self._boton.establecer_ocupado(ocupado)
        self._ocupado = ocupado
        self._actualizar_boton_fuente()

    def mostrar_estado(self, estado: EstadoIngesta, fuentes: List[Fuente]) -> None:
        ultima = estado.ultima_cotizacion
        if ultima is None:
            self._valores["ultima"].configure(text="Nunca (ejecuta el worker)", bootstyle=Colors.DANGER)
        else:
            fresco = (datetime.now(timezone.utc) - ultima).total_seconds() <= _FRESCO_SEGUNDOS
            self._valores["ultima"].configure(
                text="%s · %s" % (hace(ultima), "al día" if fresco else "desactualizado"),
                bootstyle=Colors.SUCCESS if fresco else Colors.WARNING)
        self._valores["activos"].configure(text=str(estado.activos_habilitados))
        velas = estado.velas_por_intervalo
        detalle = "  (%s)" % " · ".join("%s: %d" % (k, v) for k, v in sorted(velas.items())) if velas else ""
        self._valores["velas"].configure(text="{:,}".format(sum(velas.values())).replace(",", "\u00a0") + detalle)

        self._activas = {str(f.id_fuente): f.activa for f in fuentes}
        self._tabla.establecer_filas([
            (str(f.id_fuente),
             (f.nombre, str(f.total_activos), hace(f.ultima_cotizacion), "Habilitada" if f.activa else "Deshabilitada"),
             "" if f.activa else "baja")
            for f in fuentes
        ])
        self._actualizar_boton_fuente()

    def _actualizar_boton_fuente(self) -> None:
        iid = self._tabla.seleccionado()
        elegida = iid is not None and iid in self._activas
        libre = "disabled" if self._ocupado else "normal"
        self._boton_probar.configure(state=libre if elegida else "disabled")
        self._boton_una.configure(state=libre if elegida and self._activas[iid] else "disabled")
        if not elegida:
            self._boton_fuente.configure(state="disabled", text="Selecciona una fuente",
                                         bootstyle=ButtonStyle.PRIMARY)
        elif self._activas[iid]:
            self._boton_fuente.configure(state="normal", text="Deshabilitar fuente",
                                         bootstyle=ButtonStyle.DANGER_OUTLINE)
        else:
            self._boton_fuente.configure(state="normal", text="Habilitar fuente",
                                         bootstyle=ButtonStyle.SUCCESS_OUTLINE)

    def _pulsar_fuente(self) -> None:
        iid = self._tabla.seleccionado()
        if iid is not None and self._al_cambiar_fuente:
            self._al_cambiar_fuente(int(iid), not self._activas[iid])

    def _pulsar_probar(self) -> None:
        iid = self._tabla.seleccionado()
        if iid is not None and self._al_probar_fuente:
            self._al_probar_fuente(int(iid))

    def _pulsar_actualizar_una(self) -> None:
        iid = self._tabla.seleccionado()
        if iid is not None and self._al_actualizar_fuente:
            self._al_actualizar_fuente(int(iid))

    def _pulsar_actualizar(self) -> None:
        if self._al_actualizar:
            self._al_actualizar()
