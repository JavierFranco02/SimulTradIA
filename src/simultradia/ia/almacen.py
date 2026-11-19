"""Guarda y lee los archivos de los modelos entrenados (carpeta `modelos/` del proyecto).

En la base solo queda la ruta RELATIVA (`modelos_ia.ruta_artefacto`). Los archivos son pickle: solo se
leen los que escribió la propia aplicación en esta carpeta, nunca archivos de otro origen.
"""
import pickle
from pathlib import Path


class AlmacenModelos:
    def __init__(self, raiz: Path):
        self._raiz = Path(raiz)

    def guardar(self, modelo, id_modelo: int) -> str:
        carpeta = self._raiz / "modelos"
        carpeta.mkdir(exist_ok=True)
        ruta = "modelos/modelo_%d.pkl" % id_modelo
        with open(str(self._raiz / ruta), "wb") as archivo:
            pickle.dump(modelo, archivo)
        return ruta

    def cargar(self, ruta: str):
        with open(str(self._raiz / ruta), "rb") as archivo:
            return pickle.load(archivo)
