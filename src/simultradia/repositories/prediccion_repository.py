"""Acceso a "predicciones_direccion" y "explicaciones_prediccion". Aquí vive el SQL de las predicciones."""
from datetime import datetime, timedelta
from typing import List, Optional, Set, Tuple

from simultradia.domain.entities.prediccion_entity import EstadoCiclo, PrecisionVivo, Prediccion, SenalActivo
from simultradia.domain.enums import DireccionPrediccion

_COLUMNAS = ("p.id_prediccion, p.id_activo, p.id_modelo, p.generada_en, p.horizonte_dias, p.fecha_objetivo, "
             "p.direccion, p.prob_alcista, p.prob_bajista, p.prob_lateral, p.confianza, p.precio_referencia, "
             "p.precio_resultado, p.direccion_real, p.acierto, p.evaluada_en")


class PrediccionRepository:
    def insertar(self, conn, p: Prediccion) -> int:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO predicciones_direccion
                       (id_activo, id_modelo, generada_en, horizonte_dias, fecha_objetivo, direccion,
                        prob_alcista, prob_bajista, prob_lateral, confianza, precio_referencia)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING id_prediccion""",
                (p.id_activo, p.id_modelo, p.generada_en, p.horizonte_dias, p.fecha_objetivo,
                 p.direccion.value, p.prob_alcista, p.prob_bajista, p.prob_lateral, p.confianza,
                 p.precio_referencia))
            p.id_prediccion = cur.fetchone().id_prediccion
        return p.id_prediccion

    def insertar_explicaciones(self, conn, id_prediccion: int,
                               filas: List[Tuple[str, float, Optional[float]]]) -> None:
        with conn.cursor() as cur:
            for factor, importancia, valor in filas:
                cur.execute("INSERT INTO explicaciones_prediccion (id_prediccion, factor, importancia, valor_factor) "
                            "VALUES (%s, %s, %s, %s)", (id_prediccion, factor, importancia, valor))

    def activos_con_prediccion_de_hoy(self, conn, id_modelo: int, ahora: datetime) -> Set[int]:
        """Activos que ya tienen la predicción de HOY (día UTC) de este modelo."""
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id_activo FROM predicciones_direccion
                   WHERE id_modelo = %s AND (generada_en AT TIME ZONE 'UTC')::date = (%s AT TIME ZONE 'UTC')::date""",
                (id_modelo, ahora))
            return {f.id_activo for f in cur.fetchall()}

    def vencidas(self, conn, ahora: datetime) -> List[Prediccion]:
        with conn.cursor() as cur:
            cur.execute("SELECT " + _COLUMNAS + " FROM predicciones_direccion p "
                        "WHERE p.acierto IS NULL AND p.fecha_objetivo <= %s ORDER BY p.generada_en", (ahora,))
            return [self._a_prediccion(f) for f in cur.fetchall()]

    def registrar_resultado(self, conn, id_prediccion: int, precio_resultado, direccion_real: DireccionPrediccion,
                            acierto: bool, evaluada_en: datetime) -> None:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE predicciones_direccion SET precio_resultado = %s, direccion_real = %s,
                          acierto = %s, evaluada_en = %s WHERE id_prediccion = %s""",
                (precio_resultado, direccion_real.value, acierto, evaluada_en, id_prediccion))

    def ultimas_por_activo(self, conn, horizonte: int) -> List[SenalActivo]:
        """La predicción más reciente de cada activo habilitado, hecha por el modelo ACTIVO de ese horizonte."""
        with conn.cursor() as cur:
            cur.execute(
                """SELECT DISTINCT ON (p.id_activo) """ + _COLUMNAS + """, a.ticker, a.nombre
                   FROM predicciones_direccion p
                   JOIN modelos_ia m ON m.id_modelo = p.id_modelo AND m.estado = 'activo'
                   JOIN activos a ON a.id_activo = p.id_activo AND a.activo
                   WHERE p.horizonte_dias = %s
                   ORDER BY p.id_activo, p.generada_en DESC""", (horizonte,))
            return [SenalActivo(self._a_prediccion(f), f.ticker, f.nombre) for f in cur.fetchall()]

    def historial(self, conn, id_activo: int, horizonte: int, limite: int) -> List[Prediccion]:
        with conn.cursor() as cur:
            cur.execute("SELECT " + _COLUMNAS + " FROM predicciones_direccion p "
                        "WHERE p.id_activo = %s AND p.horizonte_dias = %s "
                        "ORDER BY p.generada_en DESC LIMIT %s", (id_activo, horizonte, limite))
            return [self._a_prediccion(f) for f in cur.fetchall()]

    def explicaciones(self, conn, id_prediccion: int) -> List[Tuple[str, float, Optional[float]]]:
        with conn.cursor() as cur:
            cur.execute("SELECT factor, importancia, valor_factor FROM explicaciones_prediccion "
                        "WHERE id_prediccion = %s ORDER BY abs(importancia) DESC", (id_prediccion,))
            return [(f.factor, float(f.importancia),
                     None if f.valor_factor is None else float(f.valor_factor)) for f in cur.fetchall()]

    def precision(self, conn, horizonte: int, ahora: datetime) -> PrecisionVivo:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT COUNT(*) AS evaluadas,
                          COUNT(CASE WHEN acierto THEN 1 END) AS aciertos,
                          COUNT(CASE WHEN evaluada_en >= %s THEN 1 END) AS evaluadas_90d,
                          COUNT(CASE WHEN acierto AND evaluada_en >= %s THEN 1 END) AS aciertos_90d
                   FROM predicciones_direccion WHERE horizonte_dias = %s AND acierto IS NOT NULL""",
                (ahora - timedelta(days=90), ahora - timedelta(days=90), horizonte))
            f = cur.fetchone()
        return PrecisionVivo(f.evaluadas, f.aciertos, f.evaluadas_90d, f.aciertos_90d)

    def estado_ciclo(self, conn, ahora: datetime) -> EstadoCiclo:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT MAX(generada_en) AS ultima,
                          COUNT(CASE WHEN acierto IS NULL THEN 1 END) AS pendientes,
                          COUNT(CASE WHEN acierto IS NOT NULL THEN 1 END) AS evaluadas,
                          COUNT(CASE WHEN (generada_en AT TIME ZONE 'UTC')::date = (%s AT TIME ZONE 'UTC')::date
                                     THEN 1 END) AS de_hoy
                   FROM predicciones_direccion""", (ahora,))
            f = cur.fetchone()
        return EstadoCiclo(f.ultima, f.de_hoy, f.pendientes, f.evaluadas)

    @staticmethod
    def _a_prediccion(f) -> Prediccion:
        return Prediccion(
            id_prediccion=f.id_prediccion, id_activo=f.id_activo, id_modelo=f.id_modelo,
            horizonte_dias=f.horizonte_dias, generada_en=f.generada_en, fecha_objetivo=f.fecha_objetivo,
            direccion=DireccionPrediccion(f.direccion), prob_alcista=float(f.prob_alcista),
            prob_bajista=float(f.prob_bajista), prob_lateral=float(f.prob_lateral),
            confianza=float(f.confianza), precio_referencia=f.precio_referencia,
            precio_resultado=f.precio_resultado,
            direccion_real=DireccionPrediccion(f.direccion_real) if f.direccion_real else None,
            acierto=f.acierto, evaluada_en=f.evaluada_en)
