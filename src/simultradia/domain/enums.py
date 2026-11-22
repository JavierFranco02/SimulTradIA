"""Listas cerradas de valores. Son el espejo de los ENUM de PostgreSQL."""
from enum import Enum


class RolUsuario(str, Enum):
    USUARIO = "usuario"
    ADMIN = "admin"


class TipoActivo(str, Enum):
    ACCION = "accion"
    CRIPTO = "cripto"
    ETF = "etf"
    DIVISA = "divisa"
    INDICE = "indice"
    BONO = "bono"


class IntervaloVela(str, Enum):
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1w"


class LadoOrden(str, Enum):
    COMPRA = "compra"
    VENTA = "venta"


class TipoOrden(str, Enum):
    MERCADO = "mercado"
    LIMITE = "limite"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    STOP_LIMITE = "stop_limite"


class EstadoOrden(str, Enum):
    PENDIENTE = "pendiente"
    PARCIAL = "parcial"
    EJECUTADA = "ejecutada"
    CANCELADA = "cancelada"
    RECHAZADA = "rechazada"
    EXPIRADA = "expirada"


class DireccionPrediccion(str, Enum):
    ALCISTA = "alcista"
    LATERAL = "lateral"
    BAJISTA = "bajista"


class NivelVolatilidad(str, Enum):
    """Qué tan agitado se espera el día, contra los últimos 90 días del propio activo."""
    BAJA = "baja"
    NORMAL = "normal"
    ALTA = "alta"


class TipoModeloIA(str, Enum):
    DIRECCION = "direccion"
    VOLATILIDAD = "volatilidad"
    SENTIMIENTO = "sentimiento"
    REGIMEN = "regimen"


class EstadoModelo(str, Enum):
    ENTRENANDO = "entrenando"
    ACTIVO = "activo"
    ARCHIVADO = "archivado"
    FALLIDO = "fallido"


class EstadoProceso(str, Enum):
    PENDIENTE = "pendiente"
    EJECUTANDO = "ejecutando"
    COMPLETADO = "completado"
    FALLIDO = "fallido"
