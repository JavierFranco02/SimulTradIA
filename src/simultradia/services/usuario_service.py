"""Casos de uso de usuarios: autenticar (verificar el login), registrarse y cambiar la contraseña temporal.

Aquí viven las REGLAS y las VALIDACIONES. Este archivo NO conoce tkinter ni SQL:
usa los repositorios para hablar con la base de datos y lanza errores propios que
el controlador entrega a la pantalla.
"""
import re
from decimal import Decimal
from typing import Dict, Optional

from simultradia.core.exceptions import (
    CredencialesInvalidas,
    CuentaDesactivada,
    DatosInvalidos,
    EmailYaRegistrado,
)
from simultradia.core.security import (
    gastar_tiempo_de_verificacion,
    hashear_password,
    verificar_password,
)
from simultradia.domain.entities.cuenta_simulada_entity import CuentaSimulada
from simultradia.domain.entities.usuario_entity import Usuario
from simultradia.domain.enums import RolUsuario

_PATRON_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class UsuarioService:
    def __init__(self, db, usuario_repository, cuenta_repository):
        self._db = db
        self._usuarios = usuario_repository
        self._cuentas = cuenta_repository

    # ----------------------------------------------------------------- login
    def autenticar(self, email: str, password: str) -> Usuario:
        """Verifica el email y la contraseña y devuelve el usuario.

        NO inicia ninguna sesión: eso lo decide quien llama (el controlador), cuando el
        resultado llega a una pantalla que sigue vigente. Si el usuario tiene una contraseña
        temporal (`debe_cambiar_password`), el controlador lo manda a cambiarla en vez de entrar.
        """
        email = self._normalizar_email(email)

        self._lanzar_si_hay_errores({
            "email": self._error_email(email),
            "password": None if password else "Ingresa tu contraseña.",
        })

        with self._db.obtener_conexion() as conn:
            usuario = self._usuarios.buscar_por_email(conn, email)

            if usuario is None:
                gastar_tiempo_de_verificacion(password)
                raise CredencialesInvalidas()
            if not verificar_password(password, usuario.password_hash):
                raise CredencialesInvalidas()
            # La cuenta desactivada se avisa DESPUÉS de comprobar la contraseña,
            # para no revelar a un desconocido qué emails existen.
            if not usuario.activo:
                raise CuentaDesactivada()

            self._usuarios.registrar_login(conn, usuario.id_usuario)

        return usuario

    # -------------------------------------------------------------- registro
    def registrar(self, nombre: str, email: str, password: str, confirmacion: str) -> Usuario:
        """Registro público: siempre crea un usuario normal (con su cuenta simulada)."""
        return self._crear(nombre, email, password, confirmacion, RolUsuario.USUARIO)

    def crear_administrador(self, nombre: str, email: str, password: str, confirmacion: str) -> Usuario:
        """Solo se usa desde scripts/crear_admin.py, nunca desde la pantalla de registro."""
        return self._crear(nombre, email, password, confirmacion, RolUsuario.ADMIN)

    # ------------------------------------------------- contraseña temporal
    def cambiar_password_temporal(self, email: str, password_actual: str, password_nueva: str,
                                  confirmacion: str) -> Usuario:
        """Cambia la contraseña temporal que entregó el administrador por una elegida por el usuario.

        Pide la temporal otra vez (no hay sesión abierta todavía) y solo funciona si la cuenta
        tiene un cambio pendiente. NO inicia sesión: la persona vuelve al login con la nueva.
        """
        email = self._normalizar_email(email)
        errores = {
            "actual": None if password_actual else "Ingresa tu contraseña temporal.",
            "password": self._error_password(password_nueva),
        }
        if not errores["password"]:
            errores["confirmacion"] = self._error_confirmacion(password_nueva, confirmacion)
            if password_nueva == password_actual:
                errores["password"] = "La contraseña nueva debe ser distinta de la temporal."
        self._lanzar_si_hay_errores(errores)

        with self._db.obtener_conexion() as conn:
            usuario = self._usuarios.buscar_por_email(conn, email)
            if usuario is None:
                gastar_tiempo_de_verificacion(password_actual)
                raise CredencialesInvalidas()
            if not verificar_password(password_actual, usuario.password_hash):
                raise CredencialesInvalidas()
            if not usuario.activo:
                raise CuentaDesactivada()
            if not usuario.debe_cambiar_password:
                raise CredencialesInvalidas("Esta cuenta no tiene un cambio de contraseña pendiente.")
            self._usuarios.actualizar_password(conn, usuario.id_usuario, hashear_password(password_nueva), False)
        usuario.debe_cambiar_password = False
        return usuario

    # --------------------------------------------------------------- interno
    def _crear(self, nombre: str, email: str, password: str, confirmacion: str,
               rol: RolUsuario) -> Usuario:
        nombre = (nombre or "").strip()
        email = self._normalizar_email(email)
        self._validar_registro(nombre, email, password, confirmacion)

        usuario = Usuario(
            nombre=nombre,
            email=email,
            password_hash=hashear_password(password),
            rol=rol,
        )
        # Usuario y cuenta se guardan en la MISMA transacción: si falla uno, no queda ninguno.
        with self._db.obtener_conexion() as conn:
            if self._usuarios.buscar_por_email(conn, email) is not None:
                raise EmailYaRegistrado()
            usuario = self._usuarios.insertar(conn, usuario)
            if rol == RolUsuario.USUARIO:   # el administrador gestiona, no opera
                self._cuentas.insertar(conn, self._cuenta_inicial(usuario))
            return usuario

    @staticmethod
    def _cuenta_inicial(usuario: Usuario) -> CuentaSimulada:
        capital = Decimal("10000")
        return CuentaSimulada(
            id_usuario=usuario.id_usuario,
            nombre="Cuenta principal",
            capital_inicial=capital,
            saldo_disponible=capital,
        )

    @staticmethod
    def _normalizar_email(email: str) -> str:
        return (email or "").strip().lower()

    # ---------------------------------------------------------- validaciones
    # Una función por campo: devuelven el mensaje de error, o None si el campo está bien.
    # Cada caso de uso (login, registro...) arma su lista combinando las que necesita.

    @staticmethod
    def _error_nombre(nombre: str) -> Optional[str]:
        if not nombre:
            return "Ingresa tu nombre."
        if len(nombre) < 2 or len(nombre) > 100:
            return "El nombre debe tener entre 2 y 100 caracteres."
        return None

    @staticmethod
    def _error_email(email: str) -> Optional[str]:
        if not email:
            return "Ingresa tu email."
        if len(email) > 255 or not _PATRON_EMAIL.match(email):
            return "Ingresa un email válido (por ejemplo: nombre@correo.com)."
        return None

    @staticmethod
    def _error_password(password: str) -> Optional[str]:
        """Reglas para ELEGIR una contraseña nueva. En el login solo se exige que no esté vacía."""
        if not password:
            return "Ingresa una contraseña."
        if len(password) < 8:
            return "La contraseña debe tener al menos 8 caracteres."
        if len(password) > 128:
            return "La contraseña es demasiado larga (máximo 128 caracteres)."
        return None

    @staticmethod
    def _error_confirmacion(password: str, confirmacion: str) -> Optional[str]:
        if password != confirmacion:
            return "Las contraseñas no coinciden."
        return None

    @staticmethod
    def _lanzar_si_hay_errores(errores: Dict[str, Optional[str]]) -> None:
        """Recibe {campo: mensaje o None}. Si algún campo tiene mensaje, avisa de todos a la vez."""
        reales = {campo: mensaje for campo, mensaje in errores.items() if mensaje}
        if reales:
            raise DatosInvalidos(reales)

    def _validar_registro(self, nombre: str, email: str, password: str, confirmacion: str) -> None:
        errores = {
            "nombre": self._error_nombre(nombre),
            "email": self._error_email(email),
            "password": self._error_password(password),
        }
        if not errores["password"]:   # solo se compara con la confirmación si la contraseña es válida
            errores["confirmacion"] = self._error_confirmacion(password, confirmacion)
        self._lanzar_si_hay_errores(errores)
