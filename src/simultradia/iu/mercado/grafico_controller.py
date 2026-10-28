"""Controlador del gráfico de Mercado: mantiene el precio y las velas del activo elegido al día.

  - Cada 2 s pide la cotización y se la aplica a la última vela (o abre una nueva): "tiempo real".
  - Cada ~30 s recarga las velas guardadas, que el worker va completando.
  - Cambiar de intervalo solo cambia qué velas se leen; la cotización es la misma.
  - Las respuestas que llegan tarde (de otro activo u otro intervalo) se descartan.
"""
from simultradia.domain.enums import IntervaloVela
from simultradia.iu.base.panel_controller import PanelController

_CADA_MS = 2000
_RECARGA_VELAS_CADA = 15   # ciclos de 2 s


class GraficoController(PanelController):
    def __init__(self, vista, mercado_service, grafico_service):
        super().__init__(vista)
        self._mercado = mercado_service
        self._grafico = grafico_service
        self._id_activo = None
        self._tipo = None             # tipo del activo elegido: decide si se abren velas nuevas en vivo
        self._intervalo = IntervaloVela.H1
        self._datos = None            # DatosGrafico del activo e intervalo actuales (None mientras carga)
        self._cotizacion = None       # la última cotización recibida de ESTE activo
        self._ultimo_precio = None
        self._peticion_velas = 0      # cada petición lleva un número: las de números viejos se descartan
        self._peticion_activo = 0
        self._consultando = False
        self._ciclos = 0
        vista.vincular_acciones(al_cambiar_intervalo=self.cambiar_intervalo)

    def cargar(self) -> None:
        """Arranca el refresco periódico (no hace nada hasta que se elija un activo)."""
        self._ciclo()

    def mostrar_activo(self, id_activo: int) -> None:
        if id_activo == self._id_activo:
            return
        self._id_activo = id_activo
        self._tipo = self._cotizacion = self._datos = self._ultimo_precio = None
        self._peticion_activo += 1
        self._consultando = False
        self._vista.limpiar_grafico()
        self._cargar_velas()
        self._consultar()

    def cambiar_intervalo(self, intervalo: IntervaloVela) -> None:
        if intervalo == self._intervalo:
            return
        self._intervalo = intervalo
        self._datos = None    # hasta que lleguen las velas nuevas no se mezcla nada
        self._ultimo_precio = None
        if self._id_activo is not None:
            self._cargar_velas()

    # --------------------------------------------------------------- interno
    def _cargar_velas(self) -> None:
        self._peticion_velas += 1
        numero, intervalo, id_activo = self._peticion_velas, self._intervalo, self._id_activo
        self._ejecutar(
            lambda: self._grafico.obtener_datos(id_activo, intervalo),
            al_terminar=lambda datos: self._al_velas(numero, intervalo, datos),
        )

    def _al_velas(self, numero: int, intervalo: IntervaloVela, datos) -> None:
        if numero != self._peticion_velas:
            return
        if self._cotizacion is not None:   # que la vela abierta ya muestre el precio de ahora
            datos = self._grafico.con_precio(datos, self._cotizacion, intervalo, self._tipo)
        self._datos = datos
        self._vista.mostrar_grafico(datos, intervalo)

    def _ciclo(self) -> None:
        if not self._vista.esta_viva():
            return
        self._ciclos += 1
        if self._id_activo is not None:
            if self._ciclos % _RECARGA_VELAS_CADA == 0:
                self._cargar_velas()
            self._consultar()
        self._vista.programar(_CADA_MS, self._ciclo)

    def _consultar(self) -> None:
        if self._consultando or self._id_activo is None:
            return
        self._consultando = True
        numero, id_activo = self._peticion_activo, self._id_activo
        self._ejecutar(lambda: self._mercado.obtener_activo(id_activo),
                       al_terminar=lambda item: self._al_activo(numero, item),
                       al_fallar=self._al_fallar_consulta)

    def _al_activo(self, numero: int, item) -> None:
        if numero != self._peticion_activo:   # respuesta de un activo que ya no está elegido
            return
        self._consultando = False
        self._vista.limpiar_mensaje()
        self._vista.mostrar_activo(item)
        self._tipo, cotizacion = item.activo.tipo, item.cotizacion
        self._cotizacion = cotizacion
        if cotizacion is None or self._datos is None or cotizacion.precio == self._ultimo_precio:
            return   # sin precio nuevo no hace falta redibujar
        self._ultimo_precio = cotizacion.precio
        self._datos = self._grafico.con_precio(self._datos, cotizacion, self._intervalo, self._tipo)
        self._vista.mostrar_grafico(self._datos, self._intervalo)

    def _al_fallar_consulta(self, error: Exception) -> None:
        self._consultando = False
        self._al_fallar(error)
