"""Reglas de negocio PURAS que usan varias partes de la app.

Ejemplos que irán aquí: cálculo de comisión, precio promedio de una posición,
ejecución de una orden. Las usan operar, replay, backtesting y el worker, por eso
hay UNA sola implementación.

Reglas: Python puro (sin BD, sin tkinter, sin red) y funciones que reciben datos
y devuelven datos. Dinero con Decimal.
"""
