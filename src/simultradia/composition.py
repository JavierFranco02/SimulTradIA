"""Armado de los servicios: UN solo lugar donde se conectan servicios y repositorios.

Lo usan main.py, worker.py y los scripts, para que ninguno repita el armado:

    db = Database(SETTINGS.database)
    servicios = crear_servicios(db)
    servicios.usuario.registrar(...)

Para agregar un servicio: súmalo a `Servicios` y a `crear_servicios`. Para sumar una fuente de
datos nueva: escribe su cliente en clients/ y regístralo en `clientes` (con el mismo nombre que
tiene en la tabla fuentes_datos).
"""
from dataclasses import dataclass

from simultradia.clients.binance_client import BinanceCliente
from simultradia.clients.yahoo_client import YahooCliente
from simultradia.repositories.activo_repository import ActivoRepository
from simultradia.repositories.cuenta_repository import CuentaRepository
from simultradia.repositories.fuente_repository import FuenteRepository
from simultradia.repositories.precio_repository import PrecioRepository
from simultradia.repositories.usuario_repository import UsuarioRepository
from simultradia.services.activo_admin_service import ActivoAdminService
from simultradia.services.fuente_admin_service import FuenteAdminService
from simultradia.services.grafico_service import GraficoService
from simultradia.services.ingesta_service import IngestaService
from simultradia.services.mercado_service import MercadoService
from simultradia.services.usuario_admin_service import UsuarioAdminService
from simultradia.services.usuario_service import UsuarioService


@dataclass(frozen=True)
class Servicios:
    usuario: UsuarioService
    usuario_admin: UsuarioAdminService
    mercado: MercadoService
    grafico: GraficoService
    ingesta: IngestaService
    activo_admin: ActivoAdminService
    fuente_admin: FuenteAdminService


def crear_servicios(db) -> Servicios:
    usuarios, activos = UsuarioRepository(), ActivoRepository()
    precios, fuentes = PrecioRepository(), FuenteRepository()
    clientes = {cliente.NOMBRE: cliente for cliente in (BinanceCliente(), YahooCliente())}
    return Servicios(
        usuario=UsuarioService(db, usuarios, CuentaRepository()),
        usuario_admin=UsuarioAdminService(db, usuarios),
        mercado=MercadoService(db, activos),
        grafico=GraficoService(db, precios),
        ingesta=IngestaService(db, activos, precios, fuentes, clientes),
        activo_admin=ActivoAdminService(db, activos, precios, fuentes, clientes),
        fuente_admin=FuenteAdminService(db, fuentes),
    )
