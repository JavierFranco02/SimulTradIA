"""Pestaña «Evaluación»: qué tan bien habría predicho el modelo en el pasado, con el mismo rigor que se usa para activarlo.

Es del modelo (no de un activo). Todo viene de la validación walk-forward guardada al entrenar.
"""
from typing import Optional

import ttkbootstrap as ttk

from simultradia.domain.entities.modelo_ia_entity import ModeloIA
from simultradia.domain.reglas.volatilidad import TRAMOS_VALIDACION, Z_MINIMO
from simultradia.ia.volatilidad import Evaluacion
from simultradia.ia.volatilidad_serializacion import desde_dict
from simultradia.iu.components import BarList, FigureView, MetricGrid, ScrollFrame, Seccion
from simultradia.iu.formato import fecha_hora
from simultradia.iu.ia import textos
from simultradia.iu.ia.graficos import dibujar_calibracion, dibujar_tramos
from simultradia.iu.styles import Colors, Fonts, Palette, Spacing

_IMPORTANCIAS_VISIBLES = 8


def _seccion(padre, titulo: str, ayuda: str):
    seccion = Seccion(padre, titulo, ayuda)
    seccion.pack(fill="x", pady=(0, Spacing.MD))
    return seccion.cuerpo


class EvaluacionView(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self._id_mostrado: Optional[int] = None
        marco = ScrollFrame(self, padding=Spacing.MD)
        marco.pack(fill="both", expand=True)
        c = marco.cuerpo

        self._modelo = ttk.Label(c, text="", font=Fonts.SUBTITLE)
        self._modelo.pack(anchor="w")
        self._veredicto = ttk.Label(c, text="", font=Fonts.DISPLAY)
        self._veredicto.pack(anchor="w")
        self._lectura = ttk.Label(c, text="", font=Fonts.BODY, wraplength=900, justify="left")
        self._lectura.pack(anchor="w", pady=(Spacing.XS, Spacing.MD))

        cuerpo = _seccion(c, "1 · ¿Cuánto se equivoca?",
                          "Error medio del rango predicho, en la prueba con datos que el modelo no había visto. "
                          "Menos es mejor. Se compara con dos bases simples.")
        self._errores = BarList(cuerpo, ancho_texto=28, ancho_valor=7)
        self._errores.pack(fill="x")
        self._ejemplo = ttk.Label(cuerpo, text="", font=Fonts.SMALL, wraplength=900, justify="left")
        self._ejemplo.pack(anchor="w", pady=(Spacing.SM, 0))

        cuerpo = _seccion(c, "2 · Error por periodo",
                          "La prueba se repite en %d periodos seguidos del pasado. Una barra azul más baja que las "
                          "otras es que le ganó a las dos bases en ese periodo." % TRAMOS_VALIDACION)
        self._tramos = FigureView(cuerpo, dibujar_tramos, alto=230)
        self._tramos.pack(fill="x")
        self._ganados = ttk.Label(cuerpo, text="", font=Fonts.BODY, wraplength=900, justify="left")
        self._ganados.pack(anchor="w", pady=(Spacing.SM, 0))

        cuerpo = _seccion(c, "3 · ¿Distingue los días tranquilos de los agitados?",
                          "Se agrupan los días de prueba según lo que esperaba el modelo. Si funciona, la barra azul "
                          "(lo real) sube junto con la gris (lo esperado). 1,0× = un día habitual.")
        self._calibracion = FigureView(cuerpo, dibujar_calibracion, alto=260)
        self._calibracion.pack(fill="x")
        self._lectura_calibracion = ttk.Label(cuerpo, text="", font=Fonts.BODY, wraplength=900, justify="left")
        self._lectura_calibracion.pack(anchor="w", pady=(Spacing.SM, 0))

        cuerpo = _seccion(c, "4 · Nivel: baja, normal o alta", "Cuántas veces acertó el nivel en la prueba.")
        self._niveles = BarList(cuerpo, ancho_texto=28, ancho_valor=7)
        self._niveles.pack(fill="x")
        self._lectura_nivel = ttk.Label(cuerpo, text="", font=Fonts.BODY, wraplength=900, justify="left")
        self._lectura_nivel.pack(anchor="w", pady=(Spacing.SM, 0))

        cuerpo = _seccion(c, "5 · En qué se apoya el modelo",
                          "Qué parte de sus decisiones se apoya en cada dato (los %d más importantes)."
                          % _IMPORTANCIAS_VISIBLES)
        self._importancias = BarList(cuerpo, ancho_texto=28, ancho_valor=6)
        self._importancias.pack(fill="x")

        cuerpo = _seccion(c, "6 · Detalle técnico", "Las cifras con las que se decide activarlo.")
        self._metricas = MetricGrid(cuerpo, columnas=4)
        self._metricas.pack(fill="x")

    def mostrar(self, modelo: ModeloIA) -> None:
        if modelo.id_modelo == self._id_mostrado:
            return              # el refresco periódico no debe redibujar lo mismo
        self._id_mostrado = modelo.id_modelo
        ev: Evaluacion = desde_dict(modelo.metricas)
        entrenado = fecha_hora(modelo.entrenado_en) if modelo.entrenado_en else "—"
        self._modelo.configure(text="%s · entrenado el %s" % (textos.nombre_modelo(modelo.version), entrenado))
        dias = ev.tramos[0].inicio, ev.tramos[-1].fin
        self._veredicto.configure(text=textos.titulo_veredicto(ev),
                                  bootstyle=Colors.SUCCESS if ev.supera_base else Colors.DANGER)
        self._lectura.configure(text=textos.explicacion_veredicto(ev, *dias) if ev.tramos else "")
        mayor = max(ev.error, ev.error_hoy, ev.error_media) or 1.0
        self._errores.establecer([
            ("El modelo", ev.error / mayor, Palette.EMA, textos.error_pct(ev.error)),
            ("Repetir el rango de hoy", ev.error_hoy / mayor, Palette.TEXTO, textos.error_pct(ev.error_hoy)),
            ("Promedio de 20 días", ev.error_media / mayor, Palette.TEXTO, textos.error_pct(ev.error_media)),
        ])
        self._ejemplo.configure(text=textos.ejemplo_error(ev.error))
        self._tramos.mostrar(ev)
        self._ganados.configure(text="Le ganó a las dos bases en %d de %d periodos." % (
            textos.tramos_ganados(ev), len(ev.tramos)))
        self._calibracion.mostrar(list(ev.calibracion))
        self._lectura_calibracion.configure(text=textos.lectura_calibracion(ev.calibracion))
        self._niveles.establecer([
            ("El modelo", ev.acierto_nivel, Palette.EMA, textos.pct(ev.acierto_nivel)),
            ("Repetir el nivel de hoy", ev.acierto_nivel_hoy, Palette.TEXTO, textos.pct(ev.acierto_nivel_hoy)),
            ("Decir siempre «normal»", textos.siempre_normal(), Palette.TEXTO, textos.pct(textos.siempre_normal())),
        ])
        self._lectura_nivel.configure(text=textos.lectura_nivel(ev))
        mejores, comparables = ev.activos_mejores
        self._metricas.establecer([
            ("Mejora frente a hoy", textos.pct(ev.mejora_hoy, 1),
             Colors.SUCCESS if ev.mejora_hoy > 0 else Colors.DANGER),
            ("z contra hoy (mín. %s)" % textos.numero(Z_MINIMO), textos.numero(ev.z_hoy)),
            ("z contra el promedio", textos.numero(ev.z_media)),
            ("Correlación", textos.numero(ev.correlacion, 2) if ev.correlacion is not None else "—"),
            ("Activos sobre las dos bases", "%d de %d" % (mejores, comparables)),
            ("Días de prueba", str(ev.dias_prueba)),
        ])
        mayor = max(ev.importancias.values(), default=0.0) or 1.0
        mas_importantes = sorted(ev.importancias.items(), key=lambda p: -p[1])[:_IMPORTANCIAS_VISIBLES]
        self._importancias.establecer([(textos.factor(n), v / mayor, Palette.EMA, textos.pct(v))
                                       for n, v in mas_importantes])
