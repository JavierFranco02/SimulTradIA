"""Un modelo de IA entrenado (espejo de modelos_ia)."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional

from simultradia.domain.enums import EstadoModelo, TipoModeloIA


@dataclass
class ModeloIA:
    nombre: str                                  # 'direccion_5d'
    version: str                                 # 'v3'
    tipo: TipoModeloIA = TipoModeloIA.DIRECCION
    algoritmo: Optional[str] = None
    horizonte_dias: Optional[int] = None
    estado: EstadoModelo = EstadoModelo.ENTRENANDO
    parametros: Dict = field(default_factory=dict)
    metricas: Dict = field(default_factory=dict)  # la evaluación walk-forward (ia/serializacion.py)
    ruta_artefacto: Optional[str] = None
    id_modelo: Optional[int] = None
    entrenado_en: Optional[datetime] = None
    creado_en: Optional[datetime] = None
