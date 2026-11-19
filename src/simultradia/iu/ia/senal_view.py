"""Pestaña «Señal»: hacia dónde va el activo según la IA, con qué probabilidad y qué datos lo empujan.

De arriba abajo, en secciones con borde: la conclusión (con su confianza), los tres escenarios posibles (el elegido
resaltado, con el azar como referencia) y los datos que más pesaron. Vista pasiva: IAController le entrega la predicción vigente.
"""
import ttkbootstrap as ttk

from simultradia.domain.enums import DireccionPrediccion as D
from simultradia.iu.components import BarList, Card, Medidor, ScrollFrame, Seccion
from simultradia.iu.formato import precio
from simultradia.iu.ia import textos
from simultradia.iu.styles import Colors, Fonts, Palette, Spacing

_COLOR = {D.ALCISTA: Palette.ALZA, D.BAJISTA: Palette.BAJA, D.LATERAL: Palette.TEXTO}
_ESTILO = {D.ALCISTA: Colors.SUCCESS, D.BAJISTA: Colors.DANGER}
_ORDEN = (D.BAJISTA, D.LATERAL, D.ALCISTA)           # de izquierda a derecha, como una escala


class _Escenario(Card):
    """Una de las tres tarjetas: nombre, probabilidad grande, barra y qué significa."""

    def __init__(self, parent, direccion: D):
        super().__init__(parent)
        self._direccion = direccion
        c = self.cuerpo
        ttk.Label(c, text=textos.direccion(direccion).upper(), font=Fonts.SMALL).pack(anchor="w")
        self._valor = ttk.Label(c, text="", font=Fonts.DISPLAY)
        self._valor.pack(anchor="w")
        self._barra = Medidor(c, marca=textos.AZAR)
        self._barra.pack(fill="x", pady=Spacing.XS)
        ttk.Label(c, text=textos.escenario_corto(direccion), font=Fonts.BODY).pack(anchor="w")

    def establecer(self, probabilidad: float, elegido: bool) -> None:
        self._valor.configure(text=textos.pct(probabilidad))
        self._barra.establecer(probabilidad, _COLOR[self._direccion])
        self.configure(bootstyle=_ESTILO.get(self._direccion, Colors.PRIMARY) if elegido else Colors.MUTED)


class SenalView(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=Spacing.MD)
        ttk.Label(self, text=textos.AVISO, font=Fonts.SMALL).pack(side="bottom", anchor="w", pady=(Spacing.SM, 0))
        self._mensaje = ttk.Label(self, text="Elige un activo del escáner.", font=Fonts.SUBTITLE)
        self._mensaje.pack(expand=True)
        self._marco = ScrollFrame(self, padding=0)
        c = self._marco.cuerpo

        self._ticker = ttk.Label(c, text="", font=Fonts.HEADING)
        self._ticker.pack(anchor="w")
        self._nombre = ttk.Label(c, text="", font=Fonts.SUBTITLE)
        self._nombre.pack(anchor="w", pady=(0, Spacing.MD))

        conclusion = Seccion(c, "Conclusión de la IA")
        conclusion.pack(fill="x", pady=(0, Spacing.MD))
        fila = ttk.Frame(conclusion.cuerpo)         # la sección empaqueta (pack): la cuadrícula va en un marco propio
        fila.pack(fill="x")
        fila.columnconfigure(0, weight=1)
        izquierda = ttk.Frame(fila)
        izquierda.grid(row=0, column=0, sticky="nw")
        self._direccion = ttk.Label(izquierda, text="", font=Fonts.DISPLAY)
        self._direccion.pack(anchor="w")
        self._frase = ttk.Label(izquierda, text="", font=Fonts.SUBTITLE, wraplength=560, justify="left")
        self._frase.pack(anchor="w")
        self._referencia = ttk.Label(izquierda, text="", font=Fonts.SMALL)
        self._referencia.pack(anchor="w", pady=(Spacing.XS, 0))
        derecha = ttk.Frame(fila)
        derecha.grid(row=0, column=1, sticky="ne", padx=(Spacing.LG, Spacing.MD))
        ttk.Label(derecha, text="CONFIANZA", font=Fonts.SMALL).pack(anchor="e")
        self._nivel = ttk.Label(derecha, text="", font=Fonts.DISPLAY)
        self._nivel.pack(anchor="e")
        self._confianza = ttk.Label(derecha, text="", font=Fonts.SUBTITLE)
        self._confianza.pack(anchor="e")
        self._azar = ttk.Label(derecha, text="", font=Fonts.SMALL, wraplength=240, justify="right")
        self._azar.pack(anchor="e", pady=(Spacing.XS, 0))

        escenarios = Seccion(c, "Los tres escenarios posibles",
                             "La marca vertical de cada barra es el azar (%s). %s" % (
                                 textos.pct(textos.AZAR), textos.explicacion_escenarios()))
        escenarios.pack(fill="x", pady=(0, Spacing.MD))
        fila = ttk.Frame(escenarios.cuerpo)
        fila.pack(fill="x")
        self._escenarios = {}
        for columna, d in enumerate(_ORDEN):
            fila.columnconfigure(columna, weight=1, uniform="escenario")
            self._escenarios[d] = _Escenario(fila, d)
            self._escenarios[d].grid(row=0, column=columna, sticky="nsew",
                                     padx=(0 if columna == 0 else Spacing.SM, 0))

        self._seccion_factores = Seccion(c, "Qué datos pesaron en esta predicción", "")
        self._seccion_factores.pack(fill="x")
        cuerpo = self._seccion_factores.cuerpo
        self._ayuda_factores = ttk.Label(cuerpo, text="", font=Fonts.SMALL, wraplength=900, justify="left")
        self._ayuda_factores.pack(anchor="w", pady=(0, Spacing.XS))
        self._factores = BarList(cuerpo, centrada=True, ancho_texto=24)
        self._sin_factores = ttk.Label(cuerpo, text="Los factores no están disponibles para esta predicción.",
                                       font=Fonts.BODY)
        self._factores.pack(fill="x")

    def limpiar(self, texto: str = "Elige un activo del escáner.") -> None:
        self._marco.pack_forget()
        self._mensaje.configure(text=texto)
        self._mensaje.pack(expand=True)

    def mostrar(self, ticker: str, nombre: str, horizonte: int, detalle) -> None:
        p = detalle.vigente
        if p is None:
            self.limpiar("Este activo no tiene una predicción vigente a %s." % textos.dias(horizonte))
            return
        self._mensaje.pack_forget()
        self._marco.pack(fill="both", expand=True)
        self._ticker.configure(text=ticker)
        self._nombre.configure(text=nombre)
        estilo = _ESTILO.get(p.direccion)
        self._direccion.configure(text=textos.direccion(p.direccion).upper(),
                                  **({"bootstyle": estilo} if estilo else {"style": "TLabel"}))
        self._frase.configure(text=textos.frase_direccion(p.direccion, horizonte))
        self._nivel.configure(text=textos.nivel_confianza(p.confianza),
                              bootstyle=Colors.WARNING if p.confianza < 0.45 else Colors.PRIMARY)
        self._confianza.configure(text=textos.pct(p.confianza))
        self._azar.configure(text=textos.frase_confianza(p.confianza))
        self._referencia.configure(text="Precio de referencia %s · se comprueba el %s"
                                   % (precio(p.precio_referencia), textos.fecha(p.fecha_objetivo)))
        for d, probabilidad in ((D.BAJISTA, p.prob_bajista), (D.LATERAL, p.prob_lateral),
                                (D.ALCISTA, p.prob_alcista)):
            self._escenarios[d].establecer(probabilidad, d == p.direccion)
        self._ayuda_factores.configure(
            text="Datos que más influyeron para decir «%s». A la derecha (azul): el dato apoya ese escenario. "
                 "A la izquierda (naranja): va en contra." % textos.direccion(p.direccion).lower())
        self._mostrar_factores(detalle.factores)

    def _mostrar_factores(self, factores) -> None:
        if not factores:
            self._factores.pack_forget()
            self._sin_factores.pack(anchor="w", pady=Spacing.SM)
            return
        self._sin_factores.pack_forget()
        self._factores.pack(fill="x")
        mayor = max(abs(aporte) for _n, aporte, _v in factores) or 1.0
        self._factores.establecer([
            (textos.factor(nombre), aporte / mayor, Palette.EMA if aporte >= 0 else Palette.SMA,
             textos.numero(aporte, 2, con_signo=True))
            for nombre, aporte, _valor in factores])
