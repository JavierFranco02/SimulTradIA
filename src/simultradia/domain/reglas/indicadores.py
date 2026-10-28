"""Parámetros de los indicadores del gráfico.

Los usan el servicio que los calcula, el dibujo (para los rótulos) y la pantalla (para los
interruptores): por eso hay UNA sola definición.
"""
PERIODO_SMA = 20
PERIODO_EMA = 50
PERIODO_BOLLINGER = 20
DESVIACIONES_BOLLINGER = 2.0
PERIODO_RSI = 14
MACD_RAPIDA, MACD_LENTA, MACD_SENAL = 12, 26, 9
