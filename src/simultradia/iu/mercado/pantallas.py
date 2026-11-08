"""Pantalla del módulo Mercado (sección dentro del shell): lista de activos + gráfico."""
from simultradia.iu.mercado.grafico_controller import GraficoController
from simultradia.iu.mercado.lista_controller import ListaController
from simultradia.iu.mercado.mercado_view import MercadoView


def _mercado(padre, nav):
    vista = MercadoView(padre)
    grafico = GraficoController(vista.grafico, nav.servicios.mercado, nav.servicios.grafico)

    def elegir_activo(id_activo: int) -> None:
        vista.establecer_activo_elegido(id_activo)
        grafico.mostrar_activo(id_activo)

    lista = ListaController(vista.lista, nav.servicios.mercado, al_elegir_activo=elegir_activo)
    if not nav.session.es_admin:      # el administrador gestiona, no opera
        vista.vincular_acciones(al_operar=lambda id_activo: nav.ir_a("operar", id_activo=id_activo))
    grafico.cargar()
    lista.cargar()
    return vista


def registrar(navegador) -> None:
    navegador.registrar("mercado", _mercado, en_shell=True)
