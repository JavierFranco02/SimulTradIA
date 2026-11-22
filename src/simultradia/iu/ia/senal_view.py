"""Pestaña «Volatilidad»: cuánto se espera que se mueva el activo mañana, en qué nivel está y qué datos lo explican.

De arriba abajo, en secciones con borde: la conclusión (nivel, rango esperado e intervalo) con el gráfico de los
últimos días, tres cuadros (hoy, lo normal, umbrales) y los datos que más pesaron junto a cómo se puede usar. Vista pasiva: IAController le entrega la predicción vigente.
"""
import ttkbootstrap as ttk

from simultradia.domain.enums import NivelVolatilidad as N
from simultradia.iu.components import BarList, FigureView, ScrollFrame, Seccion
from simultradia.iu.formato import precio
from simultradia.iu.ia import textos
from simultradia.iu.ia.graficos import dibujar_ultimos_dias
from simultradia.iu.styles import Colors, Fonts, Palette, Spacing

_ESTILO = {N.BAJA: Colors.INFO, N.NORMAL: Colors.PRIMARY, N.ALTA: Colors.WARNING}   # ni verde ni rojo
_ANCHO_RESUMEN = 260      # ancho del texto del resumen de la izquierda, en píxeles


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

        ttk.Label(c, text=textos.explicacion_rango(), font=Fonts.SMALL, wraplength=900, justify="left").pack(
            anchor="w", pady=(0, Spacing.SM))
        resumen = ttk.Frame(c)
        resumen.pack(fill="x", pady=(0, Spacing.MD))
        self._nivel, self._frase = self._tarjeta(resumen, 0, "Mañana se espera un día", Fonts.DISPLAY)
        self._rango, self._intervalo = self._tarjeta(resumen, 1, "Rango esperado (máximo − mínimo)", Fonts.DISPLAY)
        self._veces, self._normal = self._tarjeta(resumen, 2, "Frente a lo normal", Fonts.DISPLAY)

        conclusion = Seccion(c, "Últimos 30 días y mañana", "Cada barra es cuánto se movió el precio ese día.")
        conclusion.pack(fill="x", pady=(0, Spacing.MD))
        self._grafico = FigureView(conclusion.cuerpo, dibujar_ultimos_dias, alto=260)
        self._grafico.pack(fill="x")
        self._referencia = ttk.Label(conclusion.cuerpo, text="", font=Fonts.SMALL)
        self._referencia.pack(anchor="w", pady=(Spacing.SM, 0))

        tres = ttk.Frame(c)
        tres.pack(fill="x", pady=(0, Spacing.MD))
        self._cuadros = []
        for columna, titulo in enumerate(("Hoy se movió", "Lo normal", "Umbrales")):
            tres.columnconfigure(columna, weight=1, uniform="cuadro")
            seccion = Seccion(tres, titulo, "", ancho_texto=260)
            seccion.grid(row=0, column=columna, sticky="nsew", padx=(0 if columna == 0 else Spacing.SM, 0))
            valor = ttk.Label(seccion.cuerpo, text="", font=Fonts.VALUE)
            valor.pack(anchor="w")
            detalle = ttk.Label(seccion.cuerpo, text="", font=Fonts.SMALL, wraplength=260, justify="left")
            detalle.pack(anchor="w", pady=(Spacing.XS, 0))
            self._cuadros.append((valor, detalle))

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

        self._seccion_uso = Seccion(c, "Cómo se puede usar", "")
        self._seccion_uso.pack(fill="x", pady=(Spacing.MD, 0))
        self._usos = []
        for _ in range(3):
            etiqueta = ttk.Label(self._seccion_uso.cuerpo, text="", font=Fonts.BODY, wraplength=900, justify="left")
            etiqueta.pack(anchor="w", pady=(0, Spacing.XS))
            self._usos.append(etiqueta)

    @staticmethod
    def _tarjeta(fila, columna: int, titulo: str, fuente):
        """Una tarjetita del resumen: título, cifra grande y una línea de apoyo. Va al lado de las otras."""
        fila.columnconfigure(columna, weight=1, uniform="resumen")
        seccion = Seccion(fila, titulo, "", ancho_texto=_ANCHO_RESUMEN)
        seccion.grid(row=0, column=columna, sticky="nsew", padx=(0 if columna == 0 else Spacing.SM, 0))
        cifra = ttk.Label(seccion.cuerpo, text="", font=fuente)
        cifra.pack(anchor="w")
        apoyo = ttk.Label(seccion.cuerpo, text="", font=Fonts.SMALL, wraplength=_ANCHO_RESUMEN, justify="left")
        apoyo.pack(anchor="w", pady=(Spacing.XS, 0))
        return cifra, apoyo

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
        self._veces.configure(text=textos.numero(p.veces_lo_normal, 1) + "×")
        self._normal.configure(text="Lo normal (promedio de %s) es %s." % (textos.dias(20), textos.rango(p.rango_normal)))
        self._frase.configure(text=textos.frase_percentil(p.nivel))
        self._referencia.configure(text="Precio de referencia %s · se comprueba el %s"
                                   % (precio(p.precio_referencia), textos.fecha(p.fecha_objetivo)))
        self._nivel.configure(text=textos.titulo_nivel(p.nivel), bootstyle=_ESTILO[p.nivel])
        self._grafico.mostrar(list(detalle.rangos_recientes), p, list(detalle.fechas_recientes))
        (v1, d1), (v2, d2), (v3, d3) = self._cuadros
        v1.configure(text=textos.rango(p.rango_hoy))
        d1.configure(text=textos.frase_hoy(p))
        v2.configure(text=textos.rango(p.rango_normal))
        d2.configure(text="Promedio de los últimos %s." % textos.dias(20))
        v3.configure(text="%s · %s" % (textos.rango(p.umbral_bajo), textos.rango(p.umbral_alto)))
        d3.configure(text=textos.texto_umbrales(p))
        for etiqueta, texto in zip(self._usos, (textos.uso_tamano(p), textos.uso_stop(p), textos.uso_direccion())):
            etiqueta.configure(text=texto)
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
