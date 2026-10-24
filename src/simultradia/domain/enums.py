"""Listas cerradas de valores. Son el espejo de los ENUM de PostgreSQL."""
from enum import Enum


class RolUsuario(str, Enum):
    USUARIO = "usuario"
    ADMIN = "admin"
