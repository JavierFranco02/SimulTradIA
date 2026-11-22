"""Convierte la `Evaluacion` de volatilidad en un diccionario simple (columna JSON de modelos_ia) y de vuelta."""
from typing import Dict

from simultradia.ia.volatilidad import ActivoEval, BinCalibracion, Evaluacion, Tramo


def a_dict(ev: Evaluacion) -> Dict:
    return {
        "horizonte": ev.horizonte, "n_filas": ev.n_filas, "n_prueba": ev.n_prueba, "dias_prueba": ev.dias_prueba,
        "error": ev.error, "error_hoy": ev.error_hoy, "error_media": ev.error_media,
        "z_hoy": ev.z_hoy, "z_media": ev.z_media, "correlacion": ev.correlacion, "sigma": ev.sigma,
        "acierto_nivel": ev.acierto_nivel, "acierto_nivel_hoy": ev.acierto_nivel_hoy,
        "tramos": [vars(t).copy() for t in ev.tramos],
        "calibracion": [vars(b).copy() for b in ev.calibracion],
        "importancias": ev.importancias,
        "activos": [vars(a).copy() for a in ev.activos],
    }


def desde_dict(d: Dict) -> Evaluacion:
    return Evaluacion(
        horizonte=d["horizonte"], n_filas=d["n_filas"], n_prueba=d["n_prueba"], dias_prueba=d["dias_prueba"],
        error=d["error"], error_hoy=d["error_hoy"], error_media=d["error_media"],
        z_hoy=d["z_hoy"], z_media=d["z_media"], correlacion=d.get("correlacion"), sigma=d["sigma"],
        acierto_nivel=d["acierto_nivel"], acierto_nivel_hoy=d["acierto_nivel_hoy"],
        tramos=[Tramo(**t) for t in d.get("tramos", [])],
        calibracion=[BinCalibracion(**b) for b in d.get("calibracion", [])],
        importancias=d.get("importancias", {}),
        activos=[ActivoEval(**a) for a in d.get("activos", [])])
