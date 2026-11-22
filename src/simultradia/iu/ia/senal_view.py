"""Pestaña «Volatilidad»: cuánto se espera que se mueva el activo mañana, en qué nivel está y qué datos lo explican.

De arriba abajo, en secciones con borde: la conclusión (rango esperado, nivel e intervalo), la comparación con lo de
hoy y lo normal, y los datos que más pesaron. Vista pasiva: IAController le entrega la predicción vigente.
"""
import ttkbootstrap as ttk

from simultradia.domain.enums import NivelVolatilidad as N
from simultradia.iu.components import BarList, MetricGrid, ScrollFrame, Seccion
from simultradia.iu.formato import precio
from simultradia.iu.ia import textos
from simultradia.iu.styles import Colors, Fonts, Palette, Spacing

_ESTILO = {N.BAJA: Colors.INFO, N.NORMAL: Colors.PRIMARY, N.ALTA: Colors.WARNING}   # ni verde ni rojo


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

        conclusion = Seccion(c, "Qué se espera para el próximo día", textos.explicacion_rango())
        conclusion.pack(fill="x", pady=(0, Spacing.MD))
        fila = ttk.Frame(conclusion.cuerpo)         # la sección empaqueta (pack): la cuadrícula va en un marco propio
        fila.pack(fill="x")
        fila.columnconfigure(0, weight=1)
        izquierda = ttk.Frame(fila)
        izquierda.grid(row=0, column=0, sticky="nw")
        ttk.Label(izquierda, text="RANGO ESPERADO", font=Fonts.SMALL).pack(anchor="w")
        self._rango = ttk.Label(izquierda, text="", font=Fonts.DISPLAY)
        self._rango.pack(anchor="w")
        self._intervalo = ttk.Label(izquierda, text="", font=Fonts.SUBTITLE)
        self._intervalo.pack(anchor="w")
        self._frase = ttk.Label(izquierda, text="", font=Fonts.BODY, wraplength=520, justify="left")
        self._frase.pack(anchor="w", pady=(Spacing.XS, 0))
        self._referencia = ttk.Label(izquierda, text="", font=Fonts.SMALL)
        self._referencia.pack(anchor="w", pady=(Spacing.XS, 0))
        derecha = ttk.Frame(fila)
        derecha.grid(row=0, column=1, sticky="ne", padx=(Spacing.LG, Spacing.MD))
        ttk.Label(derecha, text="NIVEL", font=Fonts.SMALL).pack(anchor="e")
        self._nivel = ttk.Label(derecha, text="", font=Fonts.DISPLAY)
        self._nivel.pack(anchor="e")
        self._veces = ttk.Label(derecha, text="", font=Fonts.SUBTITLE)
        self._veces.pack(anchor="e")

        comparacion = Seccion(c, "Comparación", textos.explicacion_nivel())
        comparacion.pack(fill="x", pady=(0, Spacing.MD))
        self._metricas = MetricGrid(comparacion.cuerpo, columnas=4)
        self._metricas.pack(fill="x")

        self._seccion_factores = Seccion(c, "Qué datos pesaron en esta predicción", "")
        self._seccion_factores.pack(fill="x")
        cuerpo = self._seccion_factores.cuerpo
        ttk.Label(cuerpo, font=Fonts.SMALL, wraplength=900, justify="left",
                  text="A la derecha (azul): el dato empuja a esperar un día MÁS agitado. "
                       "A la izquierda (naranja): a esperar uno más tranquilo.").pack(anchor="w", pady=(0, Spacing.XS))
        self._factores = BarList(cuerpo, centrada=True, ancho_texto=28)
        self._sin_factores = ttk.Label(cuerpo, text="Los factores no están disponibles para esta predicción.",
                                       font=Fonts.BODY)
        self._factores.pack(fill="x")

    def limpiar(self, texto: str = "Elige un activo del escáner.") -> None:
        self._marco.pack_forget()
        self._mensaje.configure(text=texto)
        self._mensaje.pack(expand=True)

    def mostrar(self, ticker: str, nombre: str, detalle) -> None:
        p = detalle.vigente
        if p is None:
            self.limpiar("Este activo no tiene una predicción vigente.")
            return
        self._mensaje.pack_forget()
        self._marco.pack(fill="both", expand=True)
        self._ticker.configure(text=ticker)
        self._nombre.configure(text=nombre)
        self._rango.configure(text=textos.rango(p.rango_predicho))
        self._intervalo.configure(text=textos.frase_intervalo(p))
        self._frase.configure(text="%s %s" % (textos.frase_nivel(p.nivel), textos.frase_normal(p)))
        self._referencia.configure(text="Precio de referencia %s · se comprueba el %s"
                                   % (precio(p.precio_referencia), textos.fecha(p.fecha_objetivo)))
        self._nivel.configure(text=textos.nivel(p.nivel).upper(), bootstyle=_ESTILO[p.nivel])
        self._veces.configure(text=textos.veces(p.veces_lo_normal))
        self._metricas.establecer([
            ("Rango esperado", textos.rango(p.rango_predicho)),
            ("Rango de hoy", textos.rango(p.rango_hoy)),
            ("Promedio de 20 días", textos.rango(p.rango_normal)),
            ("Umbral baja / alta", "%s / %s" % (textos.rango(p.umbral_bajo), textos.rango(p.umbral_alto))),
        ])
        self._mostrar_factores(detalle.vigente.factores)

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
