"""Gráficos de la pantalla de IA, dibujados en una Figure de matplotlib (sin tkinter: se prueba solo).

  - dibujar_proyeccion: el abanico de precios posibles de Monte Carlo (5-95 %, 25-75 % y mediana).
  - dibujar_tramos: acierto del modelo contra la base en cada periodo de la validación (rotulado con sus fechas).
"""
from decimal import Decimal
from typing import Optional

from matplotlib.ticker import FuncFormatter

from simultradia.analisis.montecarlo import Proyeccion
from simultradia.ia.entrenamiento import Evaluacion
from simultradia.iu.formato import precio
from simultradia.iu.ia import textos
from simultradia.iu.styles import Palette


def _estilizar(ejes) -> None:
    ejes.set_facecolor(Palette.FONDO)
    ejes.grid(True, color=Palette.GRILLA, linewidth=0.5, alpha=0.6)
    for borde in ejes.spines.values():
        borde.set_color(Palette.GRILLA)
    ejes.tick_params(colors=Palette.TEXTO, labelsize=Palette.TAMANO_TEXTO)


def _vacio(figura, texto: str) -> None:
    figura.text(0.5, 0.5, texto, ha="center", va="center", color=Palette.TEXTO,
                fontsize=Palette.TAMANO_TEXTO + 2)


def dibujar_proyeccion(figura, proyeccion: Optional[Proyeccion], nivel: Optional[float] = None) -> None:
    figura.clear()
    figura.set_facecolor(Palette.FONDO)
    if proyeccion is None:
        _vacio(figura, "Sin proyección todavía.")
        return
    ejes = figura.add_subplot(1, 1, 1)
    figura.subplots_adjust(left=0.03, right=0.9, top=0.95, bottom=0.12)
    _estilizar(ejes)
    ejes.yaxis.tick_right()
    p = proyeccion.percentiles
    dias = list(range(proyeccion.dias + 1))

    def con_inicio(valores):
        return [proyeccion.precio_inicial] + list(valores)

    ejes.fill_between(dias, con_inicio(p[5]), con_inicio(p[95]), color=Palette.EMA, alpha=0.15,
                      label="5 % – 95 %")
    ejes.fill_between(dias, con_inicio(p[25]), con_inicio(p[75]), color=Palette.EMA, alpha=0.30,
                      label="25 % – 75 %")
    ejes.plot(dias, con_inicio(p[50]), color=Palette.EMA, linewidth=1.6, label="Mediana")
    ejes.axhline(proyeccion.precio_inicial, color=Palette.TEXTO, linestyle=":", linewidth=0.8)
    if nivel is not None:
        ejes.axhline(nivel, color=Palette.BAJA, linestyle="--", linewidth=1.0)
        ejes.annotate(precio(Decimal(str(nivel))), xy=(1, nivel), xycoords=("axes fraction", "data"),
                      xytext=(3, 0), textcoords="offset points", va="center", annotation_clip=False,
                      fontsize=Palette.TAMANO_TEXTO, color=Palette.FONDO,
                      bbox=dict(boxstyle="square,pad=0.25", fc=Palette.BAJA, ec="none"))
    ejes.set_xlim(0, proyeccion.dias)
    ejes.set_xticks(dias)
    ejes.set_xticklabels(["hoy"] + ["+%d" % d for d in dias[1:]])
    ejes.legend(loc="upper left", ncol=3, frameon=False, labelcolor=Palette.TEXTO,
                fontsize=Palette.TAMANO_TEXTO)


def dibujar_tramos(figura, evaluacion: Optional[Evaluacion]) -> None:
    """Una pareja de barras por periodo de prueba: el modelo contra la base. El periodo se rotula con sus fechas."""
    figura.clear()
    figura.set_facecolor(Palette.FONDO)
    if evaluacion is None or not evaluacion.tramos:
        _vacio(figura, "Sin validación todavía.")
        return
    ejes = figura.add_subplot(1, 1, 1)
    figura.subplots_adjust(left=0.08, right=0.98, top=0.9, bottom=0.2)
    _estilizar(ejes)
    ejes.grid(False, axis="x")
    tramos = evaluacion.tramos
    xs = list(range(len(tramos)))
    ancho = 0.36
    for desplazamiento, valores, color, nombre in (
            (-ancho / 2, [t.acierto * 100 for t in tramos], Palette.ALZA, "Modelo"),
            (ancho / 2, [t.base * 100 for t in tramos], Palette.GRILLA, "Base (siempre el escenario más común)")):
        barras = ejes.bar([x + desplazamiento for x in xs], valores, width=ancho, color=color, label=nombre)
        for barra, valor in zip(barras, valores):
            ejes.annotate("%d %%" % round(valor), xy=(barra.get_x() + ancho / 2, valor), xytext=(0, 3),
                          textcoords="offset points", ha="center", va="bottom", color=Palette.TEXTO,
                          fontsize=Palette.TAMANO_TEXTO)
    ejes.set_xticks(xs)
    ejes.set_xticklabels([textos.periodo(t.inicio, t.fin).replace(" – ", "\na ") for t in tramos])
    tope = min(100, max(40, int(max(max(t.acierto, t.base) for t in tramos) * 100 * 1.35 / 10 + 1) * 10))
    ejes.set_ylim(0, tope)
    ejes.yaxis.set_major_formatter(FuncFormatter(lambda v, _p: "%d %%" % v))
    ejes.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, frameon=False, labelcolor=Palette.TEXTO,
                fontsize=Palette.TAMANO_TEXTO)
