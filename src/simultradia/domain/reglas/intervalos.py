"""Qué intervalos de vela existen y cuáles se guardan o se arman al vuelo.

Los usan la ingesta (qué descargar), el servicio del gráfico (qué leer) y el motor
de análisis (cómo agrupar), por eso hay UNA sola definición.
"""
from typing import Dict, Tuple

from simultradia.domain.enums import IntervaloVela as I

SEGUNDOS: Dict[I, int] = {
    I.M1: 60, I.M5: 300, I.M15: 900, I.H1: 3600, I.H4: 14400, I.D1: 86400, I.W1: 604800,
}

# Intervalos que se descargan y guardan en la base: intervalo -> días de historia.
GUARDADOS: Dict[I, int] = {I.M15: 60, I.H1: 365, I.D1: 1825}

# Intervalos que NO se guardan: se arman agrupando las velas de otro intervalo.
DERIVADOS: Dict[I, I] = {I.H4: I.H1, I.W1: I.D1}

# Los que ofrece el gráfico, en el orden en que se muestran.
DISPONIBLES: Tuple[I, ...] = (I.M15, I.H1, I.H4, I.D1, I.W1)


def base_de(intervalo: I) -> I:
    """El intervalo que realmente está en la base para poder mostrar `intervalo`."""
    return DERIVADOS.get(intervalo, intervalo)
