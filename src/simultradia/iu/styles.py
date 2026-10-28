"""Estilos reutilizables de TODA la interfaz.

Regla: ningún archivo de pantalla o componente escribe una fuente, un color o un
espaciado "a mano". Siempre usa estas clases. Así, para cambiar el aspecto de
la app se edita un solo lugar: este archivo.

  - Cambiar la fuente de toda la app       ->  Fonts.FAMILY
  - Cambiar el tamaño o peso de un rol     ->  Fonts._ROLES
  - Cambiar un color o un espaciado        ->  Colors / Spacing
  - Cambiar los colores del gráfico/tabla  ->  Palette
"""
import tkinter.font as tkfont

import ttkbootstrap as ttk


class Colors:
    """Nombres de color de ttkbootstrap (se usan con bootstyle=Colors.X)."""
    PRIMARY = "primary"
    MUTED = "secondary"
    SUCCESS = "success"
    DANGER = "danger"
    WARNING = "warning"


class Palette:
    """Colores y tamaños para lo que NO es un widget de ttkbootstrap: el gráfico (matplotlib)
    y las etiquetas de la tabla. Van acordes al tema oscuro `darkly`."""
    ALZA = "#00bc8c"                 # verde: sube
    BAJA = "#e74c3c"                 # rojo: baja
    FONDO = "#222222"
    GRILLA = "#444444"
    TEXTO = "#adb5bd"
    SMA = "#f39c12"
    EMA = "#3498db"
    BOLLINGER = "#9b59b6"
    RSI = "#f1c40f"
    MACD = "#3498db"
    SENAL = "#f39c12"
    TAMANO_TEXTO = 8                 # tamaño de letra dentro del gráfico


class ButtonStyle:
    """Aspectos de botón de ttkbootstrap."""
    PRIMARY = "primary"
    LINK = "link"                    # parece un enlace de texto
    DANGER_OUTLINE = "danger-outline"
    SUCCESS_OUTLINE = "success-outline"
    TOGGLE = "outline-toolbutton"    # botón que queda "hundido" al elegirlo (pestañas, filtros)
    SWITCH = "round-toggle"          # interruptor deslizante (encendido/apagado)


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

    DISPLAY = "simultradia.display"  # cifras grandes (el precio del gráfico)
    TITLE = "simultradia.title"
    HEADING = "simultradia.heading"
    SUBTITLE = "simultradia.subtitle"
    BODY = "simultradia.body"
    SMALL = "simultradia.small"

    # (tamaño, peso) de cada rol
    _ROLES = {
        DISPLAY: (24, "bold"),
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
        for widget in ("TButton", "TCheckbutton", "TRadiobutton"):
            estilo.configure(widget, font=cls.BODY)
