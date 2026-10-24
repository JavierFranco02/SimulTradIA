"""Falsos compartidos por las pruebas (sin PostgreSQL, sin ventanas, sin red)."""
from contextlib import contextmanager
from types import SimpleNamespace


# ----------------------------------------------------------------- servicios
class DatabaseFalsa:
    @contextmanager
    def obtener_conexion(self):
        yield None


class RepositorioFalso:
    """Guarda los usuarios en un diccionario, en vez de en PostgreSQL."""

    def __init__(self):
        self.usuarios = {}
        self.logins = []
        self._siguiente_id = 1

    def buscar_por_email(self, conn, email):
        return self.usuarios.get(email.lower())

    def insertar(self, conn, usuario):
        usuario.id_usuario = self._siguiente_id
        self._siguiente_id += 1
        self.usuarios[usuario.email.lower()] = usuario
        return usuario

    def registrar_login(self, conn, id_usuario):
        self.logins.append(id_usuario)


class CuentaRepositorioFalso:
    def __init__(self):
        self.cuentas = []

    def insertar(self, conn, cuenta):
        cuenta.id_cuenta = len(self.cuentas) + 1
        self.cuentas.append(cuenta)
        return cuenta


# --------------------------------------------------------------- controladores
def en_el_acto(trabajo, al_terminar=None, al_fallar=None):
    """Reemplaza a ejecutar_en_hilo: corre el trabajo ya mismo, sin hilos."""
    try:
        resultado = trabajo()
    except Exception as error:
        if al_fallar:
            al_fallar(error)
    else:
        if al_terminar:
            al_terminar(resultado)


class EjecutorDiferido:
    """Como ejecutar_en_hilo, pero el resultado llega CUANDO el test lo decide:
    permite simular que el usuario cambia de pantalla mientras la operación sigue."""

    def __init__(self):
        self.pendientes = []

    def __call__(self, trabajo, al_terminar=None, al_fallar=None):
        self.pendientes.append((trabajo, al_terminar, al_fallar))

    def terminar_todo(self):
        for trabajo, al_terminar, al_fallar in self.pendientes:
            en_el_acto(trabajo, al_terminar, al_fallar)
        self.pendientes.clear()


class VistaFalsa:
    def __init__(self, email="ana@x.com", password="Clave12345", nombre="Ana", confirmacion=None):
        self.email, self.password, self.nombre = email, password, nombre
        self.confirmacion = password if confirmacion is None else confirmacion
        self.ocupado = False
        self.viva = True
        self.error_general = None
        self.errores_campos = {}
        self.campos_limpiados = []
        self.errores_limpiados = 0
        self.acciones = {}

    def valores(self):
        return {"nombre": self.nombre, "email": self.email,
                "password": self.password, "confirmacion": self.confirmacion}

    def vincular_acciones(self, **acciones): self.acciones = acciones
    def establecer_ocupado(self, ocupado): self.ocupado = ocupado
    def limpiar_errores(self): self.errores_limpiados += 1
    def limpiar_campo(self, clave): self.campos_limpiados.append(clave)
    def mostrar_error(self, texto): self.error_general = texto
    def mostrar_errores_campos(self, errores): self.errores_campos = dict(errores)
    def esta_viva(self): return self.viva


class NavegadorFalso:
    def __init__(self):
        self.llamadas = []

    def ir_a(self, nombre, **parametros): self.llamadas.append((nombre, parametros))


class ServicioFalso:
    def __init__(self, resultado=None, error=None):
        self.resultado, self.error, self.llamadas = resultado, error, []

    def _responder(self, nombre, *args):
        self.llamadas.append((nombre,) + args)
        if self.error:
            raise self.error
        return self.resultado

    def autenticar(self, email, password): return self._responder("autenticar", email, password)
    def registrar(self, *datos): return self._responder("registrar", *datos)


# ------------------------------------------------------------------ navegador
class VentanaFalsa:
    def __init__(self):
        self.minimos, self.geometrias, self.centrados = [], [], 0

    def minsize(self, ancho, alto): self.minimos.append((ancho, alto))
    def geometry(self, texto): self.geometrias.append(texto)
    def place_window_center(self): self.centrados += 1


class PantallaFalsa:
    """Vista mínima: sabe empaquetarse y destruirse."""

    def __init__(self, padre, **parametros):
        self.padre = padre
        self.parametros = parametros
        self.empaquetada = False
        self.destruida = False

    def pack(self, **opciones): self.empaquetada = True
    def destroy(self): self.destruida = True


class ShellFalso(PantallaFalsa):
    """Vista que cumple el protocolo del shell: `contenido` y `marcar_seccion`."""

    def __init__(self, padre, **parametros):
        super().__init__(padre, **parametros)
        self.contenido = SimpleNamespace(nombre="contenido")
        self.secciones_marcadas = []

    def marcar_seccion(self, nombre): self.secciones_marcadas.append(nombre)
