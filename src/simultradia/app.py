"""Ventana principal: crea el Navegador, registra las pantallas y muestra el login.

Los servicios llegan ya armados (los crea main.py con composition.crear_servicios).
Qué pantallas existen y cómo se arman está en iu/rutas.py; cómo se cambia de una a
otra, en iu/navegacion.py. El tamaño de la ventana lo fija cada pantalla al mostrarse.
"""
import ttkbootstrap as ttk

from simultradia.composition import Servicios
from simultradia.core.session import Session
from simultradia.core.settings import SETTINGS
from simultradia.iu.background import iniciar_revision
from simultradia.iu.navegacion import Navegador
from simultradia.iu.rutas import registrar_pantallas
from simultradia.iu.styles import Fonts


class App(ttk.Window):
    def __init__(self, servicios: Servicios, usuario_debug=None):  # DEBUG: + usuario_debug
        super().__init__(
            title=SETTINGS.app.name,
            themename="darkly",        # oscuros: darkly, superhero. Claros: flatly, litera
        )
        Fonts.register(self)       # define las fuentes de toda la interfaz
        iniciar_revision(self)     # activa la entrega de resultados de los hilos

        # La única sesión de la app: se entrega a quien la necesite.
        session = Session()
        self._navegador = Navegador(self, servicios, session)
        registrar_pantallas(self._navegador)
        if usuario_debug is not None:  # DEBUG
            session.iniciar(usuario_debug)  # DEBUG
            self._navegador.ir_a("home")  # DEBUG
        else:  # DEBUG
            self._navegador.ir_a("login")
