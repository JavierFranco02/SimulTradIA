"""Pantallas de administración (secciones del shell, solo visibles para administradores)."""
from simultradia.iu.admin.activos_controller import ActivosAdminController
from simultradia.iu.admin.activos_view import ActivosAdminView
from simultradia.iu.admin.ingesta_controller import IngestaController
from simultradia.iu.admin.ingesta_view import IngestaView
from simultradia.iu.admin.usuarios_controller import UsuariosController
from simultradia.iu.admin.usuarios_view import UsuariosView


def _usuarios(padre, nav):
    vista = UsuariosView(padre)
    UsuariosController(vista, nav.servicios.usuario_admin, nav.session).cargar()
    return vista


def _activos(padre, nav):
    vista = ActivosAdminView(padre)
    ActivosAdminController(vista, nav.servicios.activo_admin, nav.servicios.fuente_admin,
                           nav.session).cargar()
    return vista


def _ingesta(padre, nav):
    vista = IngestaView(padre)
    IngestaController(vista, nav.servicios.ingesta, nav.servicios.fuente_admin, nav.session).cargar()
    return vista


def registrar(navegador) -> None:
    navegador.registrar("admin_usuarios", _usuarios, en_shell=True)
    navegador.registrar("admin_activos", _activos, en_shell=True)
    navegador.registrar("admin_ingesta", _ingesta, en_shell=True)
