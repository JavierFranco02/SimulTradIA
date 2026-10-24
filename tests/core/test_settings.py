"""Pruebas de los ajustes jerárquicos."""
import dataclasses
import os
import unittest
from unittest import mock

from simultradia.core.settings import SETTINGS, load_settings


class PruebasSettings(unittest.TestCase):
    def test_los_ajustes_estan_agrupados_por_categoria(self):
        self.assertEqual(SETTINGS.app.name, "SimulTradIA")
        self.assertTrue(SETTINGS.database.host)

    def test_la_base_de_datos_se_lee_del_entorno(self):
        entorno = {"BD_HOST": "servidor", "BD_PUERTO": "6543", "BD_NOMBRE": "mi_bd"}
        with mock.patch.dict(os.environ, entorno):
            s = load_settings()
        self.assertEqual((s.database.host, s.database.port, s.database.name),
                         ("servidor", 6543, "mi_bd"))

    def test_los_ajustes_no_se_pueden_modificar_por_accidente(self):
        with self.assertRaises(dataclasses.FrozenInstanceError):
            SETTINGS.app.name = "otro"


if __name__ == "__main__":
    unittest.main()
