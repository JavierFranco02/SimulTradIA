"""Pantalla «Predicciones IA»: el escáner de activos a la izquierda y, a la derecha, las pestañas del activo elegido.

  - Escáner: los activos con predicción vigente, del día más agitado al más tranquilo esperado (frente a lo normal).
  - Pestañas: Volatilidad · Proyección de precio · Evaluación · Registro vs. realidad.
Si no hay modelo activo, en lugar de las pestañas se explica por qué.

Vista pasiva: IAController decide qué pedir y le entrega los datos.
"""
from typing import Callable, Dict, Optional, Tuple

import ttkbootstrap as ttk

from simultradia.analisis.montecarlo import Proyeccion
from simultradia.ia.volatilidad_serializacion import desde_dict
from simultradia.iu.base.panel_view import PanelView
from simultradia.iu.components import DataTable
from simultradia.iu.ia import textos
from simultradia.iu.ia.evaluacion_view import EvaluacionView
from simultradia.iu.ia.proyeccion_view import ProyeccionView
from simultradia.iu.ia.registro_view import RegistroView
from simultradia.iu.ia.senal_view import SenalView
from simultradia.iu.styles import Fonts, Spacing

_COLUMNAS = (
    ("ticker", "Activo", 90, "w"),
    ("rango", "Rango", 70, "e"),
    ("nivel", "Nivel", 70, "w"),
    ("veces", "vs. normal", 90, "e"),
)
_ANCHO_ESCANER = 360


class IAView(PanelView):
    def __init__(self, parent):
        super().__init__(parent, padding=Spacing.MD)
        self._al_elegir_activo: Optional[Callable[[int], None]] = None
        self._activos: Dict[int, Tuple[str, str]] = {}    # id del activo -> (ticker, nombre) de los del escáner

        cabecera = ttk.Frame(self)
        cabecera.pack(fill="x", pady=(0, Spacing.SM))
        ttk.Label(cabecera, text="Predicciones IA · Volatilidad", font=Fonts.HEADING).pack(side="left")
        ttk.Label(cabecera, text="Cuánto se moverá cada activo mañana (no hacia dónde)",
                  font=Fonts.SUBTITLE).pack(side="left", padx=(Spacing.MD, 0))

        cuerpo = ttk.Frame(self)
        cuerpo.pack(fill="both", expand=True)
        cuerpo.rowconfigure(0, weight=1)
        cuerpo.columnconfigure(0, weight=0, minsize=_ANCHO_ESCANER)     # el escáner nunca se encoge a nada
        cuerpo.columnconfigure(1, weight=1)

        izquierda = ttk.Frame(cuerpo)
        ttk.Label(izquierda, text="Escáner (de más a menos agitado)", font=Fonts.VALUE).pack(anchor="w", pady=(0, Spacing.XS))
        self._escaner = DataTable(izquierda, _COLUMNAS)
        self._escaner.pack(fill="both", expand=True)
        self._escaner.al_seleccionar(self._pulsar_activo)
        self._pie = ttk.Label(izquierda, text="", font=Fonts.SMALL)
        self._pie.pack(anchor="w", pady=(Spacing.SM, 0))

        derecha = ttk.Frame(cuerpo)
        self._sin_modelo = ttk.Label(derecha, text="", font=Fonts.SUBTITLE, justify="center", wraplength=520)
        self._pestanas = ttk.Notebook(derecha)
        self.senal, self.proyeccion = SenalView(self._pestanas), ProyeccionView(self._pestanas)
        self.evaluacion, self.registro = EvaluacionView(self._pestanas), RegistroView(self._pestanas)
        for vista, texto in ((self.senal, "Volatilidad"), (self.proyeccion, "Proyección de precio"),
                             (self.evaluacion, "Evaluación"), (self.registro, "Registro vs. realidad")):
            self._pestanas.add(vista, text=texto)
        self._pestanas.pack(fill="both", expand=True)

        izquierda.grid(row=0, column=0, sticky="nsew", padx=(0, Spacing.MD))
        derecha.grid(row=0, column=1, sticky="nsew")

    def vincular_acciones(self, al_elegir_activo: Callable[[int], None],
                          al_calcular_nivel: Callable[[], None]) -> None:
        self._al_elegir_activo = al_elegir_activo
        self.proyeccion.vincular_acciones(al_calcular_nivel)

    # --------------------------------------------- lo que el controlador lee
    def texto_nivel(self) -> str:
        return self.proyeccion.texto_nivel()

    # ------------------------------------------- lo que el controlador ordena
    def mostrar_resumen(self, resumen) -> None:
        if resumen.modelo is None:
            self._pestanas.pack_forget()
            self._sin_modelo.configure(text="No hay un modelo de volatilidad activo.\n\nO todavía no se entrenó, o no "
                                            "superó a las dos bases (repetir el rango de hoy y el promedio de 20 "
                                            "días). Un administrador puede entrenarlo en «Modelos de IA».")
            self._sin_modelo.pack(expand=True)
            self._escaner.establecer_filas([])
            self._pie.configure(text="")
            return
        self._sin_modelo.pack_forget()
        if not self._pestanas.winfo_ismapped():
            self._pestanas.pack(fill="both", expand=True)
        filas = []
        for s in resumen.senales:
            p = s.prediccion
            self._activos[p.id_activo] = (s.ticker, s.nombre)
            filas.append((str(p.id_activo), (s.ticker, textos.rango(p.rango_predicho), textos.nivel(p.nivel),
                                             textos.veces(p.veces_lo_normal).replace(" lo normal", "")), ""))
        self._escaner.establecer_filas(filas)
        self._pie.configure(text="%d activos con predicción" % len(filas) if filas else "Sin predicciones todavía.")
        self.evaluacion.mostrar(resumen.modelo)
        self.registro.mostrar_precision(resumen.precision, desde_dict(resumen.modelo.metricas))

    def seleccionar(self, id_activo: int) -> None:
        self._escaner.seleccionar(str(id_activo))

    def datos_de(self, id_activo: int) -> Tuple[str, str]:
        """(ticker, nombre) de un activo que se ve en el escáner."""
        return self._activos.get(id_activo, ("—", ""))

    def mostrar_detalle(self, ticker: str, nombre: str, detalle) -> None:
        self.senal.mostrar(ticker, nombre, detalle)
        self.registro.mostrar_historial(ticker, detalle.historial)

    def mostrar_proyeccion(self, proyeccion: Proyeccion, nivel: Optional[float]) -> None:
        self.proyeccion.mostrar(proyeccion, nivel)

    def proyeccion_no_disponible(self, texto: str) -> None:
        self.proyeccion.limpiar(texto)

    def limpiar_detalle(self) -> None:
        self.senal.limpiar()
        self.proyeccion.limpiar()
        self.registro.mostrar_historial(None, [])

    # --------------------------------------------------------- eventos de la UI
    def _pulsar_activo(self, iid: Optional[str]) -> None:
        if iid is not None and self._al_elegir_activo:
            self._al_elegir_activo(int(iid))
