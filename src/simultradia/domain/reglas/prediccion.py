"""Reglas de la predicción de dirección: horizontes, umbral y qué cuenta como "mejor que el azar".

Las usan el cálculo de features (cómo se etiqueta), el entrenamiento (cómo se valida) y la
pantalla (cómo se rotula la confianza), por eso hay UNA sola definición.
"""
from datetime import datetime, timedelta
from typing import Tuple

from simultradia.domain.enums import DireccionPrediccion, TipoActivo

# Días hacia adelante que se predicen. Cada uno es un modelo aparte.
HORIZONTES: Tuple[int, ...] = (1, 3, 5, 10)
HORIZONTE_INICIAL = 5

# Clase (índice de las probabilidades) -> dirección que se guarda y se muestra.
DIRECCIONES = (DireccionPrediccion.BAJISTA, DireccionPrediccion.LATERAL, DireccionPrediccion.ALCISTA)

# Clases, en el orden de las probabilidades: índice 0, 1, 2.
CLASES: Tuple[str, ...] = ("bajista", "lateral", "alcista")
BAJISTA, LATERAL, ALCISTA = 0, 1, 2

# Ventana (en días) de la volatilidad con que se mide qué es un "movimiento grande".
VENTANA_VOLATILIDAD = 20
# El retorno a `h` días es alcista/bajista si supera FACTOR_UMBRAL * volatilidad * raíz(h).
FACTOR_UMBRAL = 0.5

# Validación walk-forward.
TRAMOS_VALIDACION = 4
FRACCION_ENTRENAMIENTO_INICIAL = 0.4
# Un modelo "supera la base" si su estadístico z llega a este valor (≈ 95 % de confianza).
Z_MINIMO = 1.65


def dias_de_purga(horizonte: int) -> int:
    """Días de calendario que se descartan entre entrenamiento y prueba: la etiqueta de las
    últimas filas de entrenamiento mira `horizonte` días adelante y no debe tocar la prueba."""
    return int(horizonte * 1.5) + 4


def nivel_de_confianza(probabilidad: float) -> str:
    """Rótulo de la probabilidad de la clase elegida: baja, media o alta."""
    if probabilidad < 0.45:
        return "baja"
    if probabilidad < 0.60:
        return "media"
    return "alta"


def fecha_objetivo(momento_vela: datetime, horizonte: int, tipo: TipoActivo) -> datetime:
    """Cuándo se podrá evaluar una predicción hecha con la vela diaria que empieza en `momento_vela`:
    al cerrar la vela número `horizonte` después de esa. La cripto opera todos los días; lo demás,
    de lunes a viernes (los feriados no se conocen: la evaluación espera a que exista la vela)."""
    dia = momento_vela
    pendientes = horizonte
    while pendientes:
        dia += timedelta(days=1)
        if tipo == TipoActivo.CRIPTO or dia.weekday() < 5:
            pendientes -= 1
    return dia + timedelta(days=1)
