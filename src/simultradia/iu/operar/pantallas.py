"""Sección "operar" (dentro del shell): ticket de orden, gráfico, posiciones e historial.

Se puede abrir con un activo ya elegido: navegador.ir_a("operar", id_activo=5) (así lo hace Mercado).
"""
from simultradia.iu.mercado.grafico_controller import GraficoController
from simultradia.iu.operar.operar_controller import OperarController
from simultradia.iu.operar.operar_view import OperarView


def _operar(padre, nav, id_activo=None):
    vista = OperarView(padre)
    grafico = GraficoController(vista.grafico, nav.servicios.mercado, nav.servicios.grafico)
    OperarController(vista, nav.servicios.operar, nav.servicios.mercado, nav.session,
                     al_elegir_activo=grafico.mostrar_activo).cargar(id_activo)
    grafico.cargar()
    return vista


def registrar(navegador) -> None:
    navegador.registrar("operar", _operar, en_shell=True)
