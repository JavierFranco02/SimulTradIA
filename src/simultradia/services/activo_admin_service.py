"""Administración del catálogo de activos: buscar, agregar, editar, habilitar y cambiar su fuente de datos.

Todo método recibe el `actor` y exige que sea administrador. Cada fuente solo ofrece ciertos
tipos de activo y escribe sus tickers a su manera (lo declara su cliente); al agregar se
comprueba que la fuente conozca el ticker. Las velas de un activo nuevo se descargan solas en
la siguiente pasada de la ingesta.
"""
import re
from typing import Dict, List, Optional

from simultradia.core.exceptions import DatosInvalidos, ErrorOperacionInvalida
from simultradia.domain.entities.activo_entity import Activo
from simultradia.domain.entities.cotizacion_entity import ActivoCotizado
from simultradia.domain.entities.fuente_entity import Fuente
from simultradia.domain.entities.usuario_entity import Usuario
from simultradia.domain.enums import TipoActivo
from simultradia.services.permisos import exigir_admin
from simultradia.services.validacion import lanzar_si_hay_errores

_PATRON_MONEDA = re.compile(r"^[A-Z]{3}$")


class ActivoAdminService:
    def __init__(self, db, activo_repository, precio_repository, fuente_repository,
                 clientes: Dict[str, object]):
        self._db = db
        self._activos = activo_repository
        self._precios = precio_repository
        self._fuentes = fuente_repository
        self._clientes = clientes            # nombre de la fuente -> su cliente

    def listar(self, actor: Usuario, texto: str = "", tipo: Optional[str] = None,
               habilitado: Optional[bool] = None) -> List[ActivoCotizado]:
        """El catálogo completo (con los deshabilitados), filtrado: `texto` busca en ticker y nombre;
        `tipo` es el valor del tipo ("cripto", "accion"...); `habilitado` True/False filtra por estado."""
        exigir_admin(actor)
        with self._db.obtener_conexion() as conn:
            items = self._activos.listar_cotizados(conn, solo_activos=False)
        texto = (texto or "").strip().lower()
        return [i for i in items
                if (not texto or texto in i.activo.ticker.lower() or texto in i.activo.nombre.lower())
                and (tipo is None or i.activo.tipo.value == tipo)
                and (habilitado is None or i.activo.activo == habilitado)]

    def agregar(self, actor: Usuario, ticker: str, nombre: str, tipo: str, id_fuente: int) -> Activo:
        exigir_admin(actor)
        ticker, nombre = (ticker or "").strip().upper(), (nombre or "").strip()
        tipo_activo, fuente, cliente, errores = self._revisar_origen(ticker, tipo, id_fuente)
        errores["nombre"] = self._error_nombre(nombre)
        lanzar_si_hay_errores(errores)
        with self._db.obtener_conexion() as conn:
            existente = self._activos.buscar_por_ticker(conn, ticker)
        if existente is not None:
            raise DatosInvalidos({"ticker": "Ese activo ya está en el catálogo."})
        # La consulta a la fuente va FUERA de la conexión: no se retiene una conexión de la base esperando a internet.
        if not cliente.existe_simbolo(ticker):
            raise DatosInvalidos({"ticker": "%s no tiene ese ticker. Revisa que esté bien escrito." % fuente.nombre})
        with self._db.obtener_conexion() as conn:
            return self._activos.insertar(conn, Activo(
                ticker=ticker, nombre=nombre, tipo=tipo_activo, id_fuente=fuente.id_fuente,
                moneda=self._moneda(ticker, tipo_activo)))

    def probar_ticker(self, actor: Usuario, ticker: str, tipo: str, id_fuente: int) -> str:
        """Comprueba, sin guardar nada, que la fuente reconoce ese ticker. Devuelve el nombre de la
        fuente. Si no, lanza DatosInvalidos con el motivo (formato, tipo no ofrecido, ticker desconocido)."""
        exigir_admin(actor)
        ticker = (ticker or "").strip().upper()
        _tipo, fuente, cliente, errores = self._revisar_origen(ticker, tipo, id_fuente)
        lanzar_si_hay_errores(errores)
        if not cliente.existe_simbolo(ticker):
            raise DatosInvalidos({"ticker": "%s no tiene ese ticker. Revisa que esté bien escrito." % fuente.nombre})
        return fuente.nombre

    def editar(self, actor: Usuario, id_activo: int, nombre: str, moneda: str) -> None:
        """Cambia el nombre y la moneda de un activo (el ticker y la fuente no se editan aquí)."""
        exigir_admin(actor)
        nombre, moneda = (nombre or "").strip(), (moneda or "").strip().upper()
        lanzar_si_hay_errores({"nombre": self._error_nombre(nombre), "moneda": self._error_moneda(moneda)})
        with self._db.obtener_conexion() as conn:
            if not self._activos.actualizar(conn, id_activo, nombre, moneda):
                raise ErrorOperacionInvalida("Ese activo no existe.")

    def cambiar_estado(self, actor: Usuario, id_activo: int, activo: bool) -> None:
        exigir_admin(actor)
        with self._db.obtener_conexion() as conn:
            if not self._activos.establecer_activo(conn, id_activo, activo):
                raise ErrorOperacionInvalida("Ese activo no existe.")

    def cambiar_fuente(self, actor: Usuario, id_activo: int, id_fuente: int) -> None:
        """Cambia de dónde vienen los precios de un activo. Se borran sus velas y su cotización
        guardadas: mezclar datos de dos fuentes distintas en un mismo gráfico lo falsearía."""
        exigir_admin(actor)
        with self._db.obtener_conexion() as conn:
            item = self._activos.buscar_cotizado(conn, id_activo)
            fuente = self._fuentes.buscar_por_id(conn, id_fuente)
        if item is None:
            raise ErrorOperacionInvalida("Ese activo no existe.")
        cliente = self._cliente_de(fuente)
        error = self._error_fuente(fuente, cliente, item.activo.tipo) or self._error_ticker(item.activo.ticker, cliente)
        if error:
            raise ErrorOperacionInvalida(error)
        if item.activo.id_fuente == fuente.id_fuente:
            return
        if not cliente.existe_simbolo(item.activo.ticker):
            raise ErrorOperacionInvalida("%s no tiene el ticker %s." % (fuente.nombre, item.activo.ticker))
        with self._db.obtener_conexion() as conn:
            self._activos.cambiar_fuente(conn, id_activo, fuente.id_fuente)
            self._precios.borrar_precios(conn, id_activo)

    # --------------------------------------------------------------- interno
    @staticmethod
    def _tipo(tipo: str) -> Optional[TipoActivo]:
        try:
            return TipoActivo(tipo)
        except ValueError:
            return None

    def _revisar_origen(self, ticker: str, tipo: str, id_fuente: int):
        """Valida tipo, fuente y ticker (lo que decide si la fuente puede dar este activo).
        Devuelve (tipo, fuente, cliente, errores por campo); `errores` queda vacío si todo está bien."""
        tipo_activo = self._tipo(tipo)
        with self._db.obtener_conexion() as conn:
            fuente = self._fuentes.buscar_por_id(conn, id_fuente)
        cliente = self._cliente_de(fuente)
        errores = {
            "tipo": None if tipo_activo else "Elige el tipo de activo.",
            "fuente": self._error_fuente(fuente, cliente, tipo_activo),
            "ticker": self._error_ticker(ticker, cliente),
        }
        return tipo_activo, fuente, cliente, errores

    def _cliente_de(self, fuente: Optional[Fuente]):
        return self._clientes.get(fuente.nombre) if fuente else None

    @staticmethod
    def _error_fuente(fuente: Optional[Fuente], cliente, tipo: Optional[TipoActivo]) -> Optional[str]:
        if fuente is None:
            return "Elige la fuente de datos."
        if cliente is None:
            return "La fuente %s todavía no está programada en la aplicación." % fuente.nombre
        if tipo is not None and tipo not in cliente.TIPOS:
            return "%s no ofrece ese tipo de activo." % fuente.nombre
        return None

    @staticmethod
    def _error_ticker(ticker: str, cliente) -> Optional[str]:
        if not ticker:
            return "Ingresa el ticker."
        if cliente is not None and not cliente.PATRON_TICKER.match(ticker):
            return "Formato no válido para esta fuente. Ejemplo: %s." % cliente.EJEMPLO_TICKER
        return None

    @staticmethod
    def _error_nombre(nombre: str) -> Optional[str]:
        if not nombre:
            return "Ingresa el nombre."
        if len(nombre) < 2 or len(nombre) > 150:
            return "El nombre debe tener entre 2 y 150 caracteres."
        return None

    @staticmethod
    def _error_moneda(moneda: str) -> Optional[str]:
        if not _PATRON_MONEDA.match(moneda):
            return "Usa un código de 3 letras, por ejemplo USD."
        return None

    @staticmethod
    def _moneda(ticker: str, tipo: TipoActivo) -> str:
        """Moneda del precio. Divisas de Yahoo ("USDJPY=X"): la segunda moneda del par."""
        if tipo == TipoActivo.DIVISA and ticker.endswith("=X") and len(ticker) == 8:
            return ticker[3:6]
        return "USD"
