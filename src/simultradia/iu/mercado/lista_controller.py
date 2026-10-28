"""Controlador de la lista de Mercado: la pide al servicio cada pocos segundos y se la pasa a la vista.

  - Buscar, cambiar de categoría o de pestaña, u ordenar vuelve a pedir la lista de inmediato.
  - Si llega una respuesta vieja (el usuario ya buscó otra cosa), se descarta.
  - Al terminar la primera carga elige el primer activo, para que el gráfico no empiece vacío.
"""
from simultradia.iu.base.panel_controller import PanelController

_CADA_MS = 3000
# pestaña -> (filtro, columna de orden, descendente)
_PESTANAS = {
    "todos": ("todos", "ticker", False),
    "ganadores": ("ganadores", "variacion", True),
    "perdedores": ("perdedores", "variacion", False),
    "volumen": ("todos", "volumen", True),
}


class ListaController(PanelController):
    def __init__(self, vista, mercado_service, al_elegir_activo):
        """`al_elegir_activo(id_activo)` es quien muestra el gráfico del activo elegido."""
        super().__init__(vista)
        self._servicio = mercado_service
        self._filtro, self._orden, self._descendente = _PESTANAS["todos"]
        self._solicitud = 0        # número de la última petición: las anteriores se descartan
        self._cargando = False
        self._eligio_primero = False
        vista.vincular_acciones(
            al_filtrar=self._pedir,
            al_elegir_pestana=self.elegir_pestana,
            al_ordenar=self.ordenar,
            al_elegir_activo=al_elegir_activo,
        )

    def cargar(self) -> None:
        """Primera carga y, desde ahí, refresco automático mientras la pantalla siga viva."""
        self._ciclo()

    def elegir_pestana(self, pestana: str) -> None:
        self._filtro, self._orden, self._descendente = _PESTANAS[pestana]
        self._pedir()

    def ordenar(self, columna: str) -> None:
        if columna == self._orden:
            self._descendente = not self._descendente
        else:
            # los números interesan de mayor a menor; el nombre, de la A a la Z
            self._orden, self._descendente = columna, columna != "ticker"
        self._pedir()

    # --------------------------------------------------------------- interno
    def _ciclo(self) -> None:
        if not self._vista.esta_viva():
            return
        if not self._cargando:
            self._pedir()
        self._vista.programar(_CADA_MS, self._ciclo)

    def _pedir(self) -> None:
        self._solicitud += 1
        numero = self._solicitud
        texto, tipo = self._vista.texto_busqueda(), self._vista.categoria()
        filtro, orden, descendente = self._filtro, self._orden, self._descendente
        self._cargando = True
        self._ejecutar(
            lambda: self._servicio.obtener_panel(texto, filtro, orden, descendente, tipo),
            al_terminar=lambda panel: self._al_cargar(numero, panel, orden, descendente),
            al_fallar=self._al_fallar_carga,
        )

    def _al_cargar(self, numero: int, panel, orden: str, descendente: bool) -> None:
        self._cargando = False
        if numero != self._solicitud:   # llegó una respuesta vieja
            return
        self._vista.mostrar_panel(panel, orden, descendente)
        if not self._eligio_primero and panel.items:
            self._eligio_primero = True
            self._vista.seleccionar(panel.items[0].activo.id_activo)

    def _al_fallar_carga(self, error: Exception) -> None:
        self._cargando = False
        self._al_fallar(error)
