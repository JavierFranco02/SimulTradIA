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
from simultradia.core.settings import PROJECT_ROOT
from simultradia.ia.almacen import AlmacenModelos
from simultradia.repositories.activo_repository import ActivoRepository
from simultradia.repositories.cuenta_repository import CuentaRepository
from simultradia.repositories.fuente_repository import FuenteRepository
from simultradia.repositories.modelo_ia_repository import ModeloIARepository
from simultradia.repositories.orden_repository import OrdenRepository
from simultradia.repositories.posicion_repository import PosicionRepository
from simultradia.repositories.prediccion_volatilidad_repository import PrediccionVolatilidadRepository
from simultradia.repositories.precio_repository import PrecioRepository
from simultradia.repositories.snapshot_repository import SnapshotRepository
from simultradia.repositories.usuario_repository import UsuarioRepository
from simultradia.services.activo_admin_service import ActivoAdminService
from simultradia.services.fuente_admin_service import FuenteAdminService
from simultradia.services.grafico_service import GraficoService
from simultradia.services.ingesta_service import IngestaService
from simultradia.services.mercado_service import MercadoService
from simultradia.services.modelo_volatilidad_service import ModeloVolatilidadService
from simultradia.services.operar_service import OperarService
from simultradia.services.prediccion_volatilidad_service import PrediccionVolatilidadService
from simultradia.services.portafolio_service import PortafolioService
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
    operar: OperarService
    volatilidad: PrediccionVolatilidadService
    modelo_volatilidad: ModeloVolatilidadService
    portafolio: PortafolioService


def crear_servicios(db) -> Servicios:
    usuarios, activos, cuentas = UsuarioRepository(), ActivoRepository(), CuentaRepository()
    modelos, predicciones, almacen = ModeloIARepository(), PrediccionVolatilidadRepository(), AlmacenModelos(PROJECT_ROOT)
    precios, fuentes, posiciones = PrecioRepository(), FuenteRepository(), PosicionRepository()
    clientes = {cliente.NOMBRE: cliente for cliente in (BinanceCliente(), YahooCliente())}
    return Servicios(
        usuario=UsuarioService(db, usuarios, cuentas),
        usuario_admin=UsuarioAdminService(db, usuarios),
        mercado=MercadoService(db, activos),
        grafico=GraficoService(db, precios),
        ingesta=IngestaService(db, activos, precios, fuentes, clientes),
        activo_admin=ActivoAdminService(db, activos, precios, fuentes, clientes),
        fuente_admin=FuenteAdminService(db, fuentes),
        operar=OperarService(db, cuentas, posiciones, OrdenRepository(), activos, precios),
        portafolio=PortafolioService(db, cuentas, posiciones, activos, SnapshotRepository()),
        volatilidad=PrediccionVolatilidadService(db, activos, precios, modelos, predicciones, almacen),
        modelo_volatilidad=ModeloVolatilidadService(db, activos, precios, modelos, almacen),
       
    )
