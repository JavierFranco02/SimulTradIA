"""Entrenamiento y evaluación del modelo de dirección. Sin BD ni interfaz.

La validación es walk-forward: se entrena con el pasado y se prueba en un bloque posterior,
dejando una purga entre ambos para que ninguna etiqueta del entrenamiento mire dentro de la
prueba. El resultado se compara con una base (siempre la clase más frecuente del
entrenamiento) y se mide con un estadístico z conservador: dos activos el mismo día se mueven
juntos, así que los días de prueba cuentan una vez cada `horizonte`, no una por fila.
"""
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

from simultradia.analisis.features import NOMBRES_FEATURES, calcular_features, etiquetar
from simultradia.core.exceptions import ErrorOperacionInvalida
from simultradia.domain.entities.vela_entity import Vela
from simultradia.domain.reglas.prediccion import (
    ALCISTA, BAJISTA, FRACCION_ENTRENAMIENTO_INICIAL, LATERAL, TRAMOS_VALIDACION, Z_MINIMO,
    dias_de_purga)

# Un activo solo se compara contra su base si tiene al menos estas filas de prueba.
MIN_FILAS_ACTIVO = 30
# Rangos de confianza (probabilidad de la clase elegida) de la tabla de calibración.
_BORDES_CONFIANZA = (0.0, 0.4, 0.5, 0.6, 0.7, 1.0001)


@dataclass
class Dataset:
    X: np.ndarray            # (filas, features)
    y: np.ndarray            # clase real 0, 1, 2
    dias: np.ndarray         # día de cada fila (date.toordinal)
    id_activo: np.ndarray
    horizonte: int


@dataclass
class Tramo:
    inicio: int              # ordinal del primer día de prueba
    fin: int
    n_prueba: int
    acierto: float
    base: float


@dataclass
class BinCalibracion:
    etiqueta: str
    n: int
    acierto: float
    confianza: float


@dataclass
class ActivoEval:
    id_activo: int
    n: int
    acierto: float
    base: float


@dataclass
class Evaluacion:
    horizonte: int
    n_filas: int
    n_prueba: int
    dias_efectivos: float
    acierto: float
    base: float
    z: float
    auc: Optional[float]
    tramos: List[Tramo] = field(default_factory=list)
    calibracion: List[BinCalibracion] = field(default_factory=list)
    confusion: List[List[int]] = field(default_factory=list)       # [real][predicho]
    importancias: Dict[str, float] = field(default_factory=dict)   # suman 1
    activos: List[ActivoEval] = field(default_factory=list)

    @property
    def ventaja(self) -> float:
        """Puntos porcentuales por encima (o debajo) de la base."""
        return (self.acierto - self.base) * 100.0

    @property
    def supera_base(self) -> bool:
        return self.z >= Z_MINIMO

    @property
    def veredicto(self) -> str:
        return "Supera la base" if self.supera_base else "No se distingue del azar"

    @property
    def activos_mejores(self) -> Tuple[int, int]:
        """(activos que superan su base, activos comparables)."""
        return sum(1 for a in self.activos if a.acierto > a.base), len(self.activos)


@dataclass
class ResultadoEntrenamiento:
    modelo: object
    evaluacion: Evaluacion


# ---------------------------------------------------------------------------- datos
def armar_dataset(velas_por_activo: Dict[int, Sequence[Vela]], horizonte: int) -> Dataset:
    """Junta las filas con features y etiqueta de todos los activos (velas diarias CERRADAS,
    de la más vieja a la más nueva)."""
    X: List[List[float]] = []
    y: List[int] = []
    dias: List[int] = []
    ids: List[int] = []
    for id_activo, velas in velas_por_activo.items():
        filas = calcular_features(velas)
        clases = etiquetar([float(v.cierre) for v in velas], horizonte)
        for vela, fila, clase in zip(velas, filas, clases):
            if fila is None or clase is None:
                continue
            X.append(fila)
            y.append(clase)
            dias.append(vela.momento.date().toordinal())
            ids.append(id_activo)
    if not X:
        raise ErrorOperacionInvalida("No hay velas diarias suficientes para entrenar.")
    orden = np.argsort(np.array(dias), kind="stable")
    return Dataset(np.array(X, dtype=float)[orden], np.array(y, dtype=int)[orden],
                   np.array(dias, dtype=int)[orden], np.array(ids, dtype=int)[orden], horizonte)


def tramos_walk_forward(dias: Sequence[int], tramos: int = TRAMOS_VALIDACION,
                        fraccion: float = FRACCION_ENTRENAMIENTO_INICIAL) -> List[Tuple[int, int]]:
    """Bloques de prueba consecutivos (inicio, fin) en ordinales de día. Se reparten por días
    distintos, no por filas, para que cada bloque abarque el mismo tiempo."""
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
        from lightgbm import LGBMClassifier
    except ImportError:
        raise ErrorOperacionInvalida(
            "Falta la librería lightgbm. Ejecuta:  pip install -e .") from None
    return LGBMClassifier(
        objective="multiclass", n_estimators=300, learning_rate=0.03, num_leaves=15,
        min_child_samples=100, subsample=0.8, subsample_freq=1, colsample_bytree=0.8,
        reg_lambda=5.0, importance_type="gain", random_state=0, verbose=-1)


def crear_modelo_random_forest():
    """El algoritmo contra el que se compara LightGBM (solo para comparar, no para predecir)."""
    try:
        from sklearn.ensemble import RandomForestClassifier
    except ImportError:
        raise ErrorOperacionInvalida(
            "Falta la librería scikit-learn. Ejecuta:  pip install -e .") from None
    return RandomForestClassifier(n_estimators=200, min_samples_leaf=50, n_jobs=-1, random_state=0)


def _proba(modelo, X: np.ndarray) -> np.ndarray:
    """Probabilidades en columnas fijas (bajista, lateral, alcista), aunque el modelo haya
    visto menos de tres clases."""
    cruda = np.asarray(modelo.predict_proba(X))
    salida = np.zeros((len(X), 3))
    for columna, clase in enumerate(modelo.classes_):
        salida[:, int(clase)] = cruda[:, columna]
    return salida


def predecir(modelo, fila: Sequence[float]) -> Tuple[float, float, float]:
    """(alcista, lateral, bajista) de una fila de features. Suman 1."""
    p = _proba(modelo, np.array([fila], dtype=float))[0]
    return float(p[ALCISTA]), float(p[LATERAL]), float(p[BAJISTA])


def explicar(modelo, fila: Sequence[float], clase: int, maximo: int = 5) -> List[Tuple[str, float]]:
    """Los factores que más empujaron hacia `clase`: [(feature, aporte)], de mayor a menor
    valor absoluto. Positivo empuja a favor de esa clase. Vacío si el modelo no lo permite."""
    booster = getattr(modelo, "booster_", None)
    if booster is None:
        return []
    n = len(NOMBRES_FEATURES)
    columnas = list(modelo.classes_)
    if clase not in columnas:
        return []
    k = columnas.index(clase)
    contribuciones = np.asarray(booster.predict(np.array([fila], dtype=float), pred_contrib=True))[0]
    propias = contribuciones[k * (n + 1):k * (n + 1) + n]        # el último de cada clase es el sesgo
    pares = sorted(zip(NOMBRES_FEATURES, (float(x) for x in propias)), key=lambda p: -abs(p[1]))
    return pares[:maximo]


# ---------------------------------------------------------------------------- evaluación
def estadistico_z(acierto: float, base: float, n_efectivo: float) -> float:
    """Cuántos errores estándar separan el acierto de la base."""
    if n_efectivo <= 0 or base <= 0.0 or base >= 1.0:
        return 0.0
    return (acierto - base) / (base * (1.0 - base) / n_efectivo) ** 0.5


def _mayoritaria(y: np.ndarray) -> int:
    return int(np.argmax(np.bincount(y, minlength=3)))


def _calibracion(confianza: np.ndarray, acierto: np.ndarray) -> List[BinCalibracion]:
    bins = []
    for desde, hasta in zip(_BORDES_CONFIANZA[:-1], _BORDES_CONFIANZA[1:]):
        dentro = (confianza >= desde) & (confianza < hasta)
        if hasta > 1.0:
            etiqueta = "≥ %.1f" % desde
        elif desde == 0.0:
            etiqueta = "< %.1f" % hasta
        else:
            etiqueta = "%.1f – %.1f" % (desde, hasta)
        n = int(dentro.sum())
        bins.append(BinCalibracion(
            etiqueta, n, float(acierto[dentro].mean()) if n else 0.0,
            float(confianza[dentro].mean()) if n else 0.0))
    return bins


def evaluar(dataset: Dataset, crear_modelo: Callable[[], object]) -> Evaluacion:
    """Validación walk-forward. No devuelve ningún modelo: solo qué tan bien habría acertado."""
    h = dataset.horizonte
    purga = dias_de_purga(h)
    reales: List[np.ndarray] = []
    predichas: List[np.ndarray] = []
    probas: List[np.ndarray] = []
    activos: List[np.ndarray] = []
    bases_pred: List[np.ndarray] = []
    tramos: List[Tramo] = []
    dias_prueba = set()

    for inicio, fin in tramos_walk_forward(dataset.dias):
        entrena = dataset.dias < inicio - purga
        prueba = (dataset.dias >= inicio) & (dataset.dias <= fin)
        if not entrena.any() or not prueba.any():
            continue
        modelo = crear_modelo()
        modelo.fit(dataset.X[entrena], dataset.y[entrena])
        p = _proba(modelo, dataset.X[prueba])
        pred = p.argmax(axis=1)
        y = dataset.y[prueba]
        mayor = _mayoritaria(dataset.y[entrena])
        tramos.append(Tramo(inicio, fin, int(prueba.sum()), float((pred == y).mean()),
                            float((y == mayor).mean())))
        reales.append(y)
        predichas.append(pred)
        probas.append(p)
        activos.append(dataset.id_activo[prueba])
        bases_pred.append(np.full(len(y), mayor))
        dias_prueba.update(int(d) for d in dataset.dias[prueba])

    if not reales:
        raise ErrorOperacionInvalida("No se pudo armar ningún tramo de validación.")
    y = np.concatenate(reales)
    pred = np.concatenate(predichas)
    p = np.vstack(probas)
    ids = np.concatenate(activos)
    mayor = np.concatenate(bases_pred)

    acierto = float((pred == y).mean())
    base = float((mayor == y).mean())
    n_efectivo = len(dias_prueba) / float(h)

    auc: Optional[float] = None
    try:
        from sklearn.metrics import roc_auc_score
        auc = float(roc_auc_score(y, p, multi_class="ovr", average="macro", labels=[0, 1, 2]))
    except Exception:           # falta una clase en la prueba, o sklearn no está
        auc = None

    confusion = [[0, 0, 0] for _ in range(3)]
    for real, elegida in zip(y, pred):
        confusion[int(real)][int(elegida)] += 1

    por_activo = []
    for id_activo in sorted(set(int(i) for i in ids)):
        mascara = ids == id_activo
        if mascara.sum() >= MIN_FILAS_ACTIVO:
            por_activo.append(ActivoEval(id_activo, int(mascara.sum()),
                                         float((pred[mascara] == y[mascara]).mean()),
                                         float((mayor[mascara] == y[mascara]).mean())))

    return Evaluacion(
        horizonte=h, n_filas=len(dataset.y), n_prueba=len(y), dias_efectivos=n_efectivo,
        acierto=acierto, base=base, z=estadistico_z(acierto, base, n_efectivo), auc=auc,
        tramos=tramos, calibracion=_calibracion(p.max(axis=1), (pred == y).astype(float)),
        confusion=confusion, activos=por_activo)


def entrenar(dataset: Dataset, crear_modelo: Callable[[], object]) -> ResultadoEntrenamiento:
    """Evalúa con walk-forward y deja entrenado el modelo final con TODA la historia."""
    evaluacion = evaluar(dataset, crear_modelo)
    modelo = crear_modelo()
    modelo.fit(dataset.X, dataset.y)
    importancias = getattr(modelo, "feature_importances_", None)
    if importancias is not None:
        total = float(np.sum(importancias)) or 1.0
        evaluacion.importancias = {nombre: float(v) / total
                                   for nombre, v in zip(NOMBRES_FEATURES, importancias)}
    return ResultadoEntrenamiento(modelo, evaluacion)
