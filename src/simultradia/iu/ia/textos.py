"""Textos y reglas de presentación de la pantalla de IA. Python puro (sin tkinter): se prueba solo.

Todo número que ve el usuario sale de aquí, así las cuatro pestañas lo escriben igual.
"""
from datetime import date, datetime
from typing import Optional, Sequence

from simultradia.domain.entities.prediccion_entity import Prediccion
from simultradia.domain.enums import DireccionPrediccion
from simultradia.domain.reglas.prediccion import nivel_de_confianza
from simultradia.analisis.features import NOMBRES_FEATURES
from simultradia.ia.entrenamiento import BinCalibracion, Evaluacion

_ESPACIO = " "

AVISO = "Estimación estadística con fines educativos. No es asesoría financiera."

_DIRECCION = {DireccionPrediccion.ALCISTA: "Alcista", DireccionPrediccion.LATERAL: "Lateral",
              DireccionPrediccion.BAJISTA: "Bajista"}
_FACTOR = dict(zip(NOMBRES_FEATURES, (
    "Retorno 1 día", "Retorno 3 días", "Retorno 5 días", "Retorno 10 días", "Retorno 20 días",
    "RSI 14", "MACD (histograma)", "Distancia a la SMA 20", "Distancia a la EMA 50",
    "Posición en Bollinger", "Rango medio (ATR)", "Volatilidad 20 días", "Volumen relativo",
    "Rango del día")))


def pct(valor: float, decimales: int = 0) -> str:
    """0,543 -> «54 %». El valor va de 0 a 1."""
    return ("%.*f" % (decimales, valor * 100)).replace(".", ",") + _ESPACIO + "%"


def numero(valor: float, decimales: int = 2, con_signo: bool = False) -> str:
    texto = ("%+.*f" if con_signo else "%.*f") % (decimales, valor)
    return texto.replace(".", ",")


def direccion(d: DireccionPrediccion) -> str:
    return _DIRECCION[d]


def etiqueta_fila(d: DireccionPrediccion) -> str:
    """Etiqueta de color de la tabla: verde si sube, rojo si baja, normal si es lateral."""
    return {DireccionPrediccion.ALCISTA: "alza", DireccionPrediccion.BAJISTA: "baja"}.get(d, "")


def factor(nombre: str) -> str:
    return _FACTOR.get(nombre, nombre)


def confianza(p: float) -> str:
    """«Media · 54 %»."""
    return "%s%s·%s%s" % (nivel_de_confianza(p).capitalize(), _ESPACIO, _ESPACIO, pct(p))


def fecha(momento: Optional[datetime]) -> str:
    return "—" if momento is None else momento.astimezone().strftime("%d/%m/%Y")


def resultado(p: Prediccion) -> str:
    if p.acierto is None:
        return "Pendiente"
    return "Acertó" if p.acierto else "Falló"


def etiqueta_resultado(p: Prediccion) -> str:
    """Verde si acertó, rojo si falló, normal si falta."""
    return "" if p.acierto is None else "alza" if p.acierto else "baja"


# ----------------------------------------------------------------- lenguaje llano
AZAR = 1.0 / 3.0            # con tres escenarios posibles, elegir al azar acierta una de cada tres

_MESES = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")


def dias(horizonte: int) -> str:
    return "%d %s" % (horizonte, "día" if horizonte == 1 else "días")


def escenario_corto(d: DireccionPrediccion) -> str:
    """Qué significa cada escenario, en pocas palabras (va bajo cada tarjeta de probabilidad)."""
    return {DireccionPrediccion.BAJISTA: "Cae más de lo habitual",
            DireccionPrediccion.LATERAL: "Se mueve poco",
            DireccionPrediccion.ALCISTA: "Sube más de lo habitual"}[d]


def frase_direccion(d: DireccionPrediccion, horizonte: int) -> str:
    """Una frase que dice lo mismo que la señal, sin jerga."""
    plazo = "en " + dias(horizonte)
    return {DireccionPrediccion.ALCISTA: "La IA espera que el precio suba de forma marcada %s." % plazo,
            DireccionPrediccion.BAJISTA: "La IA espera que el precio caiga de forma marcada %s." % plazo,
            DireccionPrediccion.LATERAL: "La IA espera que el precio se mueva poco %s, sin una subida ni una caída "
                                         "marcadas." % plazo}[d]


def nivel_confianza(p: float) -> str:
    """«Baja», «Media» o «Alta»."""
    return nivel_de_confianza(p).capitalize()


def frase_confianza(p: float) -> str:
    """Pone la probabilidad elegida frente al azar, que es lo que da sentido al número."""
    return "El azar daría %s: esta señal queda %s puntos por encima." % (pct(AZAR), numero((p - AZAR) * 100, 0))


def explicacion_escenarios() -> str:
    return ("«Más de lo habitual» significa más de la mitad de lo que suele oscilar este activo en ese plazo. "
            "Las tres probabilidades suman 100 %.")


def periodo(inicio_ordinal: int, fin_ordinal: int) -> str:
    """«mar 2019 – ago 2020», a partir de los ordinales de día de un tramo de validación."""
    def mes(o: int) -> str:
        f = date.fromordinal(o)
        return "%s %d" % (_MESES[f.month - 1], f.year)

    desde, hasta = mes(inicio_ordinal), mes(fin_ordinal)
    return desde if desde == hasta else "%s – %s" % (desde, hasta)


def nombre_modelo(horizonte: int, version: str) -> str:
    return "Modelo a %s · versión %s" % (dias(horizonte), version.lstrip("v"))


def lectura_validacion(ev: Evaluacion) -> str:
    """Lo que dicen los números de la validación, para quien no sabe qué es un z."""
    base = ("En datos que no había visto, el modelo acertó %s de las veces. Adivinar siempre el escenario más común "
            "habría acertado %s" % (pct(ev.acierto, 1), pct(ev.base, 1)))
    if ev.supera_base:
        return base + ": la diferencia (%s pp) es lo bastante grande como para no ser casualidad." % numero(
            ev.ventaja, 1, con_signo=True)
    return base + ": la diferencia (%s pp) es demasiado pequeña para descartar que sea casualidad." % numero(
        ev.ventaja, 1, con_signo=True)


def lectura_calibracion(bins: Sequence[BinCalibracion]) -> str:
    """Compara el acierto del grupo menos seguro con el más seguro que tenga datos suficientes."""
    con_datos = [b for b in bins if b.n >= 30]
    if len(con_datos) < 2:
        return "Todavía no hay suficientes predicciones en cada nivel para comparar."
    menos, mas = con_datos[0], con_datos[-1]
    if mas.acierto > menos.acierto:
        return ("Sí: cuando el modelo está más seguro, acierta más (%s con confianza %s, contra %s con confianza %s). "
                "Por eso la confianza de cada señal es una guía útil." % (
                    pct(mas.acierto), mas.etiqueta, pct(menos.acierto), menos.etiqueta))
    return "No: la confianza no distingue los aciertos de los errores. Conviene no fiarse del porcentaje."
