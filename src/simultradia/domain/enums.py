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
