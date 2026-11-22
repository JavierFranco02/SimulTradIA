"""Entrenamiento y evaluación del modelo de volatilidad. Sin BD ni interfaz.

El modelo predice cuántas veces lo normal será el rango del día siguiente (en logaritmo; ver
`analisis.volatilidad`). La validación es walk-forward: se entrena con el pasado y se prueba en un bloque
posterior, con una purga entre ambos. El resultado se compara con DOS bases ingenuas:

  - «hoy»:    mañana se repite el rango de hoy.
  - «media»:  mañana se repite el rango normal (la media de los últimos 20 días).

El estadístico z compara los errores de forma PAREADA día por día (promediando los activos de cada día, porque
se mueven juntos) y se corrige por la correlación entre días seguidos (la volatilidad se agrupa, así que los
errores de días vecinos se parecen). El modelo supera a la base solo si el z contra AMBAS es >= `Z_MINIMO`.
"""
import math
from dataclasses import dataclass, field
from datetime import date
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

from simultradia.analisis.volatilidad import (
    ARRANQUE, INDICE_NORMAL, NOMBRES_FEATURES, calcular_features, etiquetar, rangos)
from simultradia.core.exceptions import ErrorOperacionInvalida
from simultradia.domain.entities.vela_entity import Vela
from simultradia.domain.enums import NivelVolatilidad
from simultradia.domain.reglas.volatilidad import (
    FRACCION_ENTRENAMIENTO_INICIAL, HORIZONTE, TRAMOS_VALIDACION, VENTANA_NIVEL, Z_MINIMO,
    nivel_de, umbrales_de, velas_de_purga)

MIN_FILAS_ACTIVO = 30                # un activo solo se compara si tiene al menos estas filas de prueba
_ETIQUETAS_CALIBRACION = ("Muy tranquilo", "Tranquilo", "Normal", "Agitado", "Muy agitado")


@dataclass
class Dataset:
    X: np.ndarray                    # (filas, features)
    y: np.ndarray                    # ln(rango siguiente) - ln(rango normal)
    dias: np.ndarray                 # día de cada fila (date.toordinal)
    id_activo: np.ndarray
    ln_normal: np.ndarray            # ln(rango normal) de cada fila
    ln_hoy: np.ndarray               # ln(rango de la vela de la fila)
    umbral_bajo: np.ndarray          # percentil 25 de los últimos 90 rangos
    umbral_alto: np.ndarray          # percentil 75
    horizonte: int = HORIZONTE


@dataclass
class Tramo:
    inicio: int                      # ordinal del primer día de prueba
    fin: int
    n_prueba: int
    error: float                     # error medio absoluto en logaritmo, del modelo
    error_hoy: float
    error_media: float


@dataclass
class BinCalibracion:
    etiqueta: str
    n: int
    predicho: float                  # veces lo normal que esperaba el modelo, en promedio
    real: float                      # veces lo normal que fue de verdad, en promedio


@dataclass
class ActivoEval:
    id_activo: int
    n: int
    error: float
    error_hoy: float
    error_media: float


@dataclass
class Evaluacion:
    horizonte: int
    n_filas: int
    n_prueba: int
    dias_prueba: int
    error: float                     # error medio absoluto (logaritmo) del modelo en la prueba
    error_hoy: float
    error_media: float
    z_hoy: float
    z_media: float
    correlacion: Optional[float]
    sigma: float                     # desviación del error (logaritmo): da el intervalo del 80 %
    acierto_nivel: float
    acierto_nivel_hoy: float
    tramos: List[Tramo] = field(default_factory=list)
    calibracion: List[BinCalibracion] = field(default_factory=list)
    importancias: Dict[str, float] = field(default_factory=dict)
    activos: List[ActivoEval] = field(default_factory=list)

    @property
    def z(self) -> float:
        return min(self.z_hoy, self.z_media)

    @property
    def supera_base(self) -> bool:
        return self.z >= Z_MINIMO

    @property
    def mejora_hoy(self) -> float:
        """Cuánto menos se equivoca que repetir el rango de hoy (0,12 = 12 % menos de error)."""
        return 1.0 - self.error / self.error_hoy if self.error_hoy else 0.0

    @property
    def mejora_media(self) -> float:
        return 1.0 - self.error / self.error_media if self.error_media else 0.0

    @property
    def error_porcentual(self) -> float:
        """El error típico expresado como «se equivoca ±x % del rango»: exp(error) - 1."""
        return math.exp(self.error) - 1.0

    @property
    def veredicto(self) -> str:
        if self.supera_base:
            return "Supera a las bases"
        if self.z_hoy >= Z_MINIMO or self.z_media >= Z_MINIMO:
            return "Supera a una base, no a las dos"
        return "No supera a las bases"

    @property
    def activos_mejores(self) -> Tuple[int, int]:
        """(activos donde el modelo se equivoca menos que las DOS bases, activos comparables)."""
        return (sum(1 for a in self.activos if a.error < a.error_hoy and a.error < a.error_media),
                len(self.activos))


@dataclass
class ResultadoEntrenamiento:
    modelo: object
    evaluacion: Evaluacion


# ---------------------------------------------------------------------------- datos
def armar_dataset(velas_por_activo: Dict[int, Sequence[Vela]], horizonte: int = HORIZONTE) -> Dataset:
    """Junta las filas con features y objetivo de todos los activos (velas diarias CERRADAS, de la más vieja a la más nueva)."""
    X: List[List[float]] = []
    y: List[float] = []
    dias: List[int] = []
    ids: List[int] = []
    ln_normal: List[float] = []
    ln_hoy: List[float] = []
    bajos: List[float] = []
    altos: List[float] = []
    for id_activo, velas in velas_por_activo.items():
        filas = calcular_features(velas)
        objetivos = etiquetar(velas, horizonte)
        r = rangos(velas)
        for i, (vela, fila, objetivo) in enumerate(zip(velas, filas, objetivos)):
            if fila is None or objetivo is None:
                continue
            umbrales = umbrales_de(r[max(0, i - VENTANA_NIVEL + 1):i + 1])
            if umbrales is None:
                continue
            X.append(fila)
            y.append(objetivo)
            dias.append(vela.momento.date().toordinal())
            ids.append(id_activo)
            ln_normal.append(fila[INDICE_NORMAL])
            ln_hoy.append(fila[0])
            bajos.append(umbrales[0])
            altos.append(umbrales[1])
    if not X:
        raise ErrorOperacionInvalida("No hay velas diarias suficientes para entrenar (hacen falta más de %d por activo)."
                                     % ARRANQUE)
    orden = np.argsort(np.array(dias), kind="stable")
    return Dataset(np.array(X, dtype=float)[orden], np.array(y, dtype=float)[orden],
                   np.array(dias, dtype=int)[orden], np.array(ids, dtype=int)[orden],
                   np.array(ln_normal, dtype=float)[orden], np.array(ln_hoy, dtype=float)[orden],
                   np.array(bajos, dtype=float)[orden], np.array(altos, dtype=float)[orden], horizonte)


def tramos_walk_forward(dias: Sequence[int], tramos: int = TRAMOS_VALIDACION,
                        fraccion: float = FRACCION_ENTRENAMIENTO_INICIAL) -> List[Tuple[int, int]]:
    """Bloques de prueba consecutivos (inicio, fin) en ordinales de día, repartidos por días distintos."""
    unicos = sorted(set(int(d) for d in dias))
    n = len(unicos)
    primero = int(n * fraccion)
    tamano = (n - primero) // tramos
    if tamano < 1:
        raise ErrorOperacionInvalida("Hay muy pocos días de historia para validar el modelo.")
    bloques = []
    for k in range(tramos):
        desde = primero + k * tamano
        hasta = n - 1 if k == tramos - 1 else desde + tamano - 1
        bloques.append((unicos[desde], unicos[hasta]))
    return bloques


# ---------------------------------------------------------------------------- modelo
def crear_modelo_lightgbm():
    """El modelo real. Se importa aquí para que el resto de la app funcione sin LightGBM."""
    try:
        from lightgbm import LGBMRegressor
    except ImportError:
        raise ErrorOperacionInvalida("Falta la librería lightgbm. Ejecuta:  pip install -e .") from None
    return LGBMRegressor(
        objective="regression", n_estimators=300, learning_rate=0.03, num_leaves=15,
        min_child_samples=100, subsample=0.8, subsample_freq=1, colsample_bytree=0.8,
        reg_lambda=5.0, importance_type="gain", random_state=0, verbose=-1)


def crear_modelo_random_forest():
    """El algoritmo contra el que se compara LightGBM (solo para comparar, no para predecir)."""
    try:
        from sklearn.ensemble import RandomForestRegressor
    except ImportError:
        raise ErrorOperacionInvalida("Falta la librería scikit-learn. Ejecuta:  pip install -e .") from None
    return RandomForestRegressor(n_estimators=200, min_samples_leaf=50, n_jobs=-1, random_state=0)


def predecir(modelo, fila: Sequence[float]) -> float:
    """El rango esperado de mañana (fracción del precio) a partir de una fila de features."""
    razon = float(modelo.predict(np.array([fila], dtype=float))[0])
    return math.exp(razon + fila[INDICE_NORMAL])


def explicar(modelo, fila: Sequence[float], maximo: int = 5) -> List[Tuple[str, float]]:
    """Los factores que más empujaron la predicción: [(feature, aporte)], de mayor a menor valor absoluto.
    Positivo empuja a esperar MÁS volatilidad. Vacío si el modelo no lo permite."""
    booster = getattr(modelo, "booster_", None)
    if booster is None:
        return []
    contribuciones = np.asarray(booster.predict(np.array([fila], dtype=float), pred_contrib=True))[0]
    propias = contribuciones[:len(NOMBRES_FEATURES)]               # el último valor es el sesgo
    pares = sorted(zip(NOMBRES_FEATURES, (float(x) for x in propias)), key=lambda p: -abs(p[1]))
    return pares[:maximo]


# ---------------------------------------------------------------------------- evaluación
def estadistico_z(diferencias_por_dia: Sequence[float]) -> float:
    """z de que la diferencia media de errores (base - modelo) sea mayor que cero. `diferencias_por_dia` trae un
    valor por día de prueba (el promedio de los activos de ese día). La varianza se infla por la correlación
    entre días seguidos (AR(1)): errores vecinos de volatilidad se parecen y contarían de más."""
    d = np.asarray(diferencias_por_dia, dtype=float)
    n = len(d)
    if n < 10:
        return 0.0
    desv = float(d.std(ddof=1))
    if desv <= 1e-12:
        return 0.0
    rho = 0.0
    if d[:-1].std() > 0 and d[1:].std() > 0:
        rho = float(np.corrcoef(d[:-1], d[1:])[0, 1])
    rho = min(max(rho, 0.0), 0.95)
    error_estandar = desv / math.sqrt(n) * math.sqrt((1.0 + rho) / (1.0 - rho))
    return float(d.mean() / error_estandar)


def _diferencias_por_dia(dias: np.ndarray, error_base: np.ndarray, error_modelo: np.ndarray) -> np.ndarray:
    """Promedio, por día, de |error de la base| - |error del modelo| (positivo = el modelo se equivoca menos)."""
    diferencia = np.abs(error_base) - np.abs(error_modelo)
    unicos, indice = np.unique(dias, return_inverse=True)
    suma = np.bincount(indice, weights=diferencia)
    cuenta = np.bincount(indice)
    return suma / cuenta


def _calibracion(prediccion_log: np.ndarray, real_log: np.ndarray) -> List[BinCalibracion]:
    """Cinco grupos de igual tamaño según lo que esperaba el modelo, de menos a más agitado."""
    bordes = np.quantile(prediccion_log, [0.2, 0.4, 0.6, 0.8])
    grupo = np.searchsorted(bordes, prediccion_log, side="right")
    salida = []
    for k, etiqueta in enumerate(_ETIQUETAS_CALIBRACION):
        dentro = grupo == k
        n = int(dentro.sum())
        salida.append(BinCalibracion(etiqueta, n,
                                     float(np.exp(prediccion_log[dentro]).mean()) if n else 0.0,
                                     float(np.exp(real_log[dentro]).mean()) if n else 0.0))
    return salida


def _niveles(rango_log: np.ndarray, bajo: np.ndarray, alto: np.ndarray) -> np.ndarray:
    """0 baja, 1 normal, 2 alta, según los umbrales del activo en ese día."""
    rango = np.exp(rango_log)
    return np.where(rango <= bajo, 0, np.where(rango >= alto, 2, 1))


def evaluar(dataset: Dataset, crear_modelo: Callable[[], object]) -> Evaluacion:
    """Validación walk-forward. No devuelve ningún modelo: solo qué tan bien habría predicho."""
    purga = velas_de_purga(dataset.horizonte)
    partes: Dict[str, List[np.ndarray]] = {k: [] for k in (
        "dias", "ids", "y", "y_hat", "ln_normal", "ln_hoy", "bajo", "alto")}
    tramos: List[Tramo] = []

    for inicio, fin in tramos_walk_forward(dataset.dias):
        entrena = dataset.dias < inicio - purga
        prueba = (dataset.dias >= inicio) & (dataset.dias <= fin)
        if not entrena.any() or not prueba.any():
            continue
        modelo = crear_modelo()
        modelo.fit(dataset.X[entrena], dataset.y[entrena])
        y_hat = np.asarray(modelo.predict(dataset.X[prueba]), dtype=float)
        y = dataset.y[prueba]
        hoy = dataset.ln_hoy[prueba] - dataset.ln_normal[prueba]      # base «hoy», como razón sobre lo normal
        tramos.append(Tramo(inicio, fin, int(prueba.sum()), float(np.abs(y_hat - y).mean()),
                            float(np.abs(hoy - y).mean()), float(np.abs(y).mean())))
        for clave, valor in (("dias", dataset.dias[prueba]), ("ids", dataset.id_activo[prueba]), ("y", y),
                             ("y_hat", y_hat), ("ln_normal", dataset.ln_normal[prueba]),
                             ("ln_hoy", dataset.ln_hoy[prueba]), ("bajo", dataset.umbral_bajo[prueba]),
                             ("alto", dataset.umbral_alto[prueba])):
            partes[clave].append(valor)

    if not partes["y"]:
        raise ErrorOperacionInvalida("No se pudo armar ningún tramo de validación.")
    t = {k: np.concatenate(v) for k, v in partes.items()}
    y, y_hat = t["y"], t["y_hat"]
    e_modelo = y_hat - y
    e_hoy = (t["ln_hoy"] - t["ln_normal"]) - y          # ln(rango de hoy / rango real)
    e_media = -y                                        # ln(rango normal / rango real)

    z_hoy = estadistico_z(_diferencias_por_dia(t["dias"], e_hoy, e_modelo))
    z_media = estadistico_z(_diferencias_por_dia(t["dias"], e_media, e_modelo))
    correlacion: Optional[float] = None
    if y.std() > 0 and y_hat.std() > 0:
        correlacion = float(np.corrcoef(y, y_hat)[0, 1])

    real_nivel = _niveles(y + t["ln_normal"], t["bajo"], t["alto"])
    nivel_modelo = _niveles(y_hat + t["ln_normal"], t["bajo"], t["alto"])
    nivel_hoy = _niveles(t["ln_hoy"], t["bajo"], t["alto"])

    por_activo = []
    for id_activo in sorted(set(int(i) for i in t["ids"])):
        m = t["ids"] == id_activo
        if m.sum() >= MIN_FILAS_ACTIVO:
            por_activo.append(ActivoEval(id_activo, int(m.sum()), float(np.abs(e_modelo[m]).mean()),
                                         float(np.abs(e_hoy[m]).mean()), float(np.abs(e_media[m]).mean())))

    return Evaluacion(
        horizonte=dataset.horizonte, n_filas=len(dataset.y), n_prueba=len(y),
        dias_prueba=int(len(np.unique(t["dias"]))), error=float(np.abs(e_modelo).mean()),
        error_hoy=float(np.abs(e_hoy).mean()), error_media=float(np.abs(e_media).mean()),
        z_hoy=z_hoy, z_media=z_media, correlacion=correlacion, sigma=float(e_modelo.std()),
        acierto_nivel=float((nivel_modelo == real_nivel).mean()),
        acierto_nivel_hoy=float((nivel_hoy == real_nivel).mean()),
        tramos=tramos, calibracion=_calibracion(y_hat, y), activos=por_activo)


def entrenar(dataset: Dataset, crear_modelo: Callable[[], object]) -> ResultadoEntrenamiento:
    """Evalúa con walk-forward y deja entrenado el modelo final con TODA la historia."""
    evaluacion = evaluar(dataset, crear_modelo)
    modelo = crear_modelo()
    modelo.fit(dataset.X, dataset.y)
    importancias = getattr(modelo, "feature_importances_", None)
    if importancias is not None:
        total = float(np.sum(importancias)) or 1.0
        evaluacion.importancias = {nombre: float(v) / total for nombre, v in zip(NOMBRES_FEATURES, importancias)}
    return ResultadoEntrenamiento(modelo, evaluacion)
