"""Acceso a "modelos_ia" y "entrenamientos_modelo". Aquí vive el SQL de los modelos de IA."""
import json
from datetime import datetime
from typing import Dict, List, Optional

from simultradia.domain.entities.modelo_ia_entity import ModeloIA
from simultradia.domain.enums import EstadoModelo, EstadoProceso, TipoModeloIA

_COLUMNAS = ("id_modelo, nombre, version, tipo, algoritmo, horizonte_dias, parametros, "
             "metricas_entrenamiento, ruta_artefacto, estado, entrenado_en, creado_en")


def _como_dict(valor) -> Dict:
    return json.loads(valor) if isinstance(valor, str) else (valor or {})


class ModeloIARepository:
    def siguiente_version(self, conn, nombre: str) -> str:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) AS total FROM modelos_ia WHERE nombre = %s", (nombre,))
            return "v%d" % (cur.fetchone().total + 1)

    def insertar(self, conn, modelo: ModeloIA) -> ModeloIA:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO modelos_ia (nombre, version, tipo, algoritmo, horizonte_dias, parametros, estado)
                   VALUES (%s, %s, %s, %s, %s, %s::json, %s)
                   RETURNING id_modelo, creado_en""",
                (modelo.nombre, modelo.version, modelo.tipo.value, modelo.algoritmo,
                 modelo.horizonte_dias, json.dumps(modelo.parametros), modelo.estado.value))
            fila = cur.fetchone()
        modelo.id_modelo, modelo.creado_en = fila.id_modelo, fila.creado_en
        return modelo

    def completar(self, conn, id_modelo: int, estado: EstadoModelo, metricas: Dict,
                  ruta_artefacto: str, entrenado_en: datetime) -> None:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE modelos_ia SET estado = %s, metricas_entrenamiento = %s::json,
                          ruta_artefacto = %s, entrenado_en = %s WHERE id_modelo = %s""",
                (estado.value, json.dumps(metricas), ruta_artefacto, entrenado_en, id_modelo))

    def marcar_fallido(self, conn, id_modelo: int) -> None:
        with conn.cursor() as cur:
            cur.execute("UPDATE modelos_ia SET estado = 'fallido' WHERE id_modelo = %s", (id_modelo,))

    def activar(self, conn, id_modelo: int) -> None:
        """Deja ACTIVO a este modelo y archiva al que lo estaba (mismo nombre), en la misma transacción."""
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE modelos_ia SET estado = 'archivado'
                   WHERE estado = 'activo' AND id_modelo <> %s
                     AND nombre = (SELECT nombre FROM modelos_ia WHERE id_modelo = %s)""",
                (id_modelo, id_modelo))
            cur.execute("UPDATE modelos_ia SET estado = 'activo' WHERE id_modelo = %s", (id_modelo,))

    def buscar(self, conn, id_modelo: int) -> Optional[ModeloIA]:
        with conn.cursor() as cur:
            cur.execute("SELECT " + _COLUMNAS + " FROM modelos_ia WHERE id_modelo = %s", (id_modelo,))
            fila = cur.fetchone()
        return self._a_modelo(fila) if fila else None

    def listar(self, conn, limite: int = 100) -> List[ModeloIA]:
        with conn.cursor() as cur:
            cur.execute("SELECT " + _COLUMNAS + " FROM modelos_ia ORDER BY creado_en DESC, id_modelo DESC LIMIT %s",
                        (limite,))
            return [self._a_modelo(f) for f in cur.fetchall()]

    def listar_activos(self, conn) -> List[ModeloIA]:
        """Los modelos de dirección que hoy generan predicciones (uno por horizonte)."""
        with conn.cursor() as cur:
            cur.execute("SELECT " + _COLUMNAS + " FROM modelos_ia "
                        "WHERE estado = 'activo' AND tipo = 'direccion' ORDER BY horizonte_dias")
            return [self._a_modelo(f) for f in cur.fetchall()]

    # ------------------------------------------------------- corridas de entrenamiento
    def abrir_entrenamiento(self, conn, id_modelo: int, id_usuario: Optional[int]) -> int:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO entrenamientos_modelo (id_modelo, solicitado_por, estado) "
                        "VALUES (%s, %s, 'ejecutando') RETURNING id_entrenamiento", (id_modelo, id_usuario))
            return cur.fetchone().id_entrenamiento

    def cerrar_entrenamiento(self, conn, id_entrenamiento: int, estado: EstadoProceso,
                             metricas: Dict, mensaje_error: Optional[str]) -> None:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE entrenamientos_modelo SET estado = %s, metricas = %s::json,
                          mensaje_error = %s, fin_en = now() WHERE id_entrenamiento = %s""",
                (estado.value, json.dumps(metricas), mensaje_error, id_entrenamiento))

    @staticmethod
    def _a_modelo(fila) -> ModeloIA:
        return ModeloIA(
            id_modelo=fila.id_modelo, nombre=fila.nombre, version=fila.version,
            tipo=TipoModeloIA(fila.tipo), algoritmo=fila.algoritmo, horizonte_dias=fila.horizonte_dias,
            parametros=_como_dict(fila.parametros), metricas=_como_dict(fila.metricas_entrenamiento),
            ruta_artefacto=fila.ruta_artefacto, estado=EstadoModelo(fila.estado),
            entrenado_en=fila.entrenado_en, creado_en=fila.creado_en)
