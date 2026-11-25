"""Textos y reglas de presentación de la pantalla de volatilidad. Python puro (sin tkinter): se prueba solo.

Todo número que ve el usuario sale de aquí, así las pestañas lo escriben igual.
La volatilidad NO usa verde ni rojo (no significa «bueno» ni «malo»): solo los aciertos y fallos del registro.
"""
import math
from datetime import date, datetime
from typing import Dict, List, Optional, Sequence

from simultradia.analisis.volatilidad import NOMBRES_FEATURES
from simultradia.domain.entities.prediccion_volatilidad_entity import PrediccionVolatilidad, SenalVolatilidad
from simultradia.domain.enums import NivelVolatilidad
from simultradia.domain.reglas.volatilidad import (
    PERCENTIL_ALTO, PERCENTIL_BAJO, VENTANA_NIVEL, VENTANA_NORMAL, Z_MINIMO, dia_de_la_vela_objetivo)
from simultradia.ia.volatilidad import BinCalibracion, Evaluacion

_ESPACIO = " "

AVISO = "Estimación estadística con fines educativos. No es asesoría financiera."

_TITULO_NIVEL = {NivelVolatilidad.BAJA: "TRANQUILO", NivelVolatilidad.NORMAL: "NORMAL", NivelVolatilidad.ALTA: "AGITADO"}
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


def numero_justo(valor: float, decimales: int = 2, con_signo: bool = False) -> str:
    """Hasta `decimales` decimales, y solo los que hacen falta: 2,0 -> «2»; 0,5 -> «0,5»; 0,05 -> «0,05»."""
    texto = "%.*f" % (decimales, valor)
    if "." in texto:
        texto = texto.rstrip("0").rstrip(".")
    if texto in ("0", "-0"):
        texto = "0"
    elif con_signo and valor > 0:
        texto = "+" + texto
    return texto.replace(".", ",")


def rango(valor: float) -> str:
    """Un rango diario (fracción del precio), con los decimales que hagan falta (máximo 2): 0,023 -> «2,3 %»."""
    return numero_justo(valor * 100) + _ESPACIO + "%"


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


_DIAS_SEMANA = ("lun", "mar", "mié", "jue", "vie", "sáb", "dom")


def dia_de_vela(fecha_objetivo: datetime) -> str:
    """«lun 23/11»: el día de la vela con la que se comprueba una predicción (día de mercado, no hora local)."""
    dia = dia_de_la_vela_objetivo(fecha_objetivo)
    return "%s %s" % (_DIAS_SEMANA[dia.weekday()], dia.strftime("%d/%m"))


def resultado(p: PrediccionVolatilidad) -> str:
    if p.acierto_nivel is None:
        return "Pendiente"
    return "Acertó" if p.acierto_nivel else "Falló"


def etiqueta_resultado(p: PrediccionVolatilidad) -> str:
    """Verde si acertó el nivel, rojo si falló, normal si falta."""
    return "" if p.acierto_nivel is None else "alza" if p.acierto_nivel else "baja"


def explicacion_nivel() -> str:
    return ("El nivel compara el rango esperado con los últimos %d días de ESTE activo: baja es el 25 %% más "
            "tranquilo, alta el 25 %% más agitado y normal lo demás." % VENTANA_NIVEL)


def explicacion_rango() -> str:
    return ("El rango es la distancia entre el máximo y el mínimo del día, como porcentaje del precio. "
            "No dice si el precio sube o baja: dice cuánto se mueve.")


def frase_intervalo(p: PrediccionVolatilidad) -> str:
    return "Con ~80 %% de probabilidad entre %s y %s." % (rango(p.rango_bajo), rango(p.rango_alto))


def frase_normal(p: PrediccionVolatilidad) -> str:
    return "Es %s; el promedio de %d días es %s." % (veces(p.veces_lo_normal), VENTANA_NORMAL, rango(p.rango_normal))


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


# ---------------------------------------------------------------------------- pestaña Volatilidad
def titulo_nivel(n: NivelVolatilidad) -> str:
    """«AGITADO», «NORMAL» o «TRANQUILO»: el nivel en grande."""
    return _TITULO_NIVEL[n]


def frase_percentil(n: NivelVolatilidad) -> str:
    """Qué significa el nivel, tal como se calcula: contra los últimos %d días del propio activo."""
    return {NivelVolatilidad.BAJA: "Más tranquilo que 3 de cada 4 días de los últimos %d." % VENTANA_NIVEL,
            NivelVolatilidad.NORMAL: "Dentro de lo habitual de los últimos %d días." % VENTANA_NIVEL,
            NivelVolatilidad.ALTA: "Más agitado que 3 de cada 4 días de los últimos %d." % VENTANA_NIVEL}[n]


def frase_hoy(p: PrediccionVolatilidad) -> str:
    """Lo que se movió hoy y qué espera la IA para mañana, comparado."""
    razon = p.rango_hoy / p.rango_normal if p.rango_normal else 1.0
    if p.rango_predicho > p.rango_hoy * 1.1:
        manana = "La IA espera que mañana se mueva más."
    elif p.rango_predicho < p.rango_hoy * 0.9:
        manana = "La IA espera que mañana se mueva menos."
    else:
        manana = "La IA espera algo parecido mañana."
    return "Es %s. %s" % (veces(razon), manana)


def uso_tamano(p: PrediccionVolatilidad) -> str:
    base = "Tamaño de la operación. "
    if p.nivel == NivelVolatilidad.ALTA:
        return base + ("Con un rango esperado de %s (%s) la misma cantidad de dinero arriesga más: conviene operar "
                       "menos cantidad." % (rango(p.rango_predicho), veces(p.veces_lo_normal)))
    if p.nivel == NivelVolatilidad.BAJA:
        return base + ("Se espera poco movimiento (%s): el mismo dinero arriesga menos que de costumbre." %
                       rango(p.rango_predicho))
    return base + "Se espera un movimiento habitual (%s): no hay motivo para cambiar el tamaño de siempre." % rango(
        p.rango_predicho)


def uso_stop(p: PrediccionVolatilidad) -> str:
    return ("Stop-loss. Uno más pegado al precio que el rango esperado (%s) tiene mucha probabilidad de saltar solo "
            "por el vaivén del día." % rango(p.rango_predicho))


def uso_direccion() -> str:
    return "No dice si sube o baja. Sirve para medir el riesgo, no para elegir dirección."


def frase_intervalo_corta(p: PrediccionVolatilidad) -> str:
    return "Casi seguro entre %s y %s" % (rango(p.rango_bajo), rango(p.rango_alto))


def texto_umbrales(p: PrediccionVolatilidad) -> str:
    return "Menos de %s = día tranquilo. Más de %s = día agitado (según sus últimos %d días)." % (
        rango(p.umbral_bajo), rango(p.umbral_alto), VENTANA_NIVEL)


# ---------------------------------------------------------------------------- escáner
FILTROS = (("todos", "Todos"), ("alta", "Alta"), ("normal", "Normal"), ("baja", "Baja"))


def filtrar(senales: Sequence[SenalVolatilidad], filtro: str) -> List[SenalVolatilidad]:
    if filtro == "todos":
        return list(senales)
    return [s for s in senales if s.prediccion.nivel.value == filtro]


def conteos(senales: Sequence[SenalVolatilidad]) -> Dict[str, int]:
    cuentas = {clave: 0 for clave, _t in FILTROS}
    cuentas["todos"] = len(senales)
    for s in senales:
        cuentas[s.prediccion.nivel.value] += 1
    return cuentas


def etiqueta_nivel(n: NivelVolatilidad) -> str:
    """Color de la fila del escáner: naranja si es agitado, celeste si es tranquilo, normal si no."""
    return {NivelVolatilidad.ALTA: "alerta", NivelVolatilidad.BAJA: "calma"}.get(n, "")


# ---------------------------------------------------------------------------- pestaña Evaluación
def titulo_veredicto(ev: Evaluacion) -> str:
    if ev.supera_base:
        return "Aprobado"
    if ev.z_hoy >= Z_MINIMO or ev.z_media >= Z_MINIMO:
        return "Aprobado solo a medias"
    return "No aprobado"


def explicacion_veredicto(ev: Evaluacion, inicio_ordinal: int, fin_ordinal: int) -> str:
    probado = "Probado en %d periodos, de %s, con datos que el modelo no había visto." % (
        len(ev.tramos), periodo(inicio_ordinal, fin_ordinal).replace(" – ", " a "))
    if ev.supera_base:
        return "Predice mejor el rango del día que las dos alternativas simples. %s Por eso queda activo." % probado
    if ev.z_hoy >= Z_MINIMO or ev.z_media >= Z_MINIMO:
        return ("Le gana a una de las dos alternativas simples pero no a la otra. %s No alcanza para activarlo." %
                probado)
    return ("No le gana con claridad a las alternativas simples: la diferencia podría ser casualidad. %s "
            "No se activa." % probado)


def ejemplo_error(error_log: float) -> str:
    """Qué significa el error medio con un caso concreto: un día de 2,0 %."""
    f = math.exp(error_log)
    return "Ejemplo: si un día el rango real es 2,0 %%, el modelo suele haber predicho entre %s y %s." % (
        pct(0.02 / f, 1), pct(0.02 * f, 1))


def tramos_ganados(ev: Evaluacion) -> int:
    return sum(1 for t in ev.tramos if t.error < t.error_hoy and t.error < t.error_media)


def siempre_normal() -> float:
    """Acierto de decir siempre «normal»: es la parte de días entre los dos percentiles."""
    return (PERCENTIL_ALTO - PERCENTIL_BAJO) / 100.0


def lectura_nivel(ev: Evaluacion) -> str:
    return ("Acertar el nivel es difícil: el modelo %s a decir siempre normal, porque la mitad de los días lo son. "
            "Fíate más del número del rango, que es lo que realmente se evalúa." % (
                "apenas supera" if ev.acierto_nivel > siempre_normal() else "no supera"))


def lectura_calibracion(bins: Sequence[BinCalibracion]) -> str:
    """Compara si, cuando el modelo espera más agitación, de verdad hay más."""
    con_datos = [b for b in bins if b.n >= 30]
    if len(con_datos) < 2:
        return "Todavía no hay suficientes predicciones en cada grupo para comparar."
    menos, mas = con_datos[0], con_datos[-1]
    if mas.real > menos.real * 1.05:
        texto = ("Sí distingue: cuando espera un día %s, de verdad es %s; cuando espera uno %s, %s." % (
            mas.etiqueta.lower(), veces(mas.real).replace(" lo normal", ""),
            menos.etiqueta.lower(), veces(menos.real).replace(" lo normal", "")))
        sesgo = sum(b.real - b.predicho for b in con_datos) / len(con_datos)
        if abs(sesgo) >= 0.05:
            texto += " Además es un poco %s: lo real sale en promedio %s por %s de lo esperado." % (
                "conservador" if sesgo > 0 else "exagerado", numero(abs(sesgo), 1) + "×",
                "encima" if sesgo > 0 else "debajo")
        return texto
    return "No distingue: lo que espera el modelo apenas se parece a lo que ocurre. Conviene no fiarse de la predicción."


# ---------------------------------------------------------------------------- pestaña Registro
def diferencia_pp(p: PrediccionVolatilidad) -> str:
    """Real menos predicho, en puntos porcentuales: «+0,3 pp»."""
    if p.rango_real is None:
        return "—"
    return numero_justo((p.rango_real - p.rango_predicho) * 100, con_signo=True) + " pp"


def niveles(p: PrediccionVolatilidad) -> str:
    """«Alta → Normal»: el nivel que se esperaba y el que fue."""
    return "%s → %s" % (nivel(p.nivel), nivel(p.nivel_real) if p.nivel_real else "—")


def error_contra_hoy(mejora: Optional[float]) -> str:
    """La mejora frente a repetir el rango de hoy como cambio del error: 0,21 -> «−21 %»."""
    if mejora is None:
        return "—"
    return ("−" if mejora >= 0 else "+") + pct(abs(mejora))
