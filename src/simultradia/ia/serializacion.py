"""Convierte la `Evaluacion` en un diccionario simple (para la columna JSON de modelos_ia) y de vuelta."""
from typing import Dict

from simultradia.ia.entrenamiento import (
    ActivoEval, BinCalibracion, Evaluacion, Tramo)


def a_dict(ev: Evaluacion) -> Dict:
    return {
        "horizonte": ev.horizonte, "n_filas": ev.n_filas, "n_prueba": ev.n_prueba,
        "dias_efectivos": ev.dias_efectivos, "acierto": ev.acierto, "base": ev.base,
        "z": ev.z, "auc": ev.auc,
        "tramos": [vars(t).copy() for t in ev.tramos],
        "calibracion": [vars(b).copy() for b in ev.calibracion],
        "confusion": ev.confusion,
        "importancias": ev.importancias,
        "activos": [vars(a).copy() for a in ev.activos],
    }


def desde_dict(d: Dict) -> Evaluacion:
    return Evaluacion(
        horizonte=d["horizonte"], n_filas=d["n_filas"], n_prueba=d["n_prueba"],
        dias_efectivos=d["dias_efectivos"], acierto=d["acierto"], base=d["base"],
        z=d["z"], auc=d.get("auc"),
        tramos=[Tramo(**t) for t in d.get("tramos", [])],
        calibracion=[BinCalibracion(**b) for b in d.get("calibracion", [])],
        confusion=d.get("confusion", []), importancias=d.get("importancias", {}),
        activos=[ActivoEval(**a) for a in d.get("activos", [])])
