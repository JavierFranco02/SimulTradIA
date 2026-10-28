"""Administración · Usuarios: buscar, activar o desactivar cuentas y restablecer contraseñas."""
import tkinter as tk
from tkinter import messagebox
from typing import Callable, Dict, List, NamedTuple, Optional, Tuple

import ttkbootstrap as ttk

from simultradia.domain.entities.usuario_entity import Usuario
from simultradia.iu.base.panel_view import PanelView
from simultradia.iu.components import ActionButton, DataTable, SelectField
from simultradia.iu.formato import fecha_hora
from simultradia.iu.styles import ButtonStyle, Fonts, Spacing

_COLUMNAS = (
    ("nombre", "Nombre", 160, "w"),
    ("email", "Email", 220, "w"),
    ("rol", "Rol", 80, "center"),
    ("estado", "Estado", 100, "center"),
    ("password", "Contraseña", 100, "center"),
    ("ultimo", "Último acceso", 130, "center"),
    ("creado", "Creado", 130, "center"),
)


class _Fila(NamedTuple):
    nombre: str
    activo: bool
    es_admin: bool


class UsuariosView(PanelView):
    def __init__(self, parent):
        super().__init__(parent, "Usuarios", "Quién puede entrar al simulador")
        self._al_filtrar: Optional[Callable[[], None]] = None
        self._al_cambiar_estado: Optional[Callable[[int, bool], None]] = None
        self._al_restablecer: Optional[Callable[[int], None]] = None
        self._filas: Dict[str, _Fila] = {}

        filtros = ttk.Frame(self)
        filtros.pack(fill="x", pady=(0, Spacing.SM))
        ttk.Label(filtros, text="Buscar", font=Fonts.BODY).pack(side="left", padx=(0, Spacing.SM))
        self._busqueda = tk.StringVar(master=self)
        ttk.Entry(filtros, textvariable=self._busqueda, width=28, font=Fonts.BODY).pack(side="left")
        self._busqueda.trace_add("write", lambda *_args: self._pulsar_filtrar())
        self._rol = SelectField(filtros, None, [("todos", "Todos los roles"), ("usuario", "Usuarios"),
                                                ("admin", "Administradores")], ancho=18)
        self._rol.pack(side="left", padx=(Spacing.MD, 0))
        self._rol.al_cambiar(self._pulsar_filtrar)
        self._estado = SelectField(filtros, None, [("todos", "Cualquier estado"), ("activos", "Activos"),
                                                   ("desactivados", "Desactivados")], ancho=18)
        self._estado.pack(side="left", padx=(Spacing.SM, 0))
        self._estado.al_cambiar(self._pulsar_filtrar)

        barra = ttk.Frame(self)
        barra.pack(fill="x", pady=(0, Spacing.SM))
        self._boton = ActionButton(barra, "Selecciona un usuario", self._pulsar_cambiar)
        self._boton.pack(side="left")
        self._boton.configure(state="disabled")
        self._boton_password = ActionButton(barra, "Restablecer contraseña", self._pulsar_restablecer,
                                            estilo=ButtonStyle.DANGER_OUTLINE)
        self._boton_password.pack(side="left", padx=(Spacing.SM, 0))
        self._boton_password.configure(state="disabled")

        self._tabla = DataTable(self, _COLUMNAS)
        self._tabla.pack(fill="both", expand=True)
        self._tabla.al_seleccionar(lambda _iid: self._actualizar_botones())

    def vincular_acciones(self, al_filtrar: Callable[[], None],
                          al_cambiar_estado: Callable[[int, bool], None],
                          al_restablecer: Callable[[int], None]) -> None:
        self._al_filtrar = al_filtrar
        self._al_cambiar_estado = al_cambiar_estado
        self._al_restablecer = al_restablecer

    # --------------------------------------------- lo que el controlador lee
    def filtros(self) -> Tuple[str, Optional[str], Optional[bool]]:
        """(texto buscado, rol o None, estado de la cuenta como True/False o None)."""
        rol = self._rol.obtener()
        estado = self._estado.obtener()
        return (self._busqueda.get(), None if rol in (None, "todos") else rol,
                {"activos": True, "desactivados": False}.get(estado))

    def confirmar(self, mensaje: str) -> bool:
        return messagebox.askyesno("Confirmar", mensaje, parent=self)

    # ------------------------------------------- lo que el controlador ordena
    def mostrar_usuarios(self, usuarios: List[Usuario]) -> None:
        self.establecer_subtitulo("%d usuarios · %d con la cuenta activa · %d administradores" % (
            len(usuarios), sum(1 for u in usuarios if u.activo), sum(1 for u in usuarios if u.es_admin)))
        self._filas = {str(u.id_usuario): _Fila(u.nombre, u.activo, u.es_admin) for u in usuarios}
        self._tabla.establecer_filas([
            (str(u.id_usuario),
             (u.nombre, u.email, "Admin" if u.es_admin else "Usuario",
              "Activo" if u.activo else "Desactivado",
              "Temporal" if u.debe_cambiar_password else "—",
              fecha_hora(u.ultimo_login_en), fecha_hora(u.creado_en)),
             "" if u.activo else "baja")
            for u in usuarios
        ])
        self._actualizar_botones()

    def mostrar_contrasena_temporal(self, id_usuario: int, password: str) -> None:
        """Muestra la contraseña temporal UNA vez (después solo existe su hash) y la copia al portapapeles."""
        fila = self._filas.get(str(id_usuario))
        self.clipboard_clear()
        self.clipboard_append(password)
        messagebox.showinfo(
            "Contraseña temporal",
            "Contraseña temporal de %s:\n\n%s\n\nYa está copiada al portapapeles. Entrégasela a la persona: "
            "no se volverá a mostrar. Al iniciar sesión tendrá que elegir una contraseña nueva."
            % (fila.nombre if fila else "la cuenta", password), parent=self)

    # --------------------------------------------------------------- botones
    def _actualizar_botones(self) -> None:
        iid = self._tabla.seleccionado()
        fila = self._filas.get(iid) if iid is not None else None
        if fila is None:
            self._boton.configure(state="disabled", text="Selecciona un usuario", bootstyle=ButtonStyle.PRIMARY)
        elif fila.activo:
            self._boton.configure(state="normal", text="Desactivar cuenta", bootstyle=ButtonStyle.DANGER_OUTLINE)
        else:
            self._boton.configure(state="normal", text="Reactivar cuenta", bootstyle=ButtonStyle.SUCCESS_OUTLINE)
        # A los administradores no se les restablece la contraseña desde aquí.
        self._boton_password.configure(state="normal" if fila is not None and not fila.es_admin else "disabled")

    def _pulsar_filtrar(self) -> None:
        if self._al_filtrar:
            self._al_filtrar()

    def _pulsar_cambiar(self) -> None:
        iid = self._tabla.seleccionado()
        if iid is not None and self._al_cambiar_estado:
            self._al_cambiar_estado(int(iid), not self._filas[iid].activo)

    def _pulsar_restablecer(self) -> None:
        iid = self._tabla.seleccionado()
        if iid is not None and self._al_restablecer:
            self._al_restablecer(int(iid))
