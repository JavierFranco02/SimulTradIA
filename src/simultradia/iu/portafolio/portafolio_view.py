"""Portafolio: cómo le va a la cuenta simulada. Dos pestañas:

  - Resumen: franja con seis cifras (patrimonio, rentabilidad, saldo, posiciones, P&L no realizado y realizado);
    debajo, a la izquierda, la curva de capital con la caída desde el máximo (selector 1 día / 1 sem / 1 mes / Todo) y,
    a la derecha, la tabla de métricas de rendimiento y riesgo.
  - Operaciones cerradas: cada venta con su ganancia (de la más nueva a la más vieja).

Las posiciones abiertas y las órdenes viven en Operar; aquí solo se mide cómo va todo.
Vista pasiva: PortafolioController le entrega el resumen. El selector de rango solo cambia cómo se dibuja.
"""
import tkinter as tk
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

import ttkbootstrap as ttk

from simultradia.analisis.metricas import DIAS_MINIMOS
from simultradia.iu.base.panel_view import PanelView
from simultradia.iu.components import DataTable, EquityChart
from simultradia.iu.formato import dinero, fecha_hora, porcentaje, precio, unidades
from simultradia.iu.styles import ButtonStyle, Colors, Fonts, Spacing, texto_normal
from simultradia.services.portafolio_service import ResumenPortafolio

_RANGOS = (("1 día", 24), ("1 sem", 168), ("1 mes", 720), ("Todo", None))     # texto del botón -> horas a mostrar
_CIFRAS = (("patrimonio", "Patrimonio"), ("rentabilidad", "Rentabilidad"), ("saldo", "Saldo disponible"),
           ("posiciones", "En posiciones"), ("no_realizado", "P&L no realizado"), ("realizado", "P&L realizado"))
_COLUMNAS_METRICAS = (
    ("metrica", "Métrica", 190, "w"),
    ("valor", "Valor", 170, "e"),
)
_COLUMNAS_OPERACIONES = (
    ("cerrada", "Cerrada", 130, "center"),
    ("activo", "Activo", 110, "w"),
    ("cantidad", "Cantidad", 100, "e"),
    ("entrada", "Entrada", 100, "e"),
    ("salida", "Salida", 100, "e"),
    ("comisiones", "Comisiones", 100, "e"),
    ("ganancia", "Ganancia", 120, "e"),
    ("pct", "Gan. %", 90, "e"),
)


def _decimales(valor: float, cantidad: int = 2) -> str:
    return ("%.*f" % (cantidad, valor)).replace(".", ",")


class PortafolioView(PanelView):
    def __init__(self, parent):
        super().__init__(parent, padding=Spacing.MD)
        self._cifras: Dict[str, ttk.Label] = {}
        ttk.Label(self, text="Portafolio", font=Fonts.HEADING).pack(anchor="w", pady=(0, Spacing.SM))

        self._cuaderno = ttk.Notebook(self)
        self._cuaderno.pack(fill="both", expand=True)
        self._pestana_resumen = ttk.Frame(self._cuaderno, padding=Spacing.SM)
        self._pestana_operaciones = ttk.Frame(self._cuaderno, padding=Spacing.SM)
        self._cuaderno.add(self._pestana_resumen, text="Resumen")
        self._cuaderno.add(self._pestana_operaciones, text="Operaciones cerradas")
        self._armar_resumen(self._pestana_resumen)
        self._tabla_operaciones = DataTable(self._pestana_operaciones, _COLUMNAS_OPERACIONES)
        self._tabla_operaciones.pack(fill="both", expand=True)

    # ------------------------------------------------------------- armado
    def _armar_resumen(self, padre) -> None:
        franja = ttk.Frame(padre)
        franja.pack(fill="x", pady=(0, Spacing.MD))
        for columna, (clave, titulo) in enumerate(_CIFRAS):
            franja.columnconfigure(columna, weight=1, uniform="cifra")
            bloque = ttk.Frame(franja)
            bloque.grid(row=0, column=columna, sticky="w", padx=(0, Spacing.MD))
            ttk.Label(bloque, text=titulo.upper(), font=Fonts.SMALL).pack(anchor="w")
            etiqueta = ttk.Label(bloque, text="—", font=Fonts.VALUE)
            etiqueta.pack(anchor="w")
            self._cifras[clave] = etiqueta

        cuerpo = ttk.Frame(padre)
        cuerpo.pack(fill="both", expand=True)
        derecha = ttk.Frame(cuerpo)
        derecha.pack(side="right", fill="y", padx=(Spacing.MD, 0))
        ttk.Label(derecha, text="Métricas de rendimiento y riesgo", font=Fonts.VALUE
                  ).pack(anchor="w", pady=(0, Spacing.XS))
        self._tabla_metricas = DataTable(derecha, _COLUMNAS_METRICAS)
        self._tabla_metricas.pack(fill="both", expand=True)
        ttk.Label(derecha, font=Fonts.SMALL, justify="left", wraplength=340,
                  text="La volatilidad y el Sharpe necesitan %d días de historial; antes salen «—»." % DIAS_MINIMOS
                  ).pack(anchor="w", pady=(Spacing.SM, 0))

        izquierda = ttk.Frame(cuerpo)
        izquierda.pack(side="left", fill="both", expand=True)
        barra = ttk.Frame(izquierda)
        barra.pack(fill="x")
        self._rango = tk.StringVar(master=self, value="Todo")
        for texto, _horas in _RANGOS:
            boton = ttk.Radiobutton(barra, text=texto, value=texto, variable=self._rango,
                                    command=self._pulsar_rango, bootstyle=ButtonStyle.TOGGLE)
            boton.pack(side="left", padx=(0, Spacing.XS))
            texto_normal(boton)
        self._grafico = EquityChart(izquierda)
        self._grafico.pack(fill="both", expand=True, pady=(Spacing.SM, 0))

    # ------------------------------------------- lo que el controlador ordena
    def mostrar_portafolio(self, r: ResumenPortafolio) -> None:
        self._pintar("patrimonio", dinero(r.patrimonio, r.moneda), None)
        self._pintar("rentabilidad", porcentaje(r.rentabilidad_pct, con_signo=True), r.rentabilidad_pct)
        self._pintar("saldo", dinero(r.saldo_disponible, r.moneda), None)
        self._pintar("posiciones", dinero(r.valor_posiciones, r.moneda), None)
        self._pintar("no_realizado", dinero(r.pnl_no_realizado, r.moneda, con_signo=True), r.pnl_no_realizado)
        self._pintar("realizado", dinero(r.pnl_realizado, r.moneda, con_signo=True), r.pnl_realizado)
        self._grafico.establecer_datos(r.puntos, r.caidas, r.capital_inicial)
        self._tabla_metricas.establecer_filas([
            (clave, (nombre, valor), "") for clave, nombre, valor in self._metricas(r)])
        self._tabla_operaciones.establecer_filas([
            (str(o.operacion.id_operacion_cerrada),
             (fecha_hora(o.operacion.cerrada_en), str(o.operacion.ticker), unidades(o.operacion.cantidad),
              precio(o.operacion.precio_entrada), precio(o.operacion.precio_salida),
              dinero(o.operacion.comisiones, r.moneda),
              dinero(o.operacion.ganancia_realizada, r.moneda, con_signo=True),
              porcentaje(o.ganancia_pct, con_signo=True)),
             "alza" if o.operacion.ganancia_realizada > 0 else "baja" if o.operacion.ganancia_realizada < 0 else "")
            for o in r.operaciones
        ])
        self._cuaderno.tab(self._pestana_operaciones, text="Operaciones cerradas (%d)" % len(r.operaciones))

    # --------------------------------------------------------------- interno
    def _pintar(self, clave: str, texto: str, signo: Optional[Decimal]) -> None:
        """Pone el texto de una cifra: verde si es positivo, rojo si es negativo, normal si no aplica o es cero."""
        color = Colors.SUCCESS if signo is not None and signo > 0 else (
            Colors.DANGER if signo is not None and signo < 0 else None)
        self._cifras[clave].configure(text=texto, **({"bootstyle": color} if color else {"style": "TLabel"}))

    @staticmethod
    def _metricas(r: ResumenPortafolio) -> List[Tuple[str, str, str]]:
        """Las filas de la tabla de métricas: (clave, nombre, valor ya escrito). Lo que no se puede calcular, «—»."""
        e = r.estadisticas

        def dinero_o_guion(valor: Optional[Decimal]) -> str:
            return "—" if valor is None else dinero(valor, r.moneda, con_signo=True)

        mejor_peor = "—" if e.mejor is None else "%s / %s" % (
            dinero(e.mejor, "", con_signo=True).strip(), dinero(e.peor, "", con_signo=True).strip())
        return [
            ("caida", "Caída máxima", porcentaje(Decimal(str(round(r.caida_maxima, 2))))),
            ("volatilidad", "Volatilidad anual",
             "—" if r.volatilidad_anual is None else porcentaje(Decimal(str(round(r.volatilidad_anual, 2))))),
            ("sharpe", "Ratio de Sharpe", "—" if r.sharpe is None else _decimales(r.sharpe)),
            ("exposicion", "Exposición", porcentaje(r.exposicion_pct)),
            ("operaciones", "Operaciones cerradas", str(e.total)),
            ("aciertos", "Tasa de aciertos", "—" if e.tasa_aciertos is None else porcentaje(e.tasa_aciertos)),
            ("factor", "Factor de beneficio",
             "—" if e.factor_beneficio is None else _decimales(float(e.factor_beneficio))),
            ("ganancia_media", "Ganancia media", dinero_o_guion(e.ganancia_media)),
            ("perdida_media", "Pérdida media", dinero_o_guion(e.perdida_media)),
            ("por_operacion", "Por operación (media)", dinero_o_guion(e.por_operacion)),
            ("mejor_peor", "Mejor / peor", mejor_peor),
            ("comisiones", "Comisiones pagadas", dinero(r.comisiones_pagadas, r.moneda)),
        ]

    # --------------------------------------------------------- eventos de la UI
    def _pulsar_rango(self) -> None:
        self._grafico.establecer_rango(dict(_RANGOS)[self._rango.get()])
