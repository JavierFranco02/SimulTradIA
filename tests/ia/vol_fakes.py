"""Falsos y datos de prueba de la volatilidad (sin PostgreSQL ni LightGBM): repositorios en memoria y series sintéticas."""
import math
import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sklearn.ensemble import HistGradientBoostingRegressor

from simultradia.domain.entities.prediccion_volatilidad_entity import (
    EstadoCiclo, PrecisionVivo, SenalVolatilidad)
from simultradia.domain.entities.vela_entity import Vela
from simultradia.domain.enums import EstadoModelo, TipoModeloIA

AHORA = datetime(2026, 11, 18, 10, 0, tzinfo=timezone.utc)
AYER = AHORA.replace(hour=0, minute=0) - timedelta(days=1)


def crear_modelo_prueba():
    return HistGradientBoostingRegressor(max_iter=60, learning_rate=0.1, random_state=0)


def velas_vol(n, semilla, ultimo_dia=AYER, periodo=30.0):
    """Velas diarias a las 00:00 UTC con volatilidad que oscila y se puede anticipar (la última empieza en `ultimo_dia`)."""
    azar = random.Random(semilla)
    fase = azar.random() * 6.28
    precio, salida = 100.0, []
    primero = ultimo_dia - timedelta(days=n - 1)
    for i in range(n):
        vol = 0.012 * math.exp(0.8 * math.sin(2 * math.pi * i / periodo + fase))
        cierre = precio * math.exp(azar.gauss(0, vol))
        maximo = max(precio, cierre) * (1 + abs(azar.gauss(0, vol * 0.4)))
        minimo = min(precio, cierre) * (1 - abs(azar.gauss(0, vol * 0.4)))
        salida.append(Vela(primero + timedelta(days=i), Decimal(str(round(precio, 4))), Decimal(str(round(maximo, 4))),
                           Decimal(str(round(minimo, 4))), Decimal(str(round(cierre, 4))), Decimal(1000)))
        precio = cierre
    return salida


def velas_azar(n, semilla, ultimo_dia=AYER):
    """Rangos independientes entre días: no hay nada que predecir."""
    azar = random.Random(semilla)
    primero = ultimo_dia - timedelta(days=n - 1)
    salida = []
    for i in range(n):
        rango = 0.01 * math.exp(azar.gauss(0, 0.4))
        salida.append(Vela(primero + timedelta(days=i), Decimal(100), Decimal(str(round(100 * (1 + rango / 2), 4))),
                           Decimal(str(round(100 * (1 - rango / 2), 4))), Decimal(100), Decimal(1000)))
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

    def listar(self, conn, limite=100, tipo=None):
        return [m for m in reversed(self.modelos) if tipo is None or m.tipo == tipo][:limite]

    def listar_activos(self, conn, tipo=TipoModeloIA.DIRECCION):
        return [m for m in self.modelos if m.estado == EstadoModelo.ACTIVO and m.tipo == tipo]

    def abrir_entrenamiento(self, conn, id_modelo, id_usuario):
        self.entrenamientos[id_modelo] = {"estado": "ejecutando", "error": None}
        return id_modelo

    def cerrar_entrenamiento(self, conn, id_entrenamiento, estado, metricas, mensaje_error):
        self.entrenamientos[id_entrenamiento] = {"estado": estado.value, "error": mensaje_error}


class PrediccionRepoFalso:
    def __init__(self):
        self.predicciones = []

    def insertar(self, conn, p):
        p.id_prediccion = len(self.predicciones) + 1
        self.predicciones.append(p)
        return p.id_prediccion

    def objetivos_pendientes(self, conn, id_modelo):
        return {(p.id_activo, p.fecha_objetivo) for p in self.predicciones
                if p.id_modelo == id_modelo and p.rango_real is None}

    def vencidas(self, conn, ahora):
        return [p for p in self.predicciones if p.rango_real is None and p.fecha_objetivo <= ahora]

    def registrar_resultado(self, conn, id_prediccion, rango_real, nivel_real, acierto_nivel, evaluada_en):
        p = self.predicciones[id_prediccion - 1]
        p.rango_real, p.nivel_real, p.acierto_nivel, p.evaluada_en = rango_real, nivel_real, acierto_nivel, evaluada_en

    def ultimas_por_activo(self, conn):
        ultimas = {}
        for p in self.predicciones:
            ultimas[p.id_activo] = p            # la más nueva pisa a la anterior
        return [SenalVolatilidad(p, "A%d" % p.id_activo, "Activo %d" % p.id_activo) for p in ultimas.values()]

    def historial(self, conn, id_activo, limite):
        return list(reversed([p for p in self.predicciones if p.id_activo == id_activo]))[:limite]

    def precision(self, conn, ahora):
        hechas = [p for p in self.predicciones if p.rango_real is not None]
        return PrecisionVivo(len(hechas), sum(1 for p in hechas if p.acierto_nivel),
                             None, None, sum(1 for p in hechas if p.dentro_del_intervalo))

    def estado_ciclo(self, conn, ahora):
        ultima = max((p.generada_en for p in self.predicciones), default=None)
        return EstadoCiclo(ultima, sum(1 for p in self.predicciones if p.generada_en.date() == ahora.date()),
                           sum(1 for p in self.predicciones if p.rango_real is None),
                           sum(1 for p in self.predicciones if p.rango_real is not None))
