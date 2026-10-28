"""Pantalla del módulo Mercado (sección dentro del shell): lista de activos + gráfico."""
from simultradia.iu.mercado.grafico_controller import GraficoController
from simultradia.iu.mercado.lista_controller import ListaController
from simultradia.iu.mercado.mercado_view import MercadoView


def _mercado(padre, nav):
    vista = MercadoView(padre)
    grafico = GraficoController(vista.grafico, nav.servicios.mercado, nav.servicios.grafico)
    lista = ListaController(vista.lista, nav.servicios.mercado, al_elegir_activo=grafico.mostrar_activo)
    grafico.cargar()
    lista.cargar()
    return vista


def registrar(navegador) -> None:
    navegador.registrar("mercado", _mercado, en_shell=True)
