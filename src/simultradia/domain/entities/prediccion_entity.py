"""Una predicción de dirección (espejo de predicciones_direccion) y lo que se arma con ella."""
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from simultradia.domain.enums import DireccionPrediccion


@dataclass
class Prediccion:
    id_activo: int
    id_modelo: int
    horizonte_dias: int
    generada_en: datetime
    fecha_objetivo: datetime
    direccion: DireccionPrediccion
    prob_alcista: float
    prob_bajista: float
    prob_lateral: float
    confianza: float                              # la probabilidad de la dirección elegida
    precio_referencia: Decimal                    # cierre de la última vela diaria cerrada
    id_prediccion: Optional[int] = None
    precio_resultado: Optional[Decimal] = None    # lo completa la evaluación
    direccion_real: Optional[DireccionPrediccion] = None
    acierto: Optional[bool] = None
    evaluada_en: Optional[datetime] = None


@dataclass
class SenalActivo:
    """Una predicción con el nombre del activo: una fila del escáner."""
    prediccion: Prediccion
    ticker: str
    nombre: str


@dataclass(frozen=True)
class PrecisionVivo:
    """Aciertos REALES de las predicciones ya vencidas (no es la validación del entrenamiento)."""
    evaluadas: int
    aciertos: int
    evaluadas_90d: int
    aciertos_90d: int

    @property
    def porcentaje(self) -> Optional[float]:
        return self.aciertos / self.evaluadas * 100.0 if self.evaluadas else None

    @property
    def porcentaje_90d(self) -> Optional[float]:
        return self.aciertos_90d / self.evaluadas_90d * 100.0 if self.evaluadas_90d else None


@dataclass(frozen=True)
class EstadoCiclo:
    """Cómo va el ciclo de predicciones (lo ve el administrador)."""
    ultima_generada_en: Optional[datetime]
    de_hoy: int                  # predicciones generadas hoy (día UTC)
    pendientes: int              # todavía sin evaluar
    evaluadas: int
