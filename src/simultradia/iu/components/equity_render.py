"""Dibuja la curva de capital y, debajo, la caída desde el máximo, en una Figure de matplotlib.

No usa tkinter: recibe la figura y los datos y los dibuja. Así se puede probar sin ventana.
EquityChart (el componente) solo pone esta figura dentro de la interfaz.

Arriba va el patrimonio (línea verde si está por encima del capital inicial, roja si está por debajo). Su escala se
ajusta a lo que se ve (mínimo y máximo del rango elegido, con un margen), como en las plataformas de trading: no
empieza en 0. La línea punteada del capital inicial se dibuja SOLO si cae dentro de esa escala (si no, estiraría el eje
y aplastaría la curva). Debajo, cuánto está por debajo de su máximo. Comparten el eje horizontal.

Eje horizontal (con sus etiquetas bajo CADA panel): es TIEMPO REAL (no una posición por foto). Las marcas caen en horas o días "redondos" de la zona
horaria del equipo: si están a menos de un día una de otra, cada marca lleva la HORA ("16:30") y, cuando cambia el
día, también la fecha ("19 oct"); si están a un día o más, lleva la fecha (con el año cuando cambia).
"""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, NamedTuple, Optional, Sequence

from matplotlib.ticker import FuncFormatter, MaxNLocator

from simultradia.domain.entities.snapshot_entity import SnapshotPortafolio
from simultradia.iu.components.candle_render import _MESES, _estilizar, _rotular   # helpers compartidos con las velas
from simultradia.iu.formato import dinero, porcentaje, unidades
from simultradia.iu.styles import Palette

_ALTURA = (6, 2)        # altura relativa del panel de arriba y del de caída
_MARCAS_EJE_X = 8       # cuántas marcas (como máximo) lleva el eje horizontal
_PASOS_HORAS = (1, 2, 3, 6, 12, 24, 48, 96, 168, 336, 720, 1440, 2160, 4320, 8760)   # de 1 hora a 1 año


class Dibujo(NamedTuple):
    ejes: object                      # los ejes de arriba (para saber si el mouse está encima)
    puntos: List[SnapshotPortafolio]  # los puntos que se ven ahora, en orden
    xs: List[float]                   # su posición horizontal (segundos desde 1970)
    texto: object                     # el texto "fecha Patrimonio ..." de arriba a la izquierda


def _cifra(valor: Decimal) -> str:
    return dinero(valor, "").strip()


def texto_de_punto(punto: SnapshotPortafolio) -> str:
    """Una línea con la fecha y hora del punto y sus datos: `16/11/2026 09:00   Patrimonio ...   Saldo ...`."""
    fecha = punto.momento.astimezone().strftime("%d/%m/%Y %H:%M")
    return "%s   Patrimonio %s   Saldo %s   Posiciones %s" % (
        fecha, _cifra(punto.patrimonio_total), _cifra(punto.saldo_disponible), _cifra(punto.valor_posiciones))


def marcas_eje_x(inicio: datetime, fin: datetime) -> List[datetime]:
    """Las marcas del eje horizontal entre `inicio` y `fin`: horas o días redondos, unas 6 a 9."""
    inicio, fin = inicio.astimezone(), fin.astimezone()
    horas = (fin - inicio).total_seconds() / 3600
    paso = next((p for p in _PASOS_HORAS if horas / p <= _MARCAS_EJE_X), _PASOS_HORAS[-1])
    marca = inicio.replace(minute=0, second=0, microsecond=0)
    marca = marca.replace(hour=0) if paso >= 24 else marca.replace(hour=marca.hour // paso * paso)
    marcas = []
    while marca <= fin:
        if marca >= inicio:
            marcas.append(marca)
        marca += timedelta(hours=paso)
    if len(marcas) < 2:     # un rato tan corto que no cae ninguna hora redonda: se reparte parejo
        marcas = [inicio + (fin - inicio) * i / 4 for i in range(5)]
    return marcas


def etiquetas_eje_x(marcas: Sequence[datetime]) -> List[str]:
    """El texto de cada marca. Si distan menos de un día: la hora y, en la primera o al cambiar el día, debajo la
    fecha. Si distan un día o más: la fecha y, en la primera o al cambiar el año, debajo el año."""
    con_hora = len(marcas) > 1 and marcas[1] - marcas[0] < timedelta(days=1)
    etiquetas, anterior = [], None
    for marca in marcas:
        momento = marca.astimezone()
        dia = "%d %s" % (momento.day, _MESES[momento.month - 1])
        if con_hora:
            texto = momento.strftime("%H:%M")
            if anterior is None or momento.date() != anterior.date():
                texto += "\n" + dia
        else:
            texto = dia
            if anterior is None or momento.year != anterior.year:
                texto += "\n%d" % momento.year
        etiquetas.append(texto)
        anterior = momento
    return etiquetas


def _primero_visible(puntos: Sequence[SnapshotPortafolio], horas: Optional[int]) -> int:
    """Desde qué punto se dibuja: los de las últimas `horas` (siempre al menos 2). None = todos."""
    if horas is None:
        return 0
    corte = puntos[-1].momento - timedelta(hours=horas)
    desde = next((i for i, p in enumerate(puntos) if p.momento >= corte), len(puntos) - 1)
    return max(0, min(desde, len(puntos) - 2))


def _numero_eje(valor: float, _posicion) -> str:
    return unidades(Decimal(str(round(valor, 2))))


def _porcentaje_eje(valor: float, _posicion) -> str:
    return porcentaje(Decimal(str(round(0.0 if abs(valor) < 1e-9 else valor, 2))))


MENSAJE_SIN_PUNTOS = "No hay puntos suficientes."


def dibujar_curva(figura, puntos: Sequence[SnapshotPortafolio], caidas: Sequence[float],
                  capital_inicial: Decimal, horas: Optional[int] = None,
                  mensaje_vacio: str = MENSAJE_SIN_PUNTOS) -> Optional[Dibujo]:
    """Redibuja todo. `puntos` y `caidas` (del mismo largo) vienen del servicio; se muestran los de las
    últimas `horas` (None = toda la historia). Con menos de 2 puntos no hay curva que dibujar: en su lugar se
    escribe `mensaje_vacio` (genérico por omisión; cada pantalla puede poner uno que explique su contexto)."""
    figura.clear()
    figura.set_facecolor(Palette.FONDO)
    if puntos is None or len(puntos) < 2:
        figura.text(0.5, 0.5, mensaje_vacio,
                    ha="center", va="center", color=Palette.TEXTO, fontsize=Palette.TAMANO_TEXTO + 2)
        return None

    desde = _primero_visible(puntos, horas)
    vistos, caidas_vistas = list(puntos[desde:]), list(caidas[desde:])
    xs = [p.momento.timestamp() for p in vistos]
    ys = [float(p.patrimonio_total) for p in vistos]
    base = float(capital_inicial)
    color = Palette.ALZA if ys[-1] >= base else Palette.BAJA

    cuadricula = figura.add_gridspec(2, 1, height_ratios=list(_ALTURA), hspace=0.35,
                                     left=0.03, right=0.92, top=0.98, bottom=0.11)
    arriba = figura.add_subplot(cuadricula[0, 0])
    abajo = figura.add_subplot(cuadricula[1, 0], sharex=arriba)
    for ejes in (arriba, abajo):
        _estilizar(ejes)

    # ---- patrimonio: la escala se ajusta a lo que se ve; el capital inicial solo si cabe en ella ----
    minimo, maximo = min(ys), max(ys)
    holgura = (maximo - minimo) * 0.08 or max(abs(maximo) * 0.005, 1.0)    # sin variación: un margen mínimo
    inferior, superior = minimo - holgura, maximo + holgura
    arriba.plot(xs, ys, color=color, linewidth=1.5)
    arriba.set_ylim(inferior, superior)
    if inferior <= base <= superior:
        arriba.axhline(base, color=Palette.TEXTO, linestyle="--", linewidth=0.8, alpha=0.8)
        arriba.annotate("Capital inicial", xy=(0.01, base), xycoords=("axes fraction", "data"),
                        xytext=(0, 3), textcoords="offset points", va="bottom", ha="left",
                        fontsize=Palette.TAMANO_TEXTO, color=Palette.TEXTO)
    arriba.annotate(_cifra(vistos[-1].patrimonio_total), xy=(1, ys[-1]), xycoords=("axes fraction", "data"),
                    xytext=(3, 0), textcoords="offset points", va="center", fontsize=Palette.TAMANO_TEXTO,
                    color=Palette.FONDO, annotation_clip=False,
                    bbox=dict(boxstyle="square,pad=0.25", fc=color, ec="none"))
    margen = (xs[-1] - xs[0]) * 0.01 or 1.0
    arriba.set_xlim(xs[0] - margen, xs[-1] + margen)
    arriba.yaxis.set_major_locator(MaxNLocator(nbins=6))
    arriba.yaxis.set_major_formatter(FuncFormatter(_numero_eje))
    texto = arriba.text(0.01, 0.97, texto_de_punto(vistos[-1]), transform=arriba.transAxes,
                        va="top", ha="left", color=Palette.TEXTO, fontsize=Palette.TAMANO_TEXTO)

    # ---- caída desde el máximo ----
    abajo.fill_between(xs, caidas_vistas, 0, color=Palette.BAJA, alpha=0.55, linewidth=0)
    abajo.set_ylim(min(min(caidas_vistas) * 1.2, -1.0), 0)
    abajo.yaxis.set_major_locator(MaxNLocator(nbins=3))
    abajo.yaxis.set_major_formatter(FuncFormatter(_porcentaje_eje))
    _rotular(abajo, "Caída desde el máximo")

    # ---- eje horizontal (compartido: sus etiquetas salen bajo la curva y bajo la caída): hora o fecha de cada marca ----
    marcas = marcas_eje_x(vistos[0].momento, vistos[-1].momento)
    abajo.set_xticks([m.timestamp() for m in marcas])
    abajo.set_xticklabels(etiquetas_eje_x(marcas))
    return Dibujo(arriba, vistos, xs, texto)
