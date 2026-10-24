"""Navegador: cambia de pantalla por NOMBRE. Es lo que reciben los controladores.

    navegador.ir_a("login")
    navegador.ir_a("login", email="ana@x.com", mensaje="¡Cuenta creada!")
    navegador.ir_a("mercado")

Hay dos tipos de pantalla:
  - A VENTANA COMPLETA (login, registro, home): reemplazan todo el contenido de la ventana.
  - SECCIONES (`en_shell=True`: inicio, mercado, portafolio...): se dibujan dentro del
    área de contenido del shell (la vista "home"), que mantiene el menú lateral fijo.

El shell es una pantalla a ventana completa cuya vista cumple este protocolo:
    vista.contenido                 -> el Frame donde se dibujan las secciones
    vista.marcar_seccion(nombre)    -> resalta la sección activa del menú

Cada pantalla se registra con su "fábrica", una función que construye vista + controlador:

    def fabrica(padre, navegador, **parametros):
        vista = MiView(padre)
        MiController(vista, navegador.servicios.usuario, navegador)
        return vista

Quién registra qué está en `iu/rutas.py` y en el `pantallas.py` de cada módulo.
"""
from dataclasses import dataclass
from typing import Callable, Dict, Optional, Tuple


@dataclass(frozen=True)
class Ruta:
    fabrica: Callable
    en_shell: bool = False
    tamano: Optional[Tuple[int, int]] = None          # (ancho, alto) al mostrar la pantalla
    minimo: Optional[Tuple[int, int]] = None          # tamaño mínimo de la ventana
    seccion_inicial: Optional[str] = None             # sección que se abre sola dentro del shell


class Navegador:
    def __init__(self, ventana, servicios, session):
        self.servicios = servicios
        self.session = session
        self._ventana = ventana
        self._rutas: Dict[str, Ruta] = {}
        self._pantalla = None       # pantalla a ventana completa que se está mostrando
        self._seccion = None        # sección dentro del shell (si hay shell)
        self._contenido = None      # área de contenido del shell; None si no hay shell
        self._tamano: Optional[Tuple[int, int]] = None

    def registrar(self, nombre: str, fabrica: Callable, **opciones) -> None:
        if nombre in self._rutas:
            raise ValueError("La pantalla %r ya está registrada." % nombre)
        self._rutas[nombre] = Ruta(fabrica, **opciones)

    def ir_a(self, nombre: str, **parametros) -> None:
        ruta = self._rutas.get(nombre)
        if ruta is None:
            raise KeyError("No existe la pantalla %r." % nombre)
        if ruta.en_shell:
            self._mostrar_seccion(nombre, ruta, parametros)
        else:
            self._mostrar_pantalla(ruta, parametros)

    # --------------------------------------------------------------- interno
    def _mostrar_pantalla(self, ruta: Ruta, parametros: dict) -> None:
        self._ajustar_ventana(ruta)
        vista = ruta.fabrica(self._ventana, self, **parametros)
        if self._pantalla is not None:
            self._pantalla.destroy()    # destruye también las secciones que contenía
        self._pantalla = vista
        self._seccion = None
        self._contenido = getattr(vista, "contenido", None)
        vista.pack(fill="both", expand=True)
        if ruta.seccion_inicial and self._contenido is not None:
            self.ir_a(ruta.seccion_inicial)

    def _mostrar_seccion(self, nombre: str, ruta: Ruta, parametros: dict) -> None:
        if self._contenido is None:
            raise RuntimeError("La sección %r necesita el shell: ve primero a 'home'." % nombre)
        vista = ruta.fabrica(self._contenido, self, **parametros)
        if self._seccion is not None:
            self._seccion.destroy()
        self._seccion = vista
        vista.pack(fill="both", expand=True)
        self._pantalla.marcar_seccion(nombre)

    def _ajustar_ventana(self, ruta: Ruta) -> None:
        if ruta.minimo:
            self._ventana.minsize(*ruta.minimo)
        # Solo se redimensiona si cambia el tamaño: login <-> registro no mueve la ventana.
        if ruta.tamano and ruta.tamano != self._tamano:
            self._ventana.geometry("%dx%d" % ruta.tamano)
            self._ventana.place_window_center()
            self._tamano = ruta.tamano
