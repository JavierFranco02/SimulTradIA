"""Recuerda quién tiene la sesión iniciada mientras la app está abierta.

No es global: App crea UNA instancia y se la entrega (la "inyecta") al Navegador
y a los controladores que la necesitan.
"""
from typing import Optional

from simultradia.domain.entities.usuario_entity import Usuario


class Session:
    def __init__(self) -> None:
        self._usuario: Optional[Usuario] = None

    def iniciar(self, usuario: Usuario) -> None:
        self._usuario = usuario

    def cerrar(self) -> None:
        self._usuario = None

    @property
    def usuario(self) -> Optional[Usuario]:
        return self._usuario

    @property
    def esta_iniciada(self) -> bool:
        return self._usuario is not None

    @property
    def es_admin(self) -> bool:
        return self._usuario is not None and self._usuario.es_admin
