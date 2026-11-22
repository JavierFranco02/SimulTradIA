"""Administración · Modelos de IA: entrenar y evaluar, ver las versiones, activar una y comparar algoritmos.

Vista pasiva: ModelosIAController decide qué pedir y le entrega los datos. Entrenar tarda varios minutos: mientras
corre, todos los botones de acción quedan quietos.
"""
from datetime import datetime, timezone
from tkinter import messagebox
from typing import Callable, Dict, List, Optional

import ttkbootstrap as ttk

from simultradia.domain.entities.modelo_ia_entity import ModeloIA
from simultradia.domain.entities.prediccion_volatilidad_entity import EstadoCiclo
from simultradia.domain.enums import EstadoModelo
from simultradia.ia.volatilidad_serializacion import desde_dict
from simultradia.iu.base.panel_view import PanelView
from simultradia.iu.components import ActionButton, DataTable
from simultradia.iu.formato import fecha_hora, hace
from simultradia.iu.ia import textos
from simultradia.iu.styles import ButtonStyle, Colors, Fonts, Spacing

_FRESCO_HORAS = 26      # se genera una vez al día: más viejo que esto indica que el worker no está corriendo
_ESTADOS = {EstadoModelo.ACTIVO: "Activo", EstadoModelo.ARCHIVADO: "Archivado",
            EstadoModelo.ENTRENANDO: "Entrenando", EstadoModelo.FALLIDO: "Fallido"}
_COLUMNAS_VERSIONES = (
    ("modelo", "Modelo", 130, "w"),
    ("version", "Versión", 70, "center"),
    ("estado", "Estado", 100, "center"),
    ("error", "Error", 80, "e"),
    ("mejora", "vs. hoy", 80, "e"),
    ("z", "z", 70, "e"),
    ("entrenado", "Entrenado", 140, "center"),
)
_COLUMNAS_COMPARACION = (
    ("algoritmo", "Algoritmo", 220, "w"),
    ("error", "Error", 90, "e"),
    ("mejora", "vs. hoy", 90, "e"),
    ("z", "z", 80, "e"),
    ("veredicto", "Veredicto", 200, "w"),
)


class ModelosIAView(PanelView):
    def __init__(self, parent):
        super().__init__(parent, "Modelos de IA", "Entrenar, evaluar y activar el modelo de volatilidad que genera las predicciones")
        self._al_entrenar: Optional[Callable[[], None]] = None
        self._al_comparar: Optional[Callable[[], None]] = None
        self._al_activar: Optional[Callable[[int], None]] = None
        self._activables: Dict[str, bool] = {}          # id del modelo -> se puede activar
        self._ocupado = False

        # Estado del ciclo: datos sueltos, una fila de texto cada uno.
        ciclo = ttk.Frame(self)
        ciclo.pack(fill="x", pady=(0, Spacing.SM))
        self._valores = {}
        for fila, (clave, titulo) in enumerate((("ultima", "Última predicción generada"),
                                                ("hoy", "Predicciones de hoy"),
                                                ("pendientes", "Pendientes de evaluar"),
                                                ("evaluadas", "Ya evaluadas"))):
            ttk.Label(ciclo, text=titulo, font=Fonts.BODY).grid(row=fila, column=0, sticky="w",
                                                                padx=(0, Spacing.LG), pady=2)
            self._valores[clave] = ttk.Label(ciclo, text="—", font=Fonts.BODY)
            self._valores[clave].grid(row=fila, column=1, sticky="w", pady=2)
        ttk.Label(self, font=Fonts.SMALL, justify="left",
                  text="El proceso «python worker.py» genera la predicción del día y evalúa las vencidas cada hora.\n"
                       "Un modelo solo se activa si supera a las DOS bases (repetir el rango de hoy y el promedio de 20 días); si no, queda archivado."
                  ).pack(anchor="w", pady=(0, Spacing.MD))

        # Entrenar.
        barra = ttk.Frame(self)
        barra.pack(fill="x")
        self._boton_entrenar = ActionButton(barra, "Entrenar y evaluar", self._pulsar_entrenar,
                                            "Entrenando... (varios minutos)")
        self._boton_entrenar.pack(side="right")
        self._boton_comparar = ActionButton(barra, "Comparar algoritmos", self._pulsar_comparar,
                                            "Comparando... (varios minutos)", estilo=ButtonStyle.LINK)
        self._boton_comparar.pack(side="right", padx=(0, Spacing.SM))

        # Versiones.
        ttk.Label(self, text="Versiones", font=Fonts.HEADING).pack(anchor="w", pady=(Spacing.MD, Spacing.SM))
        self._tabla = DataTable(self, _COLUMNAS_VERSIONES)
        self._tabla.pack(fill="both", expand=True)
        self._tabla.al_seleccionar(lambda _iid: self._actualizar_boton_activar())
        pie = ttk.Frame(self)
        pie.pack(fill="x", pady=(Spacing.SM, 0))
        self._boton_activar = ActionButton(pie, "Activar esta versión", self._pulsar_activar,
                                           estilo=ButtonStyle.SUCCESS_OUTLINE)
        self._boton_activar.pack(side="left")
        self._boton_activar.configure(state="disabled")

        # Comparación de algoritmos: solo aparece cuando se calculó.
        self._comparacion = ttk.Frame(self)
        self._titulo_comparacion = ttk.Label(self._comparacion, text="", font=Fonts.HEADING)
        self._titulo_comparacion.pack(anchor="w", pady=(Spacing.MD, Spacing.SM))
        self._tabla_comparacion = DataTable(self._comparacion, _COLUMNAS_COMPARACION, alto=5)
        self._tabla_comparacion.pack(fill="x")

    def vincular_acciones(self, al_entrenar: Callable[[], None], al_comparar: Callable[[], None],
                          al_activar: Callable[[int], None]) -> None:
        self._al_entrenar, self._al_comparar, self._al_activar = al_entrenar, al_comparar, al_activar

    def confirmar(self, mensaje: str) -> bool:
        return messagebox.askyesno("Confirmar", mensaje, parent=self)

    @property
    def ocupado(self) -> bool:
        return self._ocupado

    def establecer_ocupado(self, ocupado: bool, accion: str = "entrenar") -> None:
        """`accion` dice cuál botón muestra «Entrenando...» o «Comparando...»; los otros solo se desactivan."""
        self._ocupado = ocupado
        self._boton_entrenar.establecer_ocupado(ocupado and accion == "entrenar")
        self._boton_comparar.establecer_ocupado(ocupado and accion == "comparar")
        if ocupado and accion == "comparar":
            self._boton_entrenar.configure(state="disabled")
        if ocupado and accion == "entrenar":
            self._boton_comparar.configure(state="disabled")
        self._actualizar_boton_activar()

    # ------------------------------------------- lo que el controlador ordena
    def mostrar_estado(self, modelos: List[ModeloIA], ciclo: EstadoCiclo) -> None:
        ultima = ciclo.ultima_generada_en
        if ultima is None:
            self._valores["ultima"].configure(text="Nunca", bootstyle=Colors.WARNING)
        else:
            fresca = (datetime.now(timezone.utc) - ultima).total_seconds() <= _FRESCO_HORAS * 3600
            self._valores["ultima"].configure(
                text="%s · %s" % (hace(ultima), "al día" if fresca else "desactualizada"),
                bootstyle=Colors.SUCCESS if fresca else Colors.WARNING)
        self._valores["hoy"].configure(text=str(ciclo.de_hoy))
        self._valores["pendientes"].configure(text=str(ciclo.pendientes))
        self._valores["evaluadas"].configure(text=str(ciclo.evaluadas))

        filas, self._activables = [], {}
        for m in modelos:
            ev = desde_dict(m.metricas) if m.metricas else None
            filas.append((str(m.id_modelo),
                          (m.nombre, m.version, _ESTADOS[m.estado],
                           textos.error_pct(ev.error) if ev else "—",
                           textos.pct(ev.mejora_hoy, 1) if ev else "—",
                           textos.numero(ev.z) if ev else "—",
                           fecha_hora(m.entrenado_en) if m.entrenado_en else "—"),
                          "alza" if m.estado == EstadoModelo.ACTIVO else "baja" if m.estado == EstadoModelo.FALLIDO else ""))
            self._activables[str(m.id_modelo)] = (m.estado == EstadoModelo.ARCHIVADO and ev is not None
                                                  and ev.supera_base)
        self._tabla.establecer_filas(filas)
        self._actualizar_boton_activar()

    def mostrar_comparacion(self, filas) -> None:
        """`filas`: lista de (algoritmo, Evaluacion). Se agregan, al final, las dos bases que hay que superar."""
        self._titulo_comparacion.configure(text="Comparación de algoritmos")
        datos = [(str(i), (nombre, textos.error_pct(ev.error), textos.pct(ev.mejora_hoy, 1),
                           textos.numero(ev.z), ev.veredicto),
                  "alza" if ev.supera_base else "baja") for i, (nombre, ev) in enumerate(filas)]
        if filas:
            ev = filas[0][1]
            datos.append((str(len(filas)), ("Base: repetir el rango de hoy", textos.error_pct(ev.error_hoy),
                                            "—", "—", "Lo mínimo a superar"), ""))
            datos.append((str(len(filas) + 1), ("Base: promedio de 20 días", textos.error_pct(ev.error_media),
                                                "—", "—", "Lo mínimo a superar"), ""))
        self._tabla_comparacion.establecer_filas(datos)
        if not self._comparacion.winfo_ismapped():
            self._comparacion.pack(fill="x")

    # --------------------------------------------------------- eventos de la UI
    def _actualizar_boton_activar(self) -> None:
        iid = self._tabla.seleccionado()
        puede = iid is not None and self._activables.get(iid, False) and not self._ocupado
        self._boton_activar.configure(state="normal" if puede else "disabled")

    def _pulsar_entrenar(self) -> None:
        if self._al_entrenar:
            self._al_entrenar()

    def _pulsar_comparar(self) -> None:
        if self._al_comparar:
            self._al_comparar()

    def _pulsar_activar(self) -> None:
        iid = self._tabla.seleccionado()
        if iid is not None and self._al_activar:
            self._al_activar(int(iid))
