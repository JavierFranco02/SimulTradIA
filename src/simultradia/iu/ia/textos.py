"""Textos y reglas de presentación de la pantalla de volatilidad. Python puro (sin tkinter): se prueba solo.

Todo número que ve el usuario sale de aquí, así las pestañas lo escriben igual.
La volatilidad NO usa verde ni rojo (no significa «bueno» ni «malo»): solo los aciertos y fallos del registro.
"""
import math
from datetime import date, datetime
from typing import Optional, Sequence

from simultradia.analisis.volatilidad import NOMBRES_FEATURES
from simultradia.domain.entities.prediccion_volatilidad_entity import PrediccionVolatilidad
from simultradia.domain.enums import NivelVolatilidad
from simultradia.domain.reglas.volatilidad import PERCENTIL_ALTO, PERCENTIL_BAJO, VENTANA_NIVEL, VENTANA_NORMAL, Z_MINIMO
from simultradia.ia.volatilidad import BinCalibracion, Evaluacion

_ESPACIO = " "

AVISO = "Estimación estadística con fines educativos. No es asesoría financiera."

_NIVEL = {NivelVolatilidad.BAJA: "Baja", NivelVolatilidad.NORMAL: "Normal", NivelVolatilidad.ALTA: "Alta"}
_FACTOR = dict(zip(NOMBRES_FEATURES, (
    "Rango de hoy", "Rango medio 3 días", "Rango medio 5 días", "Rango medio 10 días", "Rango medio 20 días",
    "Rango medio 60 días", "Rango medio 120 días", "Rango 3 d. frente a 20 d.", "Rango 20 d. frente a 120 d.",
    "Movimiento de hoy (sin signo)", "Movimiento medio 5 días", "Movimiento medio 20 días",
    "Volatilidad 20 días", "Volatilidad 60 días", "Retorno de hoy", "Retorno 5 días", "Retorno 20 días",
    "Salto de apertura", "Volumen relativo", "Caída desde el máximo de 60 días",
    "Día de la semana (seno)", "Día de la semana (coseno)")))

_MESES = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")


def pct(valor: float, decimales: int = 0) -> str:
    """0,543 -> «54 %». El valor va de 0 a 1."""
    return ("%.*f" % (decimales, valor * 100)).replace(".", ",") + _ESPACIO + "%"


def rango(valor: float) -> str:
    """Un rango diario (fracción del precio) con un decimal: 0,023 -> «2,3 %»."""
    return pct(valor, 1)


def numero(valor: float, decimales: int = 2, con_signo: bool = False) -> str:
    texto = ("%+.*f" if con_signo else "%.*f") % (decimales, valor)
    return texto.replace(".", ",")


def veces(valor: float) -> str:
    """1,4 -> «1,4× lo normal»."""
    return numero(valor, 1) + "× lo normal"


def error_pct(error_log: float) -> str:
    """El error medio en logaritmo como «se equivoca ±x %» del rango: exp(e) - 1."""
    return "±" + pct(math.exp(error_log) - 1.0)


def nivel(n: NivelVolatilidad) -> str:
    return _NIVEL[n]


def factor(nombre: str) -> str:
    return _FACTOR.get(nombre, nombre)


def fecha(momento: Optional[datetime]) -> str:
    return "—" if momento is None else momento.astimezone().strftime("%d/%m/%Y")


def resultado(p: PrediccionVolatilidad) -> str:
    if p.acierto_nivel is None:
        return "Pendiente"
    return "Acertó" if p.acierto_nivel else "Falló"


def etiqueta_resultado(p: PrediccionVolatilidad) -> str:
    """Verde si acertó el nivel, rojo si falló, normal si falta."""
    return "" if p.acierto_nivel is None else "alza" if p.acierto_nivel else "baja"


def frase_nivel(n: NivelVolatilidad) -> str:
    return {NivelVolatilidad.BAJA: "Se espera un día tranquilo: el precio oscilaría menos de lo habitual.",
            NivelVolatilidad.NORMAL: "Se espera un día de oscilación habitual para este activo.",
            NivelVolatilidad.ALTA: "Se espera un día agitado: el precio oscilaría más de lo habitual."}[n]


def explicacion_nivel() -> str:
    return ("El nivel compara el rango esperado con los últimos %d días de ESTE activo: «baja» es del 25 %% más "
            "tranquilo, «alta» del 25 %% más agitado y «normal» lo demás." % VENTANA_NIVEL)


def explicacion_rango() -> str:
    return ("El rango es la distancia entre el máximo y el mínimo del día, como porcentaje del precio. "
            "No dice si el precio sube o baja: dice cuánto se mueve.")


def frase_intervalo(p: PrediccionVolatilidad) -> str:
    return "Con ~80 %% de probabilidad entre %s y %s." % (rango(p.rango_bajo), rango(p.rango_alto))


def frase_normal(p: PrediccionVolatilidad) -> str:
    return "Es %s (el promedio de %d días es %s)." % (veces(p.veces_lo_normal), VENTANA_NORMAL, rango(p.rango_normal))


def dias(n: int) -> str:
    return "%d %s" % (n, "día" if n == 1 else "días")


def periodo(inicio_ordinal: int, fin_ordinal: int) -> str:
    """«mar 2019 – ago 2020», a partir de los ordinales de día de un tramo de validación."""
    def mes(o: int) -> str:
        f = date.fromordinal(o)
        return "%s %d" % (_MESES[f.month - 1], f.year)

    desde, hasta = mes(inicio_ordinal), mes(fin_ordinal)
    return desde if desde == hasta else "%s – %s" % (desde, hasta)


def nombre_modelo(version: str) -> str:
    return "Modelo de volatilidad · versión %s" % version.lstrip("v")


def lectura_validacion(ev: Evaluacion) -> str:
    """Lo que dicen los números de la validación, para quien no sabe qué es un z."""
    texto = ("En datos que no había visto, el modelo se equivoca en promedio %s del rango. Repetir el rango de hoy "
             "se equivoca %s y usar el promedio de %d días, %s." % (
                 error_pct(ev.error), error_pct(ev.error_hoy), VENTANA_NORMAL, error_pct(ev.error_media)))
    if ev.supera_base:
        return texto + " Le gana a las dos con claridad: no parece casualidad."
    if ev.z_hoy >= Z_MINIMO or ev.z_media >= Z_MINIMO:
        return texto + " Solo le gana a una de las dos: no alcanza para activarlo."
    return texto + " No le gana a las bases con claridad: la diferencia podría ser casualidad."


def lectura_calibracion(bins: Sequence[BinCalibracion]) -> str:
    """Compara si, cuando el modelo espera más agitación, de verdad hay más."""
    con_datos = [b for b in bins if b.n >= 30]
    if len(con_datos) < 2:
        return "Todavía no hay suficientes predicciones en cada grupo para comparar."
    menos, mas = con_datos[0], con_datos[-1]
    if mas.real > menos.real * 1.05:
        return ("Sí: cuando espera un día más agitado, realmente lo es (%s frente a %s en los días que esperaba "
                "tranquilos). Por eso la predicción distingue días tranquilos de agitados." % (
                    veces(mas.real), veces(menos.real)))
    return "No: lo que espera el modelo apenas se parece a lo que ocurre. Conviene no fiarse de la predicción."


def lectura_nivel(ev: Evaluacion) -> str:
    return ("Acertó el nivel (baja / normal / alta) el %s de las veces; repetir el nivel de hoy acierta el %s. "
            "Como «baja» y «alta» son el %d %% de días cada una, decir siempre «normal» acertaría cerca del %d %%: "
            "el nivel es una guía, el número es lo que se evalúa." % (
                pct(ev.acierto_nivel), pct(ev.acierto_nivel_hoy), int(PERCENTIL_BAJO),
                int(PERCENTIL_ALTO - PERCENTIL_BAJO)))
