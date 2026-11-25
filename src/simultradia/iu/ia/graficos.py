"""Gráficos de la pantalla de volatilidad, dibujados en una Figure de matplotlib (sin tkinter: se prueba solo).

  - dibujar_proyeccion: el abanico de precios posibles de Monte Carlo (5-95 %, 25-75 % y mediana).
  - dibujar_tramos: error del modelo contra las dos bases en cada periodo de la validación (menos es mejor).
  - dibujar_ultimos_dias: el rango de los últimos días y el esperado para mañana (con su intervalo).
  - dibujar_calibracion: lo que esperaba el modelo contra lo que pasó, en cinco grupos de días.
  - dibujar_historial: rango predicho (con su intervalo) contra el rango real de un activo, día a día.
"""
import math
from decimal import Decimal
from typing import List, Optional, Sequence

from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.ticker import FuncFormatter

from simultradia.analisis.montecarlo import Proyeccion
from simultradia.domain.entities.prediccion_volatilidad_entity import PrediccionVolatilidad
from simultradia.ia.volatilidad import Evaluacion
from simultradia.iu.formato import precio
from simultradia.iu.ia import textos
from simultradia.iu.styles import Palette


def _estilizar(ejes) -> None:
    ejes.set_facecolor(Palette.FONDO)
    ejes.set_axisbelow(True)                         # la cuadrícula queda detrás de las barras, no encima
    ejes.grid(True, color=Palette.GRILLA, linewidth=0.5, alpha=0.6)
    for borde in ejes.spines.values():
        borde.set_color(Palette.GRILLA)
    ejes.tick_params(colors=Palette.TEXTO, labelsize=Palette.TAMANO_TEXTO)


def _decimales_eje(marcas) -> int:
    """Cuántos decimales hacen falta para que ninguna marca del eje se repita: según el paso entre marcas."""
    marcas = sorted(set(round(float(m), 9) for m in marcas))
    pasos = [b - a for a, b in zip(marcas, marcas[1:])]
    if not pasos:
        return 0
    paso = min(pasos)
    for decimales in (0, 1, 2):
        if abs(paso * 10 ** decimales - round(paso * 10 ** decimales)) < 1e-6:
            return decimales
    return 2


def _formato_pct_eje(ejes) -> FuncFormatter:
    """Marcas del eje vertical en %, todas con los mismos decimales (los que pide el paso): 0,05 / 0,10 / 0,15."""
    def escribir(valor, _posicion):
        decimales = _decimales_eje(ejes.yaxis.get_majorticklocs())
        return ("%.*f" % (decimales, valor)).replace(".", ",") + " %"
    return FuncFormatter(escribir)


_BANDA = "#2f5f86"          # el intervalo del 80 % del registro: azul acerado, más vivo que el de la proyección


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
    """Tres barras por periodo de prueba: error del modelo y de las dos bases (menos es mejor)."""
    figura.clear()
    figura.set_facecolor(Palette.FONDO)
    if evaluacion is None or not evaluacion.tramos:
        _vacio(figura, "Sin validación todavía.")
        return
    ejes = figura.add_subplot(1, 1, 1)
    figura.subplots_adjust(left=0.08, right=0.98, top=0.86, bottom=0.2)
    _estilizar(ejes)
    ejes.grid(False, axis="x")
    tramos = evaluacion.tramos
    xs = list(range(len(tramos)))
    ancho = 0.26
    # El error está en logaritmo; se dibuja en % real (exp(e) - 1) para que la altura sea proporcional al número escrito.
    def real(e: float) -> float:
        return (math.exp(e) - 1) * 100

    series = ((-ancho, [t.error for t in tramos], Palette.EMA, "Modelo"),
              (0.0, [t.error_hoy for t in tramos], Palette.GRILLA, "Repetir el rango de hoy"),
              (ancho, [t.error_media for t in tramos], Palette.SMA, "Promedio de 20 días"))
    for desplazamiento, valores, color, nombre in series:
        barras = ejes.bar([x + desplazamiento for x in xs], [real(v) for v in valores], width=ancho, color=color,
                          label=nombre)
        for barra, valor in zip(barras, valores):
            ejes.annotate(textos.error_pct(valor).lstrip("±"), xy=(barra.get_x() + ancho / 2, real(valor)),
                          xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", color=Palette.TEXTO,
                          fontsize=Palette.TAMANO_TEXTO - 1)
    ejes.set_xticks(xs)
    ejes.set_xticklabels([textos.periodo(t.inicio, t.fin).replace(" – ", "\na ") for t in tramos])
    ejes.set_ylim(0, max(real(max(t.error, t.error_hoy, t.error_media)) for t in tramos) * 1.3)
    ejes.yaxis.set_major_formatter(_formato_pct_eje(ejes))
    ejes.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=3, frameon=False, labelcolor=Palette.TEXTO,
                fontsize=Palette.TAMANO_TEXTO)


_DIAS_HISTORIAL = 30           # cuántas predicciones se dibujan como máximo
_COLUMNAS_MINIMAS = 7          # el eje tiene lugar para al menos 7 columnas: el grosor de una barra no depende de cuántas haya
_ANCHO_BARRA = 0.75            # en columnas (1 = el espacio completo de una columna)


def dibujar_historial(figura, historial: Sequence[PrediccionVolatilidad]) -> None:
    """Una columna por predicción, de la más vieja a la más nueva: la banda del intervalo del ~80 %, una marca con el
    rango predicho y, si ya se evaluó, un punto con el rango real (con borde naranja si cayó fuera de la banda).
    Una predicción pendiente muestra la banda y la marca, sin punto. Sirve desde la primera predicción."""
    figura.clear()
    figura.set_facecolor(Palette.FONDO)
    if not historial:
        _vacio(figura, "Sin predicciones todavía.")
        return
    orden: List[PrediccionVolatilidad] = sorted(historial, key=lambda p: p.generada_en)[-_DIAS_HISTORIAL:]
    ejes = figura.add_subplot(1, 1, 1)
    figura.subplots_adjust(left=0.07, right=0.98, top=0.86, bottom=0.14)
    _estilizar(ejes)
    ejes.grid(False, axis="x")
    n = len(orden)
    ancho = _ANCHO_BARRA
    for x, p in enumerate(orden):
        ejes.bar(x, (p.rango_alto - p.rango_bajo) * 100, bottom=p.rango_bajo * 100, width=ancho, color=_BANDA, zorder=2)
        ejes.hlines(p.rango_predicho * 100, x - ancho / 2, x + ancho / 2, color=Palette.EMA, linewidth=3, zorder=3)
        if p.rango_real is not None:
            dentro = p.rango_bajo <= p.rango_real <= p.rango_alto
            ejes.scatter([x], [p.rango_real * 100], s=46, color="white", zorder=4,
                         edgecolors="none" if dentro else Palette.ALERTA, linewidths=0 if dentro else 2)
    centro = (n - 1) / 2                      # con pocas predicciones, el eje no se achica: quedan centradas
    mitad = max(n, _COLUMNAS_MINIMAS) / 2 + 0.3
    ejes.set_xlim(centro - mitad, centro + mitad)
    techo = max(max(p.rango_alto, p.rango_real if p.rango_real is not None else 0.0) for p in orden)
    ejes.set_ylim(0, techo * 100 * 1.15)                 # el techo incluye el rango real: el punto nunca queda fuera
    marcas = list(range(0, n, max(1, n // 8)))
    ejes.set_xticks(marcas)
    ejes.set_xticklabels([textos.fecha(orden[x].generada_en)[:5] for x in marcas])
    ejes.yaxis.set_major_formatter(_formato_pct_eje(ejes))
    ejes.legend(handles=[Patch(color=_BANDA, label="Intervalo del 80 %"),
                         Line2D([], [], color=Palette.EMA, linewidth=3, label="Rango predicho"),
                         Line2D([], [], color="white", marker="o", linestyle="", markersize=7,
                                label="Rango real (borde naranja si cayó fuera)")],
                loc="lower left", bbox_to_anchor=(0, 1.0), ncol=3, frameon=False, labelcolor=Palette.TEXTO,
                fontsize=Palette.TAMANO_TEXTO)


def dibujar_ultimos_dias(figura, rangos: Sequence[float], prediccion: Optional[PrediccionVolatilidad],
                         fechas: Sequence = ()) -> None:
    """Barras con el rango de los últimos días, una barra aparte para mañana con su intervalo del 80 %, y tres
    líneas de referencia: el promedio de 20 días y los umbrales de «baja» y «alta». Si se dan las fechas, se escribe
    la de una barra sí y otra no, para tener una referencia del día."""
    figura.clear()
    figura.set_facecolor(Palette.FONDO)
    if not rangos or prediccion is None:
        _vacio(figura, "Sin datos para dibujar.")
        return
    ejes = figura.add_subplot(1, 1, 1)
    figura.subplots_adjust(left=0.07, right=0.98, top=0.97, bottom=0.25)
    _estilizar(ejes)
    ejes.grid(False, axis="x")
    n = len(rangos)
    xs = list(range(n))
    ejes.bar(xs, [r * 100 for r in rangos], width=0.75, color=Palette.GRILLA)
    ejes.bar([n - 1], [rangos[-1] * 100], width=0.75, color=Palette.TEXTO)        # «hoy», un poco más claro
    manana = n + 1
    ejes.bar([manana], [prediccion.rango_predicho * 100], width=0.75, color=Palette.ALERTA)
    ejes.vlines(manana, prediccion.rango_bajo * 100, prediccion.rango_alto * 100, color="white", linewidth=1.6)
    for extremo in (prediccion.rango_bajo, prediccion.rango_alto):
        ejes.hlines(extremo * 100, manana - 0.3, manana + 0.3, color="white", linewidth=1.6)
    lineas = []
    for valor, color, estilo, nombre in (
            (prediccion.rango_normal, "white", "--", "Promedio 20 días (%s)" % textos.rango(prediccion.rango_normal)),
            (prediccion.umbral_alto, Palette.ALERTA, "--", "Desde aquí: alta (%s)" % textos.rango(prediccion.umbral_alto)),
            (prediccion.umbral_bajo, Palette.CALMA, ":", "Hasta aquí: baja (%s)" % textos.rango(prediccion.umbral_bajo))):
        lineas.append(ejes.axhline(valor * 100, color=color, linestyle=estilo, linewidth=1.2, label=nombre))
    ejes.set_xlim(-0.8, manana + 0.9)
    if len(fechas) == n:
        posiciones = list(range(n - 3, -1, -2))[::-1]            # una barra sí y otra no, contando desde «hoy»
        etiquetas = [fechas[i].strftime("%d/%m") for i in posiciones]
    else:
        posiciones, etiquetas = [0], ["hace %d días" % (n - 1)]
    ejes.set_xticks(posiciones + [n - 1, manana])
    ejes.set_xticklabels(etiquetas + ["hoy", "mañana"])
    ejes.yaxis.set_major_formatter(_formato_pct_eje(ejes))
    ejes.legend(handles=lineas, loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=3, frameon=False,
                labelcolor=Palette.TEXTO, fontsize=Palette.TAMANO_TEXTO)


def dibujar_calibracion(figura, grupos: Sequence) -> None:
    """Para cada grupo de días (de más tranquilo a más agitado según el modelo): barra gris con lo esperado y
    barra azul con lo que pasó de verdad, en veces lo normal."""
    figura.clear()
    figura.set_facecolor(Palette.FONDO)
    if not grupos:
        _vacio(figura, "Sin validación todavía.")
        return
    ejes = figura.add_subplot(1, 1, 1)
    figura.subplots_adjust(left=0.17, right=0.95, top=0.88, bottom=0.2)
    _estilizar(ejes)
    ejes.grid(False, axis="y")
    ys = list(range(len(grupos)))[::-1]                      # el primer grupo arriba
    alto = 0.34
    ejes.barh([y + alto / 2 for y in ys], [g.predicho for g in grupos], height=alto, color=Palette.GRILLA,
              label="Lo que esperaba el modelo")
    ejes.barh([y - alto / 2 for y in ys], [g.real for g in grupos], height=alto, color=Palette.EMA,
              label="Lo que pasó de verdad")
    for y, g in zip(ys, grupos):
        ejes.annotate(textos.numero(g.predicho, 1) + "×", xy=(g.predicho, y + alto / 2), xytext=(3, 0),
                      textcoords="offset points", va="center", color=Palette.TEXTO, fontsize=Palette.TAMANO_TEXTO)
        ejes.annotate(textos.numero(g.real, 1) + "×", xy=(g.real, y - alto / 2), xytext=(3, 0),
                      textcoords="offset points", va="center", color="white", fontsize=Palette.TAMANO_TEXTO)
    ejes.axvline(1.0, color=Palette.TEXTO, linestyle=":", linewidth=0.8)
    ejes.set_yticks(ys)
    ejes.set_yticklabels(["Un día %s" % g.etiqueta.lower() for g in grupos])
    ejes.set_xlim(0, max(max(g.predicho, g.real) for g in grupos) * 1.2)
    ejes.set_xlabel("veces lo normal (1,0× = un día habitual)", color=Palette.TEXTO, fontsize=Palette.TAMANO_TEXTO)
    ejes.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=2, frameon=False, labelcolor=Palette.TEXTO,
                fontsize=Palette.TAMANO_TEXTO)
