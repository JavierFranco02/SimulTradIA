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

    def actualizar_password(self, conn, id_usuario, password_hash, debe_cambiar):
        for usuario in self.usuarios.values():
            if usuario.id_usuario == id_usuario:
                usuario.password_hash, usuario.debe_cambiar_password = password_hash, debe_cambiar
                return True
        return False


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
    def __init__(self, email="ana@x.com", password="Clave12345", nombre="Ana", confirmacion=None,
                 actual="Temporal1"):
        self.email, self.password, self.nombre, self.actual = email, password, nombre, actual
        self.confirmacion = password if confirmacion is None else confirmacion
        self.ocupado = False
        self.viva = True
        self.error_general = None
        self.errores_campos = {}
        self.campos_limpiados = []
        self.errores_limpiados = 0
        self.acciones = {}

    def valores(self):
        return {"nombre": self.nombre, "email": self.email, "actual": self.actual,
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


# ------------------------------------------------------- mercado y administración
class RepoPrecioFalso:
    """Guarda cotizaciones y velas en diccionarios, en vez de en PostgreSQL."""

    def __init__(self):
        self.cotizaciones = {}          # id_activo -> Cotizacion
        self.velas = {}                 # (id_activo, intervalo) -> [Vela]
        self.ultima = None

    def guardar_cotizacion(self, conn, c): self.cotizaciones[c.id_activo] = c

    def ultima_actualizacion(self, conn): return self.ultima

    def ultimo_momento(self, conn, id_activo, intervalo):
        velas = self.velas.get((id_activo, intervalo), [])
        return velas[-1].momento if velas else None

    def reemplazar_velas(self, conn, id_activo, intervalo, velas):
        if not velas:
            return
        desde = min(v.momento for v in velas)
        previas = [v for v in self.velas.get((id_activo, intervalo), []) if v.momento < desde]
        self.velas[(id_activo, intervalo)] = previas + sorted(velas, key=lambda v: v.momento)

    def buscar_velas(self, conn, id_activo, intervalo, limite):
        return self.velas.get((id_activo, intervalo), [])[-limite:]

    def contar_velas_por_intervalo(self, conn):
        total = {}
        for (_id, intervalo), velas in self.velas.items():
            total[intervalo.value] = total.get(intervalo.value, 0) + len(velas)
        return total

    def borrar_precios(self, conn, id_activo):
        self.cotizaciones.pop(id_activo, None)
        for clave in [k for k in self.velas if k[0] == id_activo]:
            del self.velas[clave]


class RepoActivoFalso:
    def __init__(self, activos=(), precios=None):
        self.activos = list(activos)
        self.precios = precios or RepoPrecioFalso()
        self._siguiente_id = 1 + max([a.id_activo for a in self.activos] + [0])

    def listar_activos(self, conn, solo_activos=True):
        return [a for a in self.activos if a.activo or not solo_activos]

    def listar_cotizados(self, conn, solo_activos=True):
        from simultradia.domain.entities.cotizacion_entity import ActivoCotizado
        return [ActivoCotizado(a, self.precios.cotizaciones.get(a.id_activo))
                for a in self.listar_activos(conn, solo_activos)]

    def buscar_cotizado(self, conn, id_activo):
        return next((i for i in self.listar_cotizados(conn, False) if i.activo.id_activo == id_activo), None)

    def buscar_por_ticker(self, conn, ticker):
        return next((a for a in self.activos if a.ticker.upper() == ticker.upper()), None)

    def insertar(self, conn, activo):
        activo.id_activo = self._siguiente_id
        self._siguiente_id += 1
        self.activos.append(activo)
        return activo

    def establecer_activo(self, conn, id_activo, activo):
        for a in self.activos:
            if a.id_activo == id_activo:
                a.activo = activo
                return True
        return False

    def actualizar(self, conn, id_activo, nombre, moneda):
        for a in self.activos:
            if a.id_activo == id_activo:
                a.nombre, a.moneda = nombre, moneda
                return True
        return False

    def cambiar_fuente(self, conn, id_activo, id_fuente):
        for a in self.activos:
            if a.id_activo == id_activo:
                a.id_fuente = id_fuente
                return True
        return False


class RepoFuenteFalso:
    def __init__(self, fuentes=()):
        self.fuentes = list(fuentes)

    def listar(self, conn): return list(self.fuentes)

    def buscar_por_id(self, conn, id_fuente):
        return next((f for f in self.fuentes if f.id_fuente == id_fuente), None)

    def establecer_activa(self, conn, id_fuente, activa):
        fuente = self.buscar_por_id(conn, id_fuente)
        if fuente is None:
            return False
        fuente.activa = activa
        return True


class UsuarioRepoAdminFalso:
    def __init__(self, usuarios=()):
        self.usuarios = list(usuarios)

    def listar(self, conn): return list(self.usuarios)

    def buscar_por_id(self, conn, id_usuario):
        return next((u for u in self.usuarios if u.id_usuario == id_usuario), None)

    def actualizar_password(self, conn, id_usuario, password_hash, debe_cambiar):
        usuario = self.buscar_por_id(conn, id_usuario)
        if usuario is None:
            return False
        usuario.password_hash, usuario.debe_cambiar_password = password_hash, debe_cambiar
        return True

    def establecer_activo(self, conn, id_usuario, activo):
        for u in self.usuarios:
            if u.id_usuario == id_usuario:
                u.activo = activo
                return True
        return False


class ClienteMercadoFalso:
    """Hace de una fuente de datos (Binance, Yahoo...): devuelve lo que el test le prepare y anota
    lo que le piden. Declara, como los clientes reales, qué tipos y tickers acepta y su ritmo."""

    def __init__(self, nombre="Binance", tipos=None, patron=r"^[A-Z0-9]{2,15}/USDT$", ejemplo="BTC/USDT",
                 cotizaciones=None, velas=None, simbolos=(), error=None,
                 segundos_cotizaciones=2, segundos_velas=60):
        import re
        from simultradia.domain.enums import TipoActivo
        self.NOMBRE = nombre
        self.TIPOS = frozenset(tipos if tipos is not None else {TipoActivo.CRIPTO})
        self.PATRON_TICKER = re.compile(patron)
        self.EJEMPLO_TICKER = ejemplo
        self.segundos_entre_cotizaciones = segundos_cotizaciones
        self.segundos_entre_velas = segundos_velas
        self.cotizaciones = cotizaciones or {}     # ticker -> Cotizacion
        self.velas = velas or {}                   # (ticker, intervalo) -> [Vela]
        self.simbolos = set(simbolos)
        self.error = error
        self.pedidos_cotizaciones = []             # lista de tickers pedidos en cada llamada
        self.pedidos_velas = []                    # (ticker, intervalo, desde)

    def existe_simbolo(self, ticker):
        if self.error:
            raise self.error
        return ticker in self.simbolos

    def obtener_cotizaciones(self, tickers):
        if self.error:
            raise self.error
        self.pedidos_cotizaciones.append(list(tickers))
        return {t: c for t, c in self.cotizaciones.items() if t in tickers}

    def obtener_velas(self, ticker, intervalo, desde):
        if self.error:
            raise self.error
        self.pedidos_velas.append((ticker, intervalo, desde))
        return [v for v in self.velas.get((ticker, intervalo), []) if v.momento >= desde]


class ServicioGenerico:
    """Servicio falso para controladores: responde a CUALQUIER método con lo que se le preparó.

        ServicioGenerico(obtener_panel="PANEL", listar=ErrorAplicacion("x"))
    Si el valor preparado es una excepción, se lanza. Todas las llamadas quedan en `llamadas`."""

    def __init__(self, **respuestas):
        self._respuestas = respuestas
        self.llamadas = []

    def __getattr__(self, nombre):
        def llamar(*argumentos):
            self.llamadas.append((nombre,) + argumentos)
            respuesta = self._respuestas.get(nombre)
            if isinstance(respuesta, Exception):
                raise respuesta
            return respuesta
        return llamar


class VistaPanelFalsa:
    """Vista falsa de una sección: anota lo que el controlador le ordena."""

    def __init__(self, busqueda="", valores=None, confirma=True, categoria=None):
        self.viva = True
        self.ocupado = False
        self._busqueda, self._valores, self._confirma, self._categoria = busqueda, valores or {}, confirma, categoria
        self.acciones = {}
        self.programadas = []      # (milisegundos, accion)
        self.error = self.exito = None
        self.mensajes_limpiados = 0
        self.eventos = []          # (nombre, argumentos) de cada mostrar_* / limpiar_*
        self.filtros_ = ("", None, None)

    def esta_viva(self): return self.viva
    def vincular_acciones(self, **acciones): self.acciones = acciones
    def programar(self, ms, accion): self.programadas.append((ms, accion))
    def texto_busqueda(self): return self._busqueda
    def categoria(self): return self._categoria
    def filtros(self): return self.filtros_
    def valores(self): return dict(self._valores)
    def confirmar(self, mensaje): return self._confirma
    def establecer_ocupado(self, ocupado): self.ocupado = ocupado
    def mostrar_error(self, texto): self.error = texto
    def mostrar_exito(self, texto): self.exito = texto
    def limpiar_mensaje(self): self.mensajes_limpiados += 1
    def limpiar_errores(self): self.eventos.append(("limpiar_errores", ()))
    def limpiar_formulario(self): self.eventos.append(("limpiar_formulario", ()))
    def limpiar_grafico(self): self.eventos.append(("limpiar_grafico", ()))
    def seleccionar(self, id_activo): self.eventos.append(("seleccionar", id_activo))
    def establecer_fuentes(self, fuentes): self.eventos.append(("fuentes", fuentes))
    def mostrar_errores_campos(self, errores): self.eventos.append(("errores_campos", dict(errores)))
    def mostrar_panel(self, panel, orden, descendente): self.eventos.append(("panel", (panel, orden, descendente)))
    def mostrar_activo(self, item): self.eventos.append(("activo", item))
    def mostrar_grafico(self, datos, intervalo): self.eventos.append(("grafico", (datos, intervalo)))
    def mostrar_usuarios(self, usuarios): self.eventos.append(("usuarios", usuarios))
    def mostrar_contrasena_temporal(self, id_usuario, password): self.eventos.append(("temporal", (id_usuario, password)))
    def mostrar_errores_edicion(self, errores): self.eventos.append(("errores_edicion", dict(errores)))
    def limpiar_errores_edicion(self): self.eventos.append(("limpiar_errores_edicion", ()))
    def mostrar_activos(self, items): self.eventos.append(("activos", items))
    def mostrar_estado(self, estado, fuentes=None): self.eventos.append(("estado", (estado, fuentes)))

    def ultimo(self, nombre):
        coincidencias = [argumentos for n, argumentos in self.eventos if n == nombre]
        return coincidencias[-1] if coincidencias else None


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
