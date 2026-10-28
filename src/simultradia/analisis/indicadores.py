"""Indicadores técnicos sobre una serie de cierres. Python puro, sin BD ni interfaz.

Cada función devuelve una lista del MISMO largo que la entrada; las posiciones donde
todavía no hay datos suficientes valen None.
"""
from typing import List, Optional, Sequence


def sma(valores: Sequence[float], periodo: int) -> List[Optional[float]]:
    """Media móvil simple: promedio de los últimos `periodo` valores."""
    resultado: List[Optional[float]] = [None] * len(valores)
    suma = 0.0
    for i, valor in enumerate(valores):
        suma += valor
        if i >= periodo:
            suma -= valores[i - periodo]
        if i >= periodo - 1:
            resultado[i] = suma / periodo
    return resultado


def ema(valores: Sequence[float], periodo: int) -> List[Optional[float]]:
    """Media móvil exponencial: pesa más los valores recientes. Arranca con la SMA."""
    resultado: List[Optional[float]] = [None] * len(valores)
    if len(valores) < periodo:
        return resultado
    anterior = sum(valores[:periodo]) / periodo
    resultado[periodo - 1] = anterior
    factor = 2.0 / (periodo + 1)
    for i in range(periodo, len(valores)):
        anterior = valores[i] * factor + anterior * (1 - factor)
        resultado[i] = anterior
    return resultado


def bollinger(valores: Sequence[float], periodo: int = 20, desviaciones: float = 2.0):
    """Bandas de Bollinger: la media de `periodo` valores y dos bandas a `desviaciones`
    desviaciones estándar por arriba y por abajo. Devuelve (media, superior, inferior)."""
    media = sma(valores, periodo)
    superior: List[Optional[float]] = [None] * len(valores)
    inferior: List[Optional[float]] = [None] * len(valores)
    for i in range(periodo - 1, len(valores)):
        ventana = valores[i - periodo + 1:i + 1]
        desviacion = (sum((x - media[i]) ** 2 for x in ventana) / periodo) ** 0.5
        superior[i] = media[i] + desviaciones * desviacion
        inferior[i] = media[i] - desviaciones * desviacion
    return media, superior, inferior


def _valor_rsi(ganancia: float, perdida: float) -> float:
    if perdida == 0:
        return 50.0 if ganancia == 0 else 100.0
    return 100.0 - 100.0 / (1.0 + ganancia / perdida)


def rsi(valores: Sequence[float], periodo: int = 14) -> List[Optional[float]]:
    """Índice de fuerza relativa (0 a 100), con el suavizado de Wilder.
    Por debajo de 30 suele indicar sobreventa; por encima de 70, sobrecompra."""
    resultado: List[Optional[float]] = [None] * len(valores)
    if len(valores) <= periodo:
        return resultado
    cambios = [valores[i] - valores[i - 1] for i in range(1, len(valores))]
    ganancia = sum(max(c, 0.0) for c in cambios[:periodo]) / periodo
    perdida = sum(max(-c, 0.0) for c in cambios[:periodo]) / periodo
    resultado[periodo] = _valor_rsi(ganancia, perdida)
    for i in range(periodo, len(cambios)):
        ganancia = (ganancia * (periodo - 1) + max(cambios[i], 0.0)) / periodo
        perdida = (perdida * (periodo - 1) + max(-cambios[i], 0.0)) / periodo
        resultado[i + 1] = _valor_rsi(ganancia, perdida)
    return resultado


def macd(valores: Sequence[float], rapida: int = 12, lenta: int = 26, senal: int = 9):
    """MACD: diferencia entre dos EMA, su línea de señal (una EMA de esa diferencia) y el
    histograma (diferencia entre ambas). Devuelve (macd, señal, histograma)."""
    n = len(valores)
    linea: List[Optional[float]] = [
        None if a is None or b is None else a - b
        for a, b in zip(ema(valores, rapida), ema(valores, lenta))]
    linea_senal: List[Optional[float]] = [None] * n
    primero = next((i for i, v in enumerate(linea) if v is not None), None)
    if primero is not None:
        for k, v in enumerate(ema(linea[primero:], senal)):
            linea_senal[primero + k] = v
    histograma = [None if a is None or b is None else a - b for a, b in zip(linea, linea_senal)]
    return linea, linea_senal, histograma
