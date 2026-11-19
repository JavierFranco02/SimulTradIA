"""Falsos y datos de prueba de la IA (sin PostgreSQL ni LightGBM): repositorios en memoria y series sintéticas."""
import math
import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sklearn.ensemble import HistGradientBoostingClassifier

from simultradia.domain.entities.vela_entity import Vela
from simultradia.domain.enums import EstadoModelo

AHORA = datetime(2026, 11, 18, 10, 0, tzinfo=timezone.utc)


def crear_modelo_prueba():
    return HistGradientBoostingClassifier(max_iter=60, learning_rate=0.1, random_state=0)


def velas_desde(cierres, ultimo_dia):
    """Velas diarias a las 00:00 UTC; la última empieza en `ultimo_dia`."""
    primero = ultimo_dia - timedelta(days=len(cierres) - 1)
    return [Vela(primero + timedelta(days=i), Decimal(str(c)), Decimal(str(c * 1.01)),
                 Decimal(str(c * 0.99)), Decimal(str(c)), Decimal(1000)) for i, c in enumerate(cierres)]


def serie_ciclica(n, semilla):
    azar = random.Random(semilla)
    fase = azar.random() * 6.28
    return [round(100.0 * math.exp(0.25 * math.sin(2 * math.pi * i / 30 + fase) + azar.gauss(0, 0.004)), 4)
            for i in range(n)]


def serie_aleatoria(n, semilla):
    azar = random.Random(semilla)
    precio, salida = 100.0, []
    for _ in range(n):
        precio *= math.exp(azar.gauss(0, 0.01))
        salida.append(round(precio, 4))
    return salida


class AlmacenFalso:
    def __init__(self):
        self.archivos = {}

    def guardar(self, modelo, id_modelo):
        ruta = "modelos/modelo_%d.pkl" % id_modelo
        self.archivos[ruta] = modelo
        return ruta

    def cargar(self, ruta):
        return self.archivos[ruta]


class ModeloRepoFalso:
    def __init__(self):
        self.modelos = []
        self.entrenamientos = {}      # id -> {"estado", "error"}

    def siguiente_version(self, conn, nombre):
        return "v%d" % (sum(1 for m in self.modelos if m.nombre == nombre) + 1)

    def insertar(self, conn, modelo):
        modelo.id_modelo = len(self.modelos) + 1
        self.modelos.append(modelo)
        return modelo

    def _por_id(self, id_modelo):
        return next((m for m in self.modelos if m.id_modelo == id_modelo), None)

    def completar(self, conn, id_modelo, estado, metricas, ruta_artefacto, entrenado_en):
        m = self._por_id(id_modelo)
        m.estado, m.metricas, m.ruta_artefacto, m.entrenado_en = estado, metricas, ruta_artefacto, entrenado_en

    def marcar_fallido(self, conn, id_modelo):
        self._por_id(id_modelo).estado = EstadoModelo.FALLIDO

    def activar(self, conn, id_modelo):
        nuevo = self._por_id(id_modelo)
        for m in self.modelos:
            if m.nombre == nuevo.nombre and m.estado == EstadoModelo.ACTIVO:
                m.estado = EstadoModelo.ARCHIVADO
        nuevo.estado = EstadoModelo.ACTIVO

    def buscar(self, conn, id_modelo):
        return self._por_id(id_modelo)

    def listar(self, conn, limite=100):
        return list(reversed(self.modelos))[:limite]

    def listar_activos(self, conn):
        return sorted((m for m in self.modelos if m.estado == EstadoModelo.ACTIVO),
                      key=lambda m: m.horizonte_dias)

    def abrir_entrenamiento(self, conn, id_modelo, id_usuario):
        self.entrenamientos[id_modelo] = {"estado": "ejecutando", "error": None}
        return id_modelo

    def cerrar_entrenamiento(self, conn, id_entrenamiento, estado, metricas, mensaje_error):
        self.entrenamientos[id_entrenamiento] = {"estado": estado.value, "error": mensaje_error}


class PrediccionRepoFalso:
    def __init__(self):
        self.predicciones = []
        self.factores_guardados = {}

    def insertar(self, conn, p):
        p.id_prediccion = len(self.predicciones) + 1
        self.predicciones.append(p)
        return p.id_prediccion

    def insertar_explicaciones(self, conn, id_prediccion, filas):
        self.factores_guardados[id_prediccion] = list(filas)

    def activos_con_prediccion_de_hoy(self, conn, id_modelo, ahora):
        return {p.id_activo for p in self.predicciones
                if p.id_modelo == id_modelo and p.generada_en.date() == ahora.date()}

    def vencidas(self, conn, ahora):
        return [p for p in self.predicciones if p.acierto is None and p.fecha_objetivo <= ahora]

    def registrar_resultado(self, conn, id_prediccion, precio_resultado, direccion_real, acierto, evaluada_en):
        p = self.predicciones[id_prediccion - 1]
        p.precio_resultado, p.direccion_real, p.acierto, p.evaluada_en = (
            precio_resultado, direccion_real, acierto, evaluada_en)

    # ---- lecturas (las usa la pantalla)
    def ultimas_por_activo(self, conn, horizonte):
        from simultradia.domain.entities.prediccion_entity import SenalActivo
        ultimas = {}
        for p in self.predicciones:
            if p.horizonte_dias == horizonte:
                ultimas[p.id_activo] = p            # la más nueva pisa a la anterior
        return [SenalActivo(p, "A%d" % p.id_activo, "Activo %d" % p.id_activo) for p in ultimas.values()]

    def explicaciones(self, conn, id_prediccion):
        return self.factores_guardados.get(id_prediccion, [])

    def historial(self, conn, id_activo, horizonte, limite):
        propias = [p for p in self.predicciones if p.id_activo == id_activo and p.horizonte_dias == horizonte]
        return list(reversed(propias))[:limite]

    def precision(self, conn, horizonte, ahora):
        from simultradia.domain.entities.prediccion_entity import PrecisionVivo
        hechas = [p for p in self.predicciones if p.horizonte_dias == horizonte and p.acierto is not None]
        aciertos = sum(1 for p in hechas if p.acierto)
        return PrecisionVivo(len(hechas), aciertos, len(hechas), aciertos)

    def estado_ciclo(self, conn, ahora):
        from simultradia.domain.entities.prediccion_entity import EstadoCiclo
        ultima = max((p.generada_en for p in self.predicciones), default=None)
        return EstadoCiclo(ultima, sum(1 for p in self.predicciones if p.generada_en.date() == ahora.date()),
                           sum(1 for p in self.predicciones if p.acierto is None),
                           sum(1 for p in self.predicciones if p.acierto is not None))
