"""Una predicción de volatilidad (espejo de predicciones_volatilidad) y lo que se arma con ella."""
import math
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Tuple

from simultradia.domain.enums import NivelVolatilidad

Factor = Tuple[str, float, Optional[float]]       # (nombre, aporte, valor del factor)


@dataclass
class PrediccionVolatilidad:
    id_activo: int
    id_modelo: int
    generada_en: datetime
    fecha_objetivo: datetime
    precio_referencia: Decimal                    # cierre de la última vela diaria cerrada
    rango_predicho: float                         # fracción del precio: 0,023 = 2,3 %
    rango_bajo: float                             # intervalo de ~80 %
    rango_alto: float
    rango_hoy: float                              # la base «repetir hoy»
    rango_normal: float                           # la base «promedio de 20 días»
    umbral_bajo: float                            # con qué se decidió el nivel (se guardan para evaluar igual)
    umbral_alto: float
    nivel: NivelVolatilidad
    factores: List[Factor] = field(default_factory=list)
    id_prediccion: Optional[int] = None
    rango_real: Optional[float] = None            # lo completa la evaluación
    nivel_real: Optional[NivelVolatilidad] = None
    acierto_nivel: Optional[bool] = None
    evaluada_en: Optional[datetime] = None

    @property
    def veces_lo_normal(self) -> float:
        return self.rango_predicho / self.rango_normal if self.rango_normal else 0.0

    @property
    def error(self) -> Optional[float]:
        """Error en logaritmo del modelo ya evaluada (0 = clavó el rango)."""
        if self.rango_real is None:
            return None
        return abs(math.log(self.rango_predicho / self.rango_real))

    @property
    def error_hoy(self) -> Optional[float]:
        """Lo que se habría equivocado «repetir el rango de hoy»."""
        if self.rango_real is None or self.rango_hoy <= 0:
            return None
        return abs(math.log(self.rango_hoy / self.rango_real))

    @property
    def dentro_del_intervalo(self) -> Optional[bool]:
        if self.rango_real is None:
            return None
        return self.rango_bajo <= self.rango_real <= self.rango_alto


@dataclass
class SenalVolatilidad:
    """Una predicción con el nombre del activo: una fila del escáner."""
    prediccion: PrediccionVolatilidad
    ticker: str
    nombre: str


@dataclass(frozen=True)
class PrecisionVivo:
    """Qué tan bien salieron las predicciones YA vencidas (no es la validación del entrenamiento)."""
    evaluadas: int
    aciertos_nivel: int
    error_modelo: Optional[float]     # error medio en logaritmo
    error_hoy: Optional[float]        # lo mismo si se hubiera repetido el rango de hoy
    dentro_intervalo: int

    @property
    def porcentaje_nivel(self) -> Optional[float]:
        return self.aciertos_nivel / self.evaluadas * 100.0 if self.evaluadas else None

    @property
    def porcentaje_intervalo(self) -> Optional[float]:
        return self.dentro_intervalo / self.evaluadas * 100.0 if self.evaluadas else None

    @property
    def mejora_hoy(self) -> Optional[float]:
        """0,12 = el modelo se equivoca 12 % menos que repetir el rango de hoy."""
        if not self.evaluadas or not self.error_hoy or self.error_modelo is None:
            return None
        return 1.0 - self.error_modelo / self.error_hoy


@dataclass(frozen=True)
class EstadoCiclo:
    """Cómo va el ciclo de predicciones (lo ve el administrador)."""
    ultima_generada_en: Optional[datetime]
    de_hoy: int
    pendientes: int
    evaluadas: int
