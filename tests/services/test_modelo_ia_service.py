"""Pruebas del entrenamiento y la activación de modelos (con repositorios en memoria y scikit-learn)."""
import unittest
from datetime import timedelta

from simultradia.core.exceptions import ErrorOperacionInvalida, ErrorPermisos
from simultradia.domain.entities.activo_entity import Activo
from simultradia.domain.entities.usuario_entity import Usuario
from simultradia.domain.enums import EstadoModelo, IntervaloVela, RolUsuario, TipoActivo
from simultradia.ia.serializacion import a_dict, desde_dict
from simultradia.services.modelo_ia_service import ModeloIAService
from tests.fakes import DatabaseFalsa, RepoActivoFalso, RepoPrecioFalso
from tests.services.ia_fakes import (
    AHORA, AlmacenFalso, ModeloRepoFalso, crear_modelo_prueba, serie_aleatoria, serie_ciclica, velas_desde)

ADMIN = Usuario("Jefe", "j@x.com", "h", rol=RolUsuario.ADMIN, id_usuario=1)
NORMAL = Usuario("Ana", "a@x.com", "h", id_usuario=2)
AYER = AHORA.replace(hour=0, minute=0) - timedelta(days=1)


def armar(generador, activos=4, dias=900):
    precios = RepoPrecioFalso()
    lista = [Activo("A%d" % i, "Activo %d" % i, TipoActivo.CRIPTO, id_activo=i) for i in range(1, activos + 1)]
    for a in lista:
        precios.velas[(a.id_activo, IntervaloVela.D1)] = velas_desde(generador(dias, a.id_activo), AYER)
    modelos, almacen = ModeloRepoFalso(), AlmacenFalso()
    servicio = ModeloIAService(DatabaseFalsa(), RepoActivoFalso(lista, precios), precios, modelos, almacen,
                               crear_modelo=crear_modelo_prueba, ahora=lambda: AHORA)
    return servicio, modelos, almacen


class PruebasModeloIAService(unittest.TestCase):
    def test_un_modelo_que_supera_la_base_queda_activo_y_guardado(self):
        servicio, modelos, almacen = armar(serie_ciclica)
        resultado = servicio.entrenar(ADMIN, 1)
        self.assertTrue(resultado.activado)
        modelo = modelos.modelos[0]
        self.assertEqual((modelo.nombre, modelo.version, modelo.estado), ("direccion_1d", "v1", EstadoModelo.ACTIVO))
        self.assertIn(modelo.ruta_artefacto, almacen.archivos)
        self.assertEqual(modelos.entrenamientos[modelo.id_modelo]["estado"], "completado")
        self.assertTrue(desde_dict(modelo.metricas).supera_base)

    def test_un_segundo_entrenamiento_archiva_al_anterior(self):
        servicio, modelos, _ = armar(serie_ciclica)
        servicio.entrenar(ADMIN, 1)
        servicio.entrenar(ADMIN, 1)
        self.assertEqual([m.estado for m in modelos.modelos], [EstadoModelo.ARCHIVADO, EstadoModelo.ACTIVO])
        self.assertEqual(modelos.modelos[1].version, "v2")

    def test_un_modelo_que_no_supera_la_base_no_se_activa_y_conserva_al_anterior(self):
        servicio, modelos, _ = armar(serie_ciclica)
        servicio.entrenar(ADMIN, 1)
        peor, _, _ = armar(serie_aleatoria)
        peor._modelos = modelos           # misma base de modelos, otros datos
        resultado = peor.entrenar(ADMIN, 1)
        self.assertFalse(resultado.activado)
        self.assertEqual([m.estado for m in modelos.modelos], [EstadoModelo.ACTIVO, EstadoModelo.ARCHIVADO])

    def test_solo_el_administrador_entrena_y_el_horizonte_debe_ser_valido(self):
        servicio, modelos, _ = armar(serie_ciclica)
        with self.assertRaises(ErrorPermisos):
            servicio.entrenar(NORMAL, 1)
        with self.assertRaises(ErrorOperacionInvalida):
            servicio.entrenar(ADMIN, 5)             # solo existe el horizonte de 1 día
        self.assertEqual(modelos.modelos, [])

    def test_si_el_entrenamiento_falla_queda_registrado(self):
        servicio, modelos, _ = armar(serie_ciclica, dias=30)      # muy pocas velas
        with self.assertRaises(ErrorOperacionInvalida):
            servicio.entrenar(ADMIN, 1)
        self.assertEqual(modelos.modelos[0].estado, EstadoModelo.FALLIDO)
        self.assertEqual(modelos.entrenamientos[1]["estado"], "fallido")
        self.assertTrue(modelos.entrenamientos[1]["error"])

    def test_activar_exige_una_version_archivada_que_supere_la_base(self):
        servicio, modelos, _ = armar(serie_ciclica)
        servicio.entrenar(ADMIN, 1)
        servicio.entrenar(ADMIN, 1)
        servicio.activar(ADMIN, 1)                                # revertir a la v1
        self.assertEqual([m.estado for m in modelos.modelos], [EstadoModelo.ACTIVO, EstadoModelo.ARCHIVADO])
        modelos.modelos[1].metricas = dict(a_dict(desde_dict(modelos.modelos[1].metricas)), z=0.1)
        with self.assertRaises(ErrorOperacionInvalida):
            servicio.activar(ADMIN, 2)                            # no supera la base
        with self.assertRaises(ErrorOperacionInvalida):
            servicio.activar(ADMIN, 99)
        with self.assertRaises(ErrorPermisos):
            servicio.activar(NORMAL, 1)

    def test_comparar_evalua_cada_algoritmo_sin_guardar_nada(self):
        servicio, modelos, almacen = armar(serie_ciclica)
        servicio._algoritmos = {"Uno": crear_modelo_prueba, "Dos": crear_modelo_prueba}
        resultado = servicio.comparar(ADMIN, 1)
        self.assertEqual([c.algoritmo for c in resultado], ["Uno", "Dos"])
        self.assertTrue(all(c.evaluacion.supera_base for c in resultado))
        self.assertEqual((modelos.modelos, almacen.archivos), ([], {}))
        with self.assertRaises(ErrorPermisos):
            servicio.comparar(NORMAL, 1)
        with self.assertRaises(ErrorOperacionInvalida):
            servicio.comparar(ADMIN, 7)

    def test_las_metricas_se_guardan_y_se_leen_sin_perder_nada(self):
        servicio, modelos, _ = armar(serie_ciclica)
        ev = servicio.entrenar(ADMIN, 1).evaluacion
        volvio = desde_dict(modelos.modelos[0].metricas)
        self.assertEqual((volvio.z, volvio.acierto, volvio.confusion), (ev.z, ev.acierto, ev.confusion))
        self.assertEqual(len(volvio.tramos), len(ev.tramos))
        self.assertEqual(len(volvio.calibracion), len(ev.calibracion))


if __name__ == "__main__":
    unittest.main()
