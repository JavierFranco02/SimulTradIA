"""Pestaña «Evaluación»: qué tan bien habría predicho el modelo en el pasado, con el mismo rigor que se usa para activarlo.

Es del modelo (no de un activo). Todo viene de la validación walk-forward guardada al entrenar.
"""
from typing import Optional

import ttkbootstrap as ttk

from simultradia.domain.entities.modelo_ia_entity import ModeloIA
from simultradia.domain.reglas.volatilidad import TRAMOS_VALIDACION, Z_MINIMO
from simultradia.ia.volatilidad import Evaluacion
from simultradia.ia.volatilidad_serializacion import desde_dict
from simultradia.iu.components import BarList, DataTable, FigureView, MetricGrid, ScrollFrame, Seccion
from simultradia.iu.formato import fecha_hora
from simultradia.iu.ia import textos
from simultradia.iu.ia.graficos import dibujar_tramos
from simultradia.iu.styles import Colors, Fonts, Palette, Spacing

_COLUMNAS_CALIBRACION = (
    ("grupo", "El modelo esperaba un día", 190, "w"),
    ("n", "Predicciones", 110, "e"),
    ("predicho", "Esperado", 120, "e"),
    ("real", "Real", 120, "e"),
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

        cuerpo = _seccion(c, "Error por periodo",
                          "La prueba se repite en %d periodos seguidos del pasado, con datos que el modelo no había "
                          "visto. Se compara su error con dos bases: repetir el rango de hoy y usar el promedio de "
                          "20 días. Una barra azul más baja que las otras es que les ganó." % TRAMOS_VALIDACION)
        self._tramos = FigureView(cuerpo, dibujar_tramos, alto=230)
        self._tramos.pack(fill="x")

        cuerpo = _seccion(c, "¿Distingue los días tranquilos de los agitados?",
                          "Se agrupan los días de prueba según lo que esperaba el modelo. Si funciona, «lo real» "
                          "sube junto con «lo esperado». Los valores son veces lo normal (1,0× = un día habitual).")
        self._calibracion = DataTable(cuerpo, _COLUMNAS_CALIBRACION, alto=5)
        self._calibracion.pack(fill="x")
        self._lectura_calibracion = ttk.Label(cuerpo, text="", font=Fonts.BODY, wraplength=900, justify="left")
        self._lectura_calibracion.pack(anchor="w", pady=(Spacing.SM, 0))

        cuerpo = _seccion(c, "Nivel: baja, normal o alta", "")
        self._lectura_nivel = ttk.Label(cuerpo, text="", font=Fonts.BODY, wraplength=900, justify="left")
        self._lectura_nivel.pack(anchor="w")

        cuerpo = _seccion(c, "Qué datos usa más el modelo",
                          "Qué parte de sus decisiones se apoya en cada dato (los %d más importantes)."
                          % _IMPORTANCIAS_VISIBLES)
        self._importancias = BarList(cuerpo, ancho_texto=28, ancho_valor=6)
        self._importancias.pack(fill="x")

    def mostrar(self, modelo: ModeloIA) -> None:
        if modelo.id_modelo == self._id_mostrado:
            return              # el refresco periódico no debe redibujar lo mismo
        self._id_mostrado = modelo.id_modelo
        ev: Evaluacion = desde_dict(modelo.metricas)
        entrenado = fecha_hora(modelo.entrenado_en) if modelo.entrenado_en else "—"
        self._modelo.configure(text="%s · entrenado el %s" % (textos.nombre_modelo(modelo.version), entrenado))
        self._veredicto.configure(text=ev.veredicto, bootstyle=Colors.SUCCESS if ev.supera_base else Colors.DANGER)
        self._lectura.configure(text=textos.lectura_validacion(ev))
        mejores, comparables = ev.activos_mejores
        self._metricas.establecer([
            ("Error del modelo", textos.error_pct(ev.error)),
            ("Error repitiendo hoy", textos.error_pct(ev.error_hoy)),
            ("Error con el promedio 20 d.", textos.error_pct(ev.error_media)),
            ("Mejora frente a hoy", textos.pct(ev.mejora_hoy, 1),
             Colors.SUCCESS if ev.mejora_hoy > 0 else Colors.DANGER),
            ("z contra hoy (mín. %s)" % textos.numero(Z_MINIMO), textos.numero(ev.z_hoy)),
            ("z contra el promedio", textos.numero(ev.z_media)),
            ("Correlación", textos.numero(ev.correlacion, 2) if ev.correlacion is not None else "—"),
            ("Activos sobre las dos bases", "%d de %d" % (mejores, comparables)),
        ])
        self._tramos.mostrar(ev)
        self._calibracion.establecer_filas([
            (str(i), (b.etiqueta, str(b.n), textos.veces(b.predicho) if b.n else "—",
                      textos.veces(b.real) if b.n else "—"), "")
            for i, b in enumerate(ev.calibracion)])
        self._lectura_calibracion.configure(text=textos.lectura_calibracion(ev.calibracion))
        self._lectura_nivel.configure(text=textos.lectura_nivel(ev))
        mayor = max(ev.importancias.values(), default=0.0) or 1.0
        mas_importantes = sorted(ev.importancias.items(), key=lambda p: -p[1])[:_IMPORTANCIAS_VISIBLES]
        self._importancias.establecer([(textos.factor(n), v / mayor, Palette.EMA, textos.pct(v))
                                       for n, v in mas_importantes])
