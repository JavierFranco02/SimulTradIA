"""Dibuja las velas, los indicadores y los paneles inferiores en una Figure de matplotlib.

No usa tkinter: recibe la figura y los datos y los dibuja. Así se puede probar sin ventana.
CandleChart (el componente) solo pone esta figura dentro de la interfaz.

Arriba va siempre el precio (velas, medias, bandas de Bollinger). Debajo, uno tras otro y solo si
se piden: volumen, RSI y MACD. Todos comparten el eje horizontal.
"""
from decimal import Decimal
from typing import List, NamedTuple, Optional

from matplotlib.ticker import FuncFormatter, MaxNLocator

from simultradia.domain.entities.vela_entity import Vela
from simultradia.domain.enums import IntervaloVela
from simultradia.domain.reglas import indicadores as cfg
from simultradia.domain.reglas.intervalos import SEGUNDOS
from simultradia.iu.formato import compacto, precio
from simultradia.iu.styles import Palette

_NAN = float("nan")
_ALTURA = {"precio": 6, "volumen": 1.5, "rsi": 2, "macd": 2}   # altura relativa de cada panel


class OpcionesGrafico(NamedTuple):
    visibles: int = 120          # cuántas velas se ven
    sma: bool = True
    ema: bool = True
    bollinger: bool = False
    volumen: bool = True
    rsi: bool = False
    macd: bool = False


class Dibujo(NamedTuple):
    ejes: object          # los ejes del precio (para saber si el mouse está encima)
    velas: List[Vela]     # las velas que se ven ahora, en orden
    texto: object         # el texto "O H L C" de arriba a la izquierda


def texto_de_vela(vela: Vela) -> str:
    return "O %s   H %s   L %s   C %s   Vol %s" % (
        precio(vela.apertura), precio(vela.maximo), precio(vela.minimo),
        precio(vela.cierre), compacto(vela.volumen))


def _estilizar(ejes) -> None:
    ejes.set_facecolor(Palette.FONDO)
    ejes.grid(True, color=Palette.GRILLA, linewidth=0.5, alpha=0.6)
    for borde in ejes.spines.values():
        borde.set_color(Palette.GRILLA)
    ejes.tick_params(colors=Palette.TEXTO, labelsize=Palette.TAMANO_TEXTO)
    ejes.yaxis.tick_right()


def _rotular(ejes, texto: str) -> None:
    ejes.text(0.01, 0.93, texto, transform=ejes.transAxes, va="top", ha="left",
              color=Palette.TEXTO, fontsize=Palette.TAMANO_TEXTO)


def _serie(valores, desde: int) -> List[float]:
    return [_NAN if v is None else v for v in valores[desde:]]


def dibujar_velas(figura, datos, intervalo: IntervaloVela,
                  opciones: OpcionesGrafico = OpcionesGrafico()) -> Optional[Dibujo]:
    """Redibuja todo. `datos` es un DatosGrafico; se muestran las últimas `opciones.visibles` velas."""
    figura.clear()
    figura.set_facecolor(Palette.FONDO)
    if datos is None or not datos.velas:
        figura.text(0.5, 0.5, "Aún no hay velas guardadas para este activo.\n"
                    "Deja correr el worker unos minutos.", ha="center", va="center",
                    color=Palette.TEXTO, fontsize=Palette.TAMANO_TEXTO + 2)
        return None

    total = len(datos.velas)
    desde = total - min(opciones.visibles, total)
    velas = datos.velas[desde:]
    xs = list(range(len(velas)))
    abre = [float(v.apertura) for v in velas]
    alto = [float(v.maximo) for v in velas]
    bajo = [float(v.minimo) for v in velas]
    cierra = [float(v.cierre) for v in velas]
    colores = [Palette.ALZA if c >= a else Palette.BAJA for a, c in zip(abre, cierra)]

    # El volumen se omite si el activo no lo tiene (las divisas y los índices no lo informan).
    paneles = (["precio"] + (["volumen"] if opciones.volumen and any(v.volumen > 0 for v in velas) else [])
               + (["rsi"] if opciones.rsi else []) + (["macd"] if opciones.macd else []))
    cuadricula = figura.add_gridspec(len(paneles), 1, height_ratios=[_ALTURA[p] for p in paneles],
                                     hspace=0.08, left=0.03, right=0.92, top=0.98, bottom=0.08)
    ejes = {}
    for posicion, nombre in enumerate(paneles):
        ejes[nombre] = figura.add_subplot(cuadricula[posicion, 0],
                                          sharex=ejes["precio"] if posicion else None)
        _estilizar(ejes[nombre])
        if posicion < len(paneles) - 1:
            ejes[nombre].tick_params(labelbottom=False)

    # ---- precio: mecha (mínimo a máximo) y cuerpo (apertura a cierre) ----
    ax = ejes["precio"]
    rango = (max(alto) - min(bajo)) or 1.0
    ax.vlines(xs, bajo, alto, colors=colores, linewidth=1)
    ax.bar(xs, [max(abs(c - a), rango * 0.002) for a, c in zip(abre, cierra)],
           bottom=[min(a, c) for a, c in zip(abre, cierra)], width=0.7, color=colores)
    if opciones.bollinger:
        superior, inferior = _serie(datos.bb_superior, desde), _serie(datos.bb_inferior, desde)
        ax.plot(xs, superior, color=Palette.BOLLINGER, linewidth=1,
                label="Bollinger %d, %g" % (cfg.PERIODO_BOLLINGER, cfg.DESVIACIONES_BOLLINGER))
        ax.plot(xs, inferior, color=Palette.BOLLINGER, linewidth=1)
        ax.fill_between(xs, inferior, superior, color=Palette.BOLLINGER, alpha=0.08)
    if opciones.sma:
        ax.plot(xs, _serie(datos.sma, desde), color=Palette.SMA, linewidth=1.2,
                label="SMA %d" % cfg.PERIODO_SMA)
    if opciones.ema:
        ax.plot(xs, _serie(datos.ema, desde), color=Palette.EMA, linewidth=1.2,
                label="EMA %d" % cfg.PERIODO_EMA)

    # Línea y etiqueta con el último precio, como en las plataformas de trading.
    y = cierra[-1]
    ax.axhline(y, color=colores[-1], linestyle=":", linewidth=0.8)
    ax.annotate(precio(velas[-1].cierre), xy=(1, y), xycoords=("axes fraction", "data"),
                xytext=(3, 0), textcoords="offset points", va="center",
                fontsize=Palette.TAMANO_TEXTO, color=Palette.FONDO, annotation_clip=False,
                bbox=dict(boxstyle="square,pad=0.25", fc=colores[-1], ec="none"))
    ax.margins(x=0.01, y=0.08)
    ax.set_xlim(-1, len(velas) + 1)
    if ax.get_legend_handles_labels()[0]:
        ax.legend(loc="upper right", frameon=False, labelcolor=Palette.TEXTO,
                  fontsize=Palette.TAMANO_TEXTO)
    texto = ax.text(0.01, 0.97, texto_de_vela(velas[-1]), transform=ax.transAxes,
                    va="top", ha="left", color=Palette.TEXTO, fontsize=Palette.TAMANO_TEXTO)

    # ---- paneles inferiores ----
    if "volumen" in ejes:
        ejes["volumen"].bar(xs, [float(v.volumen) for v in velas], width=0.7, color=colores, alpha=0.6)
        ejes["volumen"].yaxis.set_major_formatter(FuncFormatter(lambda v, _p: compacto(Decimal(str(v)))))
        ejes["volumen"].yaxis.set_major_locator(MaxNLocator(nbins=2))
        _rotular(ejes["volumen"], "Volumen")
    if "rsi" in ejes:
        panel = ejes["rsi"]
        panel.plot(xs, _serie(datos.rsi, desde), color=Palette.RSI, linewidth=1.2)
        for nivel in (30, 70):    # debajo de 30: sobreventa; encima de 70: sobrecompra
            panel.axhline(nivel, color=Palette.TEXTO, linestyle="--", linewidth=0.7, alpha=0.7)
        panel.set_ylim(0, 100)
        panel.set_yticks([30, 70])
        _rotular(panel, "RSI %d" % cfg.PERIODO_RSI)
    if "macd" in ejes:
        panel = ejes["macd"]
        histograma = _serie(datos.macd_hist, desde)
        panel.bar(xs, histograma, width=0.7, alpha=0.6,
                  color=[Palette.ALZA if (h == h and h >= 0) else Palette.BAJA for h in histograma])
        panel.plot(xs, _serie(datos.macd, desde), color=Palette.MACD, linewidth=1.2)
        panel.plot(xs, _serie(datos.macd_senal, desde), color=Palette.SENAL, linewidth=1.2)
        panel.axhline(0, color=Palette.TEXTO, linewidth=0.6, alpha=0.7)
        _rotular(panel, "MACD %d, %d, %d" % (cfg.MACD_RAPIDA, cfg.MACD_LENTA, cfg.MACD_SENAL))

    # ---- fechas del eje horizontal (solo en el panel de más abajo) ----
    formato = "%d/%m %H:%M" if SEGUNDOS[intervalo] < 86400 else "%d/%m/%y"
    eje_x = ejes[paneles[-1]]
    eje_x.xaxis.set_major_locator(MaxNLocator(nbins=6, integer=True))
    eje_x.xaxis.set_major_formatter(FuncFormatter(
        lambda x, _p: velas[int(round(x))].momento.astimezone().strftime(formato)
        if 0 <= int(round(x)) < len(velas) else ""))
    return Dibujo(ax, velas, texto)
