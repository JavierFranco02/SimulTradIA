"""Gráfico de un activo (el panel derecho de Mercado): precio en vivo, intervalos, velas e indicadores.

Vista pasiva: GraficoController le dice qué mostrar. Mientras no hay activo elegido muestra una
indicación. Los interruptores de indicadores y la cantidad de velas solo cambian cómo se dibuja:
no hace falta pedir nada al servicio.
"""
import tkinter as tk
from typing import Callable, Optional

import ttkbootstrap as ttk

from simultradia.domain.entities.cotizacion_entity import ActivoCotizado
from simultradia.domain.enums import IntervaloVela, TipoActivo
from simultradia.domain.reglas import indicadores as cfg
from simultradia.domain.reglas.intervalos import DISPONIBLES
from simultradia.iu.base.panel_view import PanelView
from simultradia.iu.components import CandleChart, SelectField
from simultradia.iu.components.candle_render import OpcionesGrafico
from simultradia.iu.formato import TIPO_SINGULAR, compacto, hace, porcentaje, precio
from simultradia.iu.styles import ButtonStyle, Colors, Fonts, Spacing

_ETIQUETAS = {IntervaloVela.M15: "15 min", IntervaloVela.H1: "1 h", IntervaloVela.H4: "4 h",
              IntervaloVela.D1: "1 día", IntervaloVela.W1: "1 sem"}
_VELAS = (30, 60, 90, 120, 200, 300, 500)     # cuántas velas mostrar (500 es todo lo que se carga)
_VELAS_INICIAL = 120
# (clave, texto del interruptor, encendido al empezar)
_INDICADORES = (
    ("sma", "SMA %d" % cfg.PERIODO_SMA, True),
    ("ema", "EMA %d" % cfg.PERIODO_EMA, True),
    ("bollinger", "Bollinger", False),
    ("volumen", "Volumen", True),
    ("rsi", "RSI %d" % cfg.PERIODO_RSI, False),
    ("macd", "MACD", False),
)


class GraficoActivoView(PanelView):
    def __init__(self, parent):
        super().__init__(parent, padding=Spacing.SM)
        self._al_cambiar_intervalo: Optional[Callable[[IntervaloVela], None]] = None

        self._indicacion = ttk.Label(self, text="Elige un activo de la lista para ver su gráfico.",
                                     font=Fonts.SUBTITLE, bootstyle=Colors.MUTED)
        self._indicacion.pack(expand=True)
        self._contenido = ttk.Frame(self)       # se muestra cuando hay un activo elegido

        cabecera = ttk.Frame(self._contenido)
        cabecera.pack(fill="x", pady=(0, Spacing.SM))
        nombres = ttk.Frame(cabecera)
        nombres.pack(side="left")
        self._ticker = ttk.Label(nombres, text="", font=Fonts.TITLE)
        self._ticker.pack(anchor="w")
        self._detalle = ttk.Label(nombres, text="", font=Fonts.SUBTITLE, bootstyle=Colors.MUTED)
        self._detalle.pack(anchor="w")
        cifras = ttk.Frame(cabecera)
        cifras.pack(side="right")
        self._precio = ttk.Label(cifras, text="—", font=Fonts.DISPLAY)
        self._precio.pack(anchor="e")
        self._variacion = ttk.Label(cifras, text="", font=Fonts.HEADING)
        self._variacion.pack(anchor="e")
        self._datos_dia = ttk.Label(self._contenido, text="", font=Fonts.SMALL, bootstyle=Colors.MUTED)
        self._datos_dia.pack(anchor="w", pady=(0, Spacing.SM))

        barra = ttk.Frame(self._contenido)
        barra.pack(fill="x")
        self._intervalo = tk.StringVar(master=self, value=IntervaloVela.H1.value)
        for intervalo in DISPONIBLES:
            ttk.Radiobutton(barra, text=_ETIQUETAS[intervalo], value=intervalo.value,
                            variable=self._intervalo, command=self._pulsar_intervalo,
                            bootstyle=ButtonStyle.TOGGLE).pack(side="left", padx=(0, Spacing.XS))
        self._velas = SelectField(barra, None, [(str(n), "%d velas" % n) for n in _VELAS], ancho=10)
        self._velas.establecer(str(_VELAS_INICIAL))
        self._velas.al_cambiar(self._pulsar_opciones)
        self._velas.pack(side="right")

        interruptores = ttk.Frame(self._contenido)
        interruptores.pack(fill="x", pady=(Spacing.SM, Spacing.SM))
        ttk.Label(interruptores, text="Indicadores", font=Fonts.BODY,
                  bootstyle=Colors.MUTED).pack(side="left", padx=(0, Spacing.MD))
        self._activos = {}
        for clave, texto, encendido in _INDICADORES:
            self._activos[clave] = tk.BooleanVar(master=self, value=encendido)
            ttk.Checkbutton(interruptores, text=texto, variable=self._activos[clave],
                            command=self._pulsar_opciones, bootstyle=ButtonStyle.SWITCH
                            ).pack(side="left", padx=(0, Spacing.MD))

        self._grafico = CandleChart(self._contenido)
        self._grafico.pack(fill="both", expand=True)
        self._grafico.establecer_opciones(self._opciones())

    def vincular_acciones(self, al_cambiar_intervalo: Callable[[IntervaloVela], None]) -> None:
        self._al_cambiar_intervalo = al_cambiar_intervalo

    # ------------------------------------------- lo que el controlador ordena
    def mostrar_activo(self, item: ActivoCotizado) -> None:
        if not self._contenido.winfo_ismapped():
            self._indicacion.pack_forget()
            self._contenido.pack(fill="both", expand=True)
        a, c = item.activo, item.cotizacion
        periodo = "24 h" if a.tipo == TipoActivo.CRIPTO else "del día"
        self._ticker.configure(text=a.ticker)
        self._detalle.configure(text="%s · %s · %s" % (a.nombre, TIPO_SINGULAR[a.tipo], a.fuente))
        if c is None:
            self._precio.configure(text="—")
            self._variacion.configure(text="Sin precio todavía", bootstyle=Colors.MUTED)
            self._datos_dia.configure(text="")
            return
        v = c.variacion_pct_dia
        color = Colors.SUCCESS if v and v > 0 else Colors.DANGER if v and v < 0 else Colors.MUTED
        flecha = "▲ " if v and v > 0 else "▼ " if v and v < 0 else ""
        self._precio.configure(text="%s %s" % (precio(c.precio), a.moneda))
        self._variacion.configure(
            text=flecha + (porcentaje(v, con_signo=True) if v is not None else "—") + "  (%s)" % periodo,
            bootstyle=color)
        partes = []
        if c.maximo_dia is not None:
            partes.append("Máx. %s %s" % (periodo, precio(c.maximo_dia)))
        if c.minimo_dia is not None:
            partes.append("Mín. %s %s" % (periodo, precio(c.minimo_dia)))
        if c.volumen_dia:    # las divisas y los índices no informan volumen
            partes.append("Vol. %s USD" % compacto(c.volumen_dia))
        partes.append("actualizado " + hace(c.actualizado_en))
        self._datos_dia.configure(text="   ·   ".join(partes))

    def mostrar_grafico(self, datos, intervalo: IntervaloVela) -> None:
        self._grafico.establecer_datos(datos, intervalo)

    def limpiar_grafico(self) -> None:
        self._grafico.limpiar()

    # --------------------------------------------------------- eventos de la UI
    def _opciones(self) -> OpcionesGrafico:
        return OpcionesGrafico(visibles=int(self._velas.obtener()),
                               **{clave: var.get() for clave, var in self._activos.items()})

    def _pulsar_opciones(self) -> None:
        self._grafico.establecer_opciones(self._opciones())

    def _pulsar_intervalo(self) -> None:
        if self._al_cambiar_intervalo:
            self._al_cambiar_intervalo(IntervaloVela(self._intervalo.get()))
