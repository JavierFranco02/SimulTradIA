"""Ayuda compartida por los servicios que validan formularios."""
from typing import Dict, Optional

from simultradia.core.exceptions import DatosInvalidos


def lanzar_si_hay_errores(errores: Dict[str, Optional[str]]) -> None:
    """Recibe {campo: mensaje o None}. Si algún campo tiene mensaje, avisa de todos a la vez."""
    reales = {campo: mensaje for campo, mensaje in errores.items() if mensaje}
    if reales:
        raise DatosInvalidos(reales)
