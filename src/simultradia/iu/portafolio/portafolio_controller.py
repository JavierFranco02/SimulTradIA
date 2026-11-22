"""Controlador de Portafolio: pide el resumen de la cuenta cada pocos segundos y se lo pasa a la vista.

  - Una sola consulta a la vez: si la anterior no ha terminado, el ciclo siguiente la espera.
  - Pide TODO de una vez (cifras, curva, métricas y operaciones cerradas): una sola conexión a la base.
  - Si la consulta falla y sigue fallando, el error se avisa una sola vez (no un diálogo cada 15 s).
"""
from simultradia.iu.base.panel_controller import PanelController

_CADA_MS = 15000


class PortafolioController(PanelController):
    def __init__(self, vista, portafolio_service, session):
        super().__init__(vista)
        self._servicio = portafolio_service
        self._session = session
        self._consultando = False

    def cargar(self) -> None:
        """Primera carga y, desde ahí, refresco automático mientras la pantalla siga viva."""
        self._ciclo()

    # --------------------------------------------------------------- interno
    def _ciclo(self) -> None:
        if not self._vista.esta_viva():
            return
        self._pedir()
        self._vista.programar(_CADA_MS, self._ciclo)

    def _pedir(self) -> None:
        if self._consultando:
            return
        self._consultando = True
        actor = self._session.usuario
        self._ejecutar(lambda: self._servicio.obtener_portafolio(actor),
                       al_terminar=self._al_cargar, al_fallar=self._al_fallar_carga)

    def _al_cargar(self, resumen) -> None:
        self._consultando = False
        self._recuperado("portafolio")
        self._vista.mostrar_portafolio(resumen)

    def _al_fallar_carga(self, error: Exception) -> None:
        self._consultando = False
        self._avisar_una_vez("portafolio", error)
