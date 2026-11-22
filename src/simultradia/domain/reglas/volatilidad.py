"""Reglas de la predicción de volatilidad: qué se predice, cómo se mide el nivel y qué cuenta como "mejor que la base".

Se predice el RANGO del día siguiente: (máximo - mínimo) / cierre de la vela diaria, como fracción (0,023 = 2,3 %).
Python puro: lo comparten el motor, los servicios y las pantallas.
"""
import math
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional, Sequence

from simultradia.domain.enums import NivelVolatilidad, TipoActivo

NOMBRE_MODELO = "volatilidad_1d"
HORIZONTE = 1                      # un día adelante
VENTANA_NORMAL = 20                # velas con que se mide el rango "normal" de un activo
VENTANA_NIVEL = 90                 # velas con que se mide qué es baja, normal o alta
PERCENTIL_BAJO = 25.0              # por debajo del percentil 25 de esas 90 velas: volatilidad baja
PERCENTIL_ALTO = 75.0              # por encima del percentil 75: alta
PISO_RANGO = 1e-4                  # un día sin máximo ni mínimo (0 %) se trata como 0,01 %: así existe el logaritmo
TRAMOS_VALIDACION = 4
FRACCION_ENTRENAMIENTO_INICIAL = 0.4
Z_MINIMO = 1.65                    # el modelo solo se activa si supera a las DOS bases con este z o más
MARGEN_INTERVALO = 1.2816          # z de un intervalo del 80 % (10 % por abajo, 10 % por arriba)
NIVELES = (NivelVolatilidad.BAJA, NivelVolatilidad.NORMAL, NivelVolatilidad.ALTA)


def velas_de_purga(horizonte: int = HORIZONTE) -> int:
    """Velas que se descartan entre entrenamiento y prueba: la etiqueta mira `horizonte` velas adelante."""
    return int(horizonte * 1.5) + 4


def percentil(valores: Sequence[float], q: float) -> float:
    """Percentil `q` (0 a 100) con interpolación lineal. `valores` no puede estar vacío."""
    orden = sorted(valores)
    if len(orden) == 1:
        return float(orden[0])
    posicion = (len(orden) - 1) * q / 100.0
    abajo = int(math.floor(posicion))
    arriba = min(abajo + 1, len(orden) - 1)
    return float(orden[abajo] + (orden[arriba] - orden[abajo]) * (posicion - abajo))


def umbrales_de(rangos_recientes: Sequence[float]) -> Optional[tuple]:
    """(umbral_bajo, umbral_alto) a partir de los últimos rangos del activo; None si hay muy pocos."""
    if len(rangos_recientes) < 20:
        return None
    return percentil(rangos_recientes, PERCENTIL_BAJO), percentil(rangos_recientes, PERCENTIL_ALTO)


def nivel_de(rango: float, umbral_bajo: float, umbral_alto: float) -> NivelVolatilidad:
    if rango <= umbral_bajo:
        return NivelVolatilidad.BAJA
    if rango >= umbral_alto:
        return NivelVolatilidad.ALTA
    return NivelVolatilidad.NORMAL


def intervalo_80(rango: float, sigma_log: float) -> tuple:
    """(bajo, alto) del rango esperado con ~80 % de probabilidad, a partir del error típico (en logaritmo)."""
    return rango * math.exp(-MARGEN_INTERVALO * sigma_log), rango * math.exp(MARGEN_INTERVALO * sigma_log)


def a_utc(momento: datetime) -> datetime:
    """El mismo instante en UTC. Una hora sin zona se toma como UTC.

    Las velas diarias empiezan a las 00:00 UTC, pero PostgreSQL las devuelve en la zona de la sesión (por ejemplo
    -03: el día anterior a las 21:00). El día de una vela y su día de la semana son los de UTC, no los locales."""
    if momento.tzinfo is None:
        return momento.replace(tzinfo=timezone.utc)
    return momento.astimezone(timezone.utc)


def dia_utc(momento: datetime) -> date:
    """El día (UTC) al que pertenece la vela que empieza en `momento`."""
    return a_utc(momento).date()


def fecha_objetivo(momento_vela: datetime, tipo: TipoActivo) -> datetime:
    """Cuándo se puede evaluar la predicción hecha con la vela que empieza en `momento_vela`: al cerrar la
    vela del día siguiente (cripto: todos los días; lo demás: de lunes a viernes; los feriados no se conocen:
    la evaluación espera a que esa vela exista). Se devuelve en UTC."""
    dia = a_utc(momento_vela) + timedelta(days=1)
    while tipo != TipoActivo.CRIPTO and dia.weekday() >= 5:
        dia += timedelta(days=1)
    return dia + timedelta(days=1)


def dia_de_la_vela_objetivo(fecha: datetime) -> date:
    """El día de la vela que se compara con la predicción (la `fecha_objetivo` es cuando esa vela cierra)."""
    return dia_utc(fecha) - timedelta(days=1)
