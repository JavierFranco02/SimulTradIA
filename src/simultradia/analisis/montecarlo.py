"""Proyección de precio por Monte Carlo. Python puro, sin BD ni interfaz.

NO es la predicción de la IA: solo muestra qué tan abierto está el abanico de precios posibles
si el activo se mueve como lo hizo hace poco. Remuestrea (con reemplazo) los retornos reales
recientes, restándoles su media para no suponer ninguna tendencia.
"""
import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

PERCENTILES = (5, 25, 50, 75, 95)


@dataclass
class Proyeccion:
    precio_inicial: float
    dias: int
    simulaciones: int
    percentiles: Dict[int, List[float]] = field(default_factory=dict)   # {5: [dia1..diaN], ...}
    prob_subir: float = 0.0                                             # P(cerrar por encima del inicial)
    prob_tocar_nivel: Optional[float] = None                            # P(tocar `nivel` en algún día)


def _percentil(ordenados: Sequence[float], p: int) -> float:
    posicion = (len(ordenados) - 1) * p / 100.0
    abajo = int(math.floor(posicion))
    arriba = min(abajo + 1, len(ordenados) - 1)
    return ordenados[abajo] + (ordenados[arriba] - ordenados[abajo]) * (posicion - abajo)


def proyectar(cierres: Sequence[float], dias: int, simulaciones: int = 5000, ventana: int = 250,
              nivel: Optional[float] = None, semilla: Optional[int] = None,
              precio_actual: Optional[float] = None) -> Proyeccion:
    """Simula `simulaciones` caminos de `dias` días. `precio_actual` reemplaza al último cierre
    como punto de partida (útil si hay una cotización más nueva). `nivel` es, por ejemplo, el
    stop-loss del usuario."""
    if dias < 1 or simulaciones < 1:
        raise ValueError("Los días y las simulaciones deben ser al menos 1.")
    recientes = list(cierres[-(ventana + 1):])
    if len(recientes) < 31:
        raise ValueError("Hay muy pocos datos para proyectar (se necesitan al menos 30 retornos).")
    logs = [math.log(recientes[i] / recientes[i - 1]) for i in range(1, len(recientes))
            if recientes[i - 1] > 0 and recientes[i] > 0]
    media = sum(logs) / len(logs)
    logs = [x - media for x in logs]

    inicio = float(precio_actual if precio_actual is not None else recientes[-1])
    azar = random.Random(semilla)
    por_dia = [[] for _ in range(dias)]
    subieron = 0
    tocaron = 0
    for _ in range(simulaciones):
        precio = inicio
        toco = False
        for d in range(dias):
            precio *= math.exp(azar.choice(logs))
            por_dia[d].append(precio)
            if nivel is not None and not toco:
                toco = precio <= nivel if nivel < inicio else precio >= nivel
        subieron += precio > inicio
        tocaron += toco

    resultado = Proyeccion(precio_inicial=inicio, dias=dias, simulaciones=simulaciones)
    ordenados = [sorted(p) for p in por_dia]
    for p in PERCENTILES:
        resultado.percentiles[p] = [_percentil(o, p) for o in ordenados]
    resultado.prob_subir = subieron / simulaciones
    if nivel is not None:
        resultado.prob_tocar_nivel = tocaron / simulaciones
    return resultado
