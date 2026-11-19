"""Pestaña «Evaluación»: qué tan bien habría acertado el modelo en el pasado, con el mismo rigor que se usa para activarlo.

Es del modelo (no de un activo). Todo viene de la validación walk-forward guardada al entrenar.
"""
from typing import Optional

import ttkbootstrap as ttk

from simultradia.domain.entities.modelo_ia_entity import ModeloIA
from simultradia.domain.reglas.prediccion import CLASES, TRAMOS_VALIDACION, Z_MINIMO
from simultradia.ia.entrenamiento import Evaluacion
from simultradia.ia.serializacion import desde_dict
from simultradia.iu.components import BarList, DataTable, FigureView, MetricGrid, ScrollFrame, Seccion
from simultradia.iu.formato import fecha_hora
from simultradia.iu.ia import textos
from simultradia.iu.ia.graficos import dibujar_tramos
from simultradia.iu.styles import Colors, Fonts, Palette, Spacing

_COLUMNAS_CALIBRACION = (
    ("rango", "Confianza", 110, "w"),
    ("n", "Predicciones", 110, "e"),
    ("acierto", "Acierto", 90, "e"),
    ("media", "Confianza media", 130, "e"),
)
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
        self._veredicto = ttk.Label(c, text="", font=Fonts.HEADING)
        self._veredicto.pack(anchor="w")
        self._lectura = ttk.Label(c, text="", font=Fonts.BODY, wraplength=900, justify="left")
        self._lectura.pack(anchor="w", pady=(Spacing.XS, Spacing.MD))
        self._metricas = MetricGrid(c, columnas=4)
        self._metricas.pack(fill="x", pady=(0, Spacing.SM))

        cuerpo = _seccion(c, "Acierto por periodo",
                          "La prueba se repite en %d periodos seguidos del pasado, cada uno con datos que el modelo "
                          "no había visto al entrenarse. Una barra verde más alta que la gris es que le ganó a la base."
                          % TRAMOS_VALIDACION)
        self._tramos = FigureView(cuerpo, dibujar_tramos, alto=230)
        self._tramos.pack(fill="x")

        cuerpo = _seccion(c, "¿Acierta más cuando está más seguro?",
                          "Se agrupan las predicciones por su confianza. Si el modelo es honesto, el acierto sube "
                          "con la confianza.")
        self._calibracion = DataTable(cuerpo, _COLUMNAS_CALIBRACION, alto=5)
        self._calibracion.pack(fill="x")
        self._lectura_calibracion = ttk.Label(cuerpo, text="", font=Fonts.BODY, wraplength=900, justify="left")
        self._lectura_calibracion.pack(anchor="w", pady=(Spacing.SM, 0))

        cuerpo = _seccion(c, "Qué acierta y en qué se equivoca",
                          "Cada fila es lo que pasó de verdad y cada columna lo que dijo el modelo. En verde, "
                          "lo que acertó; el resto son confusiones.")
        self._confusion = ttk.Frame(cuerpo)
        self._confusion.pack(anchor="w")

        cuerpo = _seccion(c, "Qué datos usa más el modelo",
                          "Qué parte de sus decisiones se apoya en cada dato (los %d más importantes)."
                          % _IMPORTANCIAS_VISIBLES)
        self._importancias = BarList(cuerpo, ancho_texto=24, ancho_valor=6)
        self._importancias.pack(fill="x")

    def mostrar(self, modelo: ModeloIA) -> None:
        if modelo.id_modelo == self._id_mostrado:
            return              # el refresco periódico no debe redibujar lo mismo
        self._id_mostrado = modelo.id_modelo
        ev: Evaluacion = desde_dict(modelo.metricas)
        entrenado = fecha_hora(modelo.entrenado_en) if modelo.entrenado_en else "—"
        self._modelo.configure(text="%s · entrenado el %s" % (textos.nombre_modelo(ev.horizonte, modelo.version), entrenado))
        self._veredicto.configure(text=ev.veredicto, bootstyle=Colors.SUCCESS if ev.supera_base else Colors.DANGER)
        self._lectura.configure(text=textos.lectura_validacion(ev))
        mejores, comparables = ev.activos_mejores
        self._metricas.establecer([
            ("Acierto del modelo", textos.pct(ev.acierto, 1)),
            ("Acierto de la base", textos.pct(ev.base, 1)),
            ("Ventaja", textos.numero(ev.ventaja, 1, con_signo=True) + " pp",
             Colors.SUCCESS if ev.ventaja > 0 else Colors.DANGER),
            ("Estadístico z (mín. %s)" % textos.numero(Z_MINIMO), textos.numero(ev.z)),
            ("AUC", textos.numero(ev.auc, 3) if ev.auc is not None else "—"),
            ("Días evaluados", str(int(round(ev.dias_efectivos * ev.horizonte)))),
            ("Predicciones de prueba", "{:,}".format(ev.n_prueba).replace(",", " ")),
            ("Activos sobre su base", "%d de %d" % (mejores, comparables)),
        ])
        self._tramos.mostrar(ev)
        self._calibracion.establecer_filas([
            (str(i), (b.etiqueta, str(b.n), textos.pct(b.acierto) if b.n else "—",
                      textos.pct(b.confianza) if b.n else "—"), "")
            for i, b in enumerate(ev.calibracion)])
        self._lectura_calibracion.configure(text=textos.lectura_calibracion(ev.calibracion))
        self._dibujar_confusion(ev)
        mayor = max(ev.importancias.values(), default=0.0) or 1.0
        mas_importantes = sorted(ev.importancias.items(), key=lambda p: -p[1])[:_IMPORTANCIAS_VISIBLES]
        self._importancias.establecer([(textos.factor(n), v / mayor, Palette.EMA, textos.pct(v))
                                       for n, v in mas_importantes])

    def _dibujar_confusion(self, ev: Evaluacion) -> None:
        for hijo in self._confusion.winfo_children():
            hijo.destroy()
        nombres = [c.capitalize() for c in CLASES]
        ttk.Label(self._confusion, text="Lo que dijo el modelo", font=Fonts.SMALL).grid(
            row=0, column=1, columnspan=3, pady=(0, 2))
        for columna, nombre in enumerate(nombres):
            ttk.Label(self._confusion, text=nombre, font=Fonts.BODY, width=14, anchor="center").grid(
                row=1, column=columna + 1)
        ttk.Label(self._confusion, text="Lo que pasó", font=Fonts.SMALL).grid(
            row=1, column=0, sticky="w", padx=(0, Spacing.MD))
        for fila, nombre in enumerate(nombres):
            ttk.Label(self._confusion, text="Fue " + nombre.lower(), font=Fonts.BODY).grid(
                row=fila + 2, column=0, sticky="w", padx=(0, Spacing.MD))
            total = sum(ev.confusion[fila]) or 1
            for columna in range(3):
                celda = ttk.Label(self._confusion, font=Fonts.VALUE, width=14, anchor="center", text="%s (%s)" % (
                    "{:,}".format(ev.confusion[fila][columna]).replace(",", " "),
                    textos.pct(ev.confusion[fila][columna] / total)))
                if fila == columna:
                    celda.configure(bootstyle=Colors.SUCCESS)       # los aciertos están en la diagonal
                celda.grid(row=fila + 2, column=columna + 1, pady=2)
