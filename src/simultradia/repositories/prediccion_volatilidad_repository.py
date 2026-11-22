"""Acceso a "predicciones_volatilidad". Aquí vive el SQL de las predicciones de volatilidad."""
import json
from datetime import datetime, timedelta
from typing import List, Optional, Set

from simultradia.domain.entities.prediccion_volatilidad_entity import (
    EstadoCiclo, PrecisionVivo, PrediccionVolatilidad, SenalVolatilidad)
from simultradia.domain.enums import NivelVolatilidad

_COLUMNAS = ("p.id_prediccion, p.id_activo, p.id_modelo, p.generada_en, p.fecha_objetivo, p.precio_referencia, "
             "p.rango_predicho, p.rango_bajo, p.rango_alto, p.rango_hoy, p.rango_normal, p.umbral_bajo, "
             "p.umbral_alto, p.nivel, p.factores, p.rango_real, p.nivel_real, p.acierto_nivel, p.evaluada_en")


class PrediccionVolatilidadRepository:
    def insertar(self, conn, p: PrediccionVolatilidad) -> int:
        factores = [{"factor": n, "aporte": a, "valor": v} for n, a, v in p.factores]
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO predicciones_volatilidad
                       (id_activo, id_modelo, generada_en, fecha_objetivo, precio_referencia, rango_predicho,
                        rango_bajo, rango_alto, rango_hoy, rango_normal, umbral_bajo, umbral_alto, nivel, factores)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::json)
                   RETURNING id_prediccion""",
                (p.id_activo, p.id_modelo, p.generada_en, p.fecha_objetivo, p.precio_referencia, p.rango_predicho,
                 p.rango_bajo, p.rango_alto, p.rango_hoy, p.rango_normal, p.umbral_bajo, p.umbral_alto,
                 p.nivel.value, json.dumps(factores)))
            p.id_prediccion = cur.fetchone().id_prediccion
        return p.id_prediccion

    def activos_con_prediccion_de_hoy(self, conn, id_modelo: int, ahora: datetime) -> Set[int]:
        """Activos que ya tienen la predicción de HOY (día UTC) de este modelo."""
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id_activo FROM predicciones_volatilidad
                   WHERE id_modelo = %s AND (generada_en AT TIME ZONE 'UTC')::date = (%s AT TIME ZONE 'UTC')::date""",
                (id_modelo, ahora))
            return {f.id_activo for f in cur.fetchall()}

    def vencidas(self, conn, ahora: datetime) -> List[PrediccionVolatilidad]:
        with conn.cursor() as cur:
            cur.execute("SELECT " + _COLUMNAS + " FROM predicciones_volatilidad p "
                        "WHERE p.rango_real IS NULL AND p.fecha_objetivo <= %s ORDER BY p.generada_en", (ahora,))
            return [self._a_prediccion(f) for f in cur.fetchall()]

    def registrar_resultado(self, conn, id_prediccion: int, rango_real: float, nivel_real: NivelVolatilidad,
                            acierto_nivel: bool, evaluada_en: datetime) -> None:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE predicciones_volatilidad SET rango_real = %s, nivel_real = %s,
                          acierto_nivel = %s, evaluada_en = %s WHERE id_prediccion = %s""",
                (rango_real, nivel_real.value, acierto_nivel, evaluada_en, id_prediccion))

    def ultimas_por_activo(self, conn) -> List[SenalVolatilidad]:
        """La predicción más reciente de cada activo habilitado, hecha por el modelo ACTIVO."""
        with conn.cursor() as cur:
            cur.execute(
                """SELECT DISTINCT ON (p.id_activo) """ + _COLUMNAS + """, a.ticker, a.nombre
                   FROM predicciones_volatilidad p
                   JOIN modelos_ia m ON m.id_modelo = p.id_modelo AND m.estado = 'activo'
                   JOIN activos a ON a.id_activo = p.id_activo AND a.activo
                   ORDER BY p.id_activo, p.generada_en DESC""")
            return [SenalVolatilidad(self._a_prediccion(f), f.ticker, f.nombre) for f in cur.fetchall()]

    def historial(self, conn, id_activo: int, limite: int) -> List[PrediccionVolatilidad]:
        with conn.cursor() as cur:
            cur.execute("SELECT " + _COLUMNAS + " FROM predicciones_volatilidad p "
                        "WHERE p.id_activo = %s ORDER BY p.generada_en DESC LIMIT %s", (id_activo, limite))
            return [self._a_prediccion(f) for f in cur.fetchall()]

    def precision(self, conn, ahora: datetime) -> PrecisionVivo:
        """Resultados REALES de las ya evaluadas, de los últimos 90 días de evaluación."""
        with conn.cursor() as cur:
            cur.execute(
                """SELECT COUNT(*) AS evaluadas,
                          COUNT(CASE WHEN acierto_nivel THEN 1 END) AS aciertos,
                          AVG(abs(ln(rango_predicho / rango_real))) AS error_modelo,
                          AVG(abs(ln(GREATEST(rango_hoy, 0.0001) / rango_real))) AS error_hoy,
                          COUNT(CASE WHEN rango_real BETWEEN rango_bajo AND rango_alto THEN 1 END) AS dentro
                   FROM predicciones_volatilidad
                   WHERE rango_real IS NOT NULL AND rango_real > 0 AND evaluada_en >= %s""",
                (ahora - timedelta(days=90),))
            f = cur.fetchone()
        return PrecisionVivo(
            f.evaluadas, f.aciertos,
            None if f.error_modelo is None else float(f.error_modelo),
            None if f.error_hoy is None else float(f.error_hoy), f.dentro)

    def estado_ciclo(self, conn, ahora: datetime) -> EstadoCiclo:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT MAX(generada_en) AS ultima,
                          COUNT(CASE WHEN rango_real IS NULL THEN 1 END) AS pendientes,
                          COUNT(CASE WHEN rango_real IS NOT NULL THEN 1 END) AS evaluadas,
                          COUNT(CASE WHEN (generada_en AT TIME ZONE 'UTC')::date = (%s AT TIME ZONE 'UTC')::date
                                     THEN 1 END) AS de_hoy
                   FROM predicciones_volatilidad""", (ahora,))
            f = cur.fetchone()
        return EstadoCiclo(f.ultima, f.de_hoy, f.pendientes, f.evaluadas)

    @staticmethod
    def _a_prediccion(f) -> PrediccionVolatilidad:
        crudo = f.factores
        lista = json.loads(crudo) if isinstance(crudo, str) else (crudo or [])
        return PrediccionVolatilidad(
            id_prediccion=f.id_prediccion, id_activo=f.id_activo, id_modelo=f.id_modelo,
            generada_en=f.generada_en, fecha_objetivo=f.fecha_objetivo, precio_referencia=f.precio_referencia,
            rango_predicho=float(f.rango_predicho), rango_bajo=float(f.rango_bajo), rango_alto=float(f.rango_alto),
            rango_hoy=float(f.rango_hoy), rango_normal=float(f.rango_normal),
            umbral_bajo=float(f.umbral_bajo), umbral_alto=float(f.umbral_alto),
            nivel=NivelVolatilidad(f.nivel),
            factores=[(d["factor"], float(d["aporte"]), None if d.get("valor") is None else float(d["valor"]))
                      for d in lista],
            rango_real=None if f.rango_real is None else float(f.rango_real),
            nivel_real=NivelVolatilidad(f.nivel_real) if f.nivel_real else None,
            acierto_nivel=f.acierto_nivel, evaluada_en=f.evaluada_en)
