"""Tareas del worker (proceso sin ventanas): ingesta de datos, evaluar predicciones vencidas,
ejecutar órdenes pendientes.

`worker.py` solo PROGRAMA cuándo corre cada tarea; cada archivo de aquí es una tarea
corta que llama a un servicio. El armado de servicios es `composition.crear_servicios`.
"""
