"""Estilos reutilizables de TODA la interfaz.

Regla: ningún archivo de pantalla o componente escribe una fuente, un color o un
espaciado "a mano". Siempre usa estas clases. Así, para cambiar el aspecto de
la app se edita un solo lugar: este archivo.

  - Cambiar la fuente de toda la app       ->  Fonts.FAMILY
  - Cambiar el tamaño o peso de un rol     ->  Fonts._ROLES
  - Cambiar un color o un espaciado        ->  Colors / Spacing
"""
import tkinter.font as tkfont

import ttkbootstrap as ttk


class Colors:
    """Nombres de color de ttkbootstrap (se usan con bootstyle=Colors.X)."""
    PRIMARY = "primary"
    MUTED = "secondary"
    SUCCESS = "success"
    DANGER = "danger"


class ButtonStyle:
    """Aspectos de botón de ttkbootstrap."""
    PRIMARY = "primary"
    LINK = "link"                    # parece un enlace de texto
    DANGER_OUTLINE = "danger-outline"


class Spacing:
    """Espacios estándar, en píxeles."""
    XS = 4
    SM = 8
    MD = 12
    LG = 20


class Fonts:
    """Fuentes por ROL (título, cuerpo...). Cada rol es una "fuente con nombre" de
    Tk: si cambia su definición, todos los widgets que la usan se actualizan.

        ttk.Label(self, text="Hola", font=Fonts.TITLE)
    """
    FAMILY = "Helvetica"             # cambiar esta línea cambia la fuente de TODA la app

    TITLE = "simultradia.title"
    HEADING = "simultradia.heading"
    SUBTITLE = "simultradia.subtitle"
    BODY = "simultradia.body"
    SMALL = "simultradia.small"

    # (tamaño, peso) de cada rol
    _ROLES = {
        TITLE: (22, "bold"),
        HEADING: (18, "bold"),
        SUBTITLE: (11, "normal"),
        BODY: (10, "normal"),
        SMALL: (8, "normal"),
    }

    _creadas: dict = {}   # guarda las fuentes: si se pierde la referencia, Tk las borra

    @classmethod
    def register(cls, root) -> None:
        """Se llama UNA vez, justo después de crear la ventana principal."""
        existentes = tkfont.names(root)
        for nombre, (tamano, peso) in cls._ROLES.items():
            if nombre in existentes:
                fuente = tkfont.Font(root=root, name=nombre, exists=True)
                fuente.configure(family=cls.FAMILY, size=tamano, weight=peso)
            else:
                fuente = tkfont.Font(root=root, name=nombre, family=cls.FAMILY,
                                     size=tamano, weight=peso)
            cls._creadas[nombre] = fuente

        # Las fuentes por defecto de Tk también adoptan la familia elegida.
        tamano_cuerpo = cls._ROLES[cls.BODY][0]
        for nombre in ("TkDefaultFont", "TkTextFont", "TkMenuFont"):
            tkfont.Font(root=root, name=nombre, exists=True).configure(
                family=cls.FAMILY, size=tamano_cuerpo)

        # Los botones y casillas no aceptan "font=" directamente: la toman del estilo.
        estilo = ttk.Style()
        for widget in ("TButton", "TCheckbutton"):
            estilo.configure(widget, font=cls.BODY)
