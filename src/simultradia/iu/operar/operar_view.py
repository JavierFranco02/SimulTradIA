"""Operar: ticket de orden a la izquierda; a la derecha, el gráfico del activo (en su versión compacta)
y, debajo, en pestañas: posiciones abiertas, órdenes pendientes e historial de órdenes.

Vista pasiva: OperarController le dice qué mostrar y recibe lo que el usuario pulsa. El gráfico es
el mismo de Mercado (`GraficoActivoView`) y lo maneja su propio GraficoController.
Los bordes entre las zonas se arrastran con el mouse; al abrir, el gráfico se lleva casi dos tercios del alto.
El ticket tiene tres tarjetas (la de la cuenta, la calculadora de riesgo y el resumen de la orden) y se desplaza
si no cabe en el alto.
"""
import tkinter as tk
from decimal import Decimal
from tkinter import messagebox
from typing import Callable, Dict, List, Optional

import ttkbootstrap as ttk

from simultradia.domain.entities.cotizacion_entity import ActivoCotizado
from simultradia.domain.entities.orden_entity import Ejecucion, Orden
from simultradia.domain.enums import EstadoOrden, LadoOrden, TipoOrden
from simultradia.domain.reglas import indicadores as cfg
from simultradia.domain.reglas.operaciones import Estimacion
from simultradia.iu.base.panel_view import PanelView
from simultradia.iu.components import ActionButton, Card, DataTable, ScrollFrame, SelectField
from simultradia.iu.formato import dinero, fecha_hora, porcentaje, precio, unidades
from simultradia.iu.mercado.grafico_view import GraficoActivoView
from simultradia.iu.operar.proteccion_dialog import EditarProteccionDialog
from simultradia.iu.styles import ButtonStyle, Colors, Fonts, Palette, Spacing
from simultradia.services.operar_service import (
    CantidadPorRiesgo, PosicionValorada, ResumenOperar, SolicitudOrden, SugerenciaStop)

_TIPO = {TipoOrden.MERCADO: "Mercado", TipoOrden.LIMITE: "Límite", TipoOrden.STOP_LOSS: "Stop-loss",
         TipoOrden.TAKE_PROFIT: "Take-profit", TipoOrden.STOP_LIMITE: "Stop-límite"}
_ESTADO = {EstadoOrden.PENDIENTE: "Pendiente", EstadoOrden.PARCIAL: "Parcial", EstadoOrden.EJECUTADA: "Ejecutada",
           EstadoOrden.CANCELADA: "Cancelada", EstadoOrden.RECHAZADA: "Rechazada", EstadoOrden.EXPIRADA: "Expirada"}
_COLUMNAS_POSICIONES = (
    ("activo", "Activo", 100, "w"),
    ("cantidad", "Cantidad", 100, "e"),
    ("promedio", "P. medio", 90, "e"),
    ("precio", "Precio", 90, "e"),
    ("valor", "Valor", 110, "e"),
    ("pnl", "P&L", 110, "e"),
    ("pnl_pct", "P&L %", 80, "e"),
    ("sl", "Stop-loss", 90, "e"),
    ("tp", "Take-profit", 90, "e"),
)
_COLUMNAS_PENDIENTES = (
    ("id", "N°", 50, "center"),
    ("activo", "Activo", 100, "w"),
    ("lado", "Lado", 70, "center"),
    ("tipo", "Tipo", 80, "center"),
    ("cantidad", "Cantidad", 100, "e"),
    ("precio", "Precio límite", 100, "e"),
    ("sl", "Stop-loss", 90, "e"),
    ("tp", "Take-profit", 90, "e"),
    ("creada", "Creada", 130, "center"),
)
_COLUMNAS_HISTORIAL = (
    ("fecha", "Fecha", 130, "center"),
    ("activo", "Activo", 100, "w"),
    ("lado", "Lado", 70, "center"),
    ("tipo", "Tipo", 80, "center"),
    ("cantidad", "Cantidad", 100, "e"),
    ("precio", "P. ejecución", 100, "e"),
    ("comision", "Comisión", 90, "e"),
    ("estado", "Estado", 90, "center"),
    ("nota", "Nota", 260, "w"),
)
_ANCHO_TICKET = 340     # ancho del ticket, en píxeles
_PROPORCION_GRAFICO = 0.66     # parte del alto que se lleva el gráfico al abrir la pantalla
_TIPOS_DE_ORDEN = ((TipoOrden.MERCADO.value, "Mercado"), (TipoOrden.LIMITE.value, "Límite"))


def _niveles(valor: Optional[Decimal]) -> str:
    return "—" if valor is None else precio(valor)


class OperarView(PanelView):
    def __init__(self, parent):
        super().__init__(parent, padding=Spacing.MD)
        self._al_elegir_activo: Optional[Callable[[], None]] = None
        self._al_cambiar_orden: Optional[Callable[[], None]] = None
        self._al_porcentaje: Optional[Callable[[int], None]] = None
        self._al_enviar: Optional[Callable[[], None]] = None
        self._al_cerrar_posicion: Optional[Callable[[], None]] = None
        self._al_cerrar_todas: Optional[Callable[[], None]] = None
        self._al_guardar_proteccion: Optional[Callable[[int, str, str], None]] = None
        self._al_cancelar_orden: Optional[Callable[[], None]] = None
        self._al_sugerir_stop: Optional[Callable[[], None]] = None
        self._al_calcular_cantidad: Optional[Callable[[], None]] = None
        self._tickers: Dict[str, str] = {}              # id del activo -> ticker
        self._posiciones: Dict[str, PosicionValorada] = {}
        self._pendientes: Dict[str, Orden] = {}
        self._dialogo: Optional[EditarProteccionDialog] = None
        self._moneda = "USD"

        panel = ttk.Panedwindow(self, orient="horizontal")
        panel.pack(fill="both", expand=True)
        panel.add(self._crear_ticket(panel), weight=0)
        self._derecha = ttk.Panedwindow(panel, orient="vertical")
        self.grafico = GraficoActivoView(self._derecha, compacto=True)
        self._derecha.add(self.grafico, weight=3)
        self._derecha.add(self._crear_tablas(self._derecha), weight=2)
        panel.add(self._derecha, weight=1)

        for variable in (self._cantidad, self._limite, self._stop_loss, self._take_profit):
            variable.trace_add("write", lambda *_args: self._pulsar_orden())
        self._actualizar_lado()
        self._actualizar_campos()
        self.mostrar_estimacion(None)
        self.programar(150, self._fijar_reparto)

    # ------------------------------------------------------------- armado
    @staticmethod
    def _rotulo(padre, texto: str) -> ttk.Label:
        """Título pequeño y apagado de un dato (SALDO DISPONIBLE, TU POSICIÓN...)."""
        return ttk.Label(padre, text=texto.upper(), font=Fonts.SMALL, foreground=Palette.TEXTO)

    def _campo(self, padre, rotulo: str):
        """Un rótulo con una caja de texto debajo. Devuelve (marco, variable, entrada)."""
        marco = ttk.Frame(padre)
        self._rotulo(marco, rotulo).pack(anchor="w", pady=(0, 2))
        variable = tk.StringVar(master=self)
        entrada = ttk.Entry(marco, textvariable=variable, font=Fonts.BODY)
        entrada.pack(fill="x")
        return marco, variable, entrada

    def _crear_ticket(self, padre) -> ScrollFrame:
        desplazable = ScrollFrame(padre, ancho=_ANCHO_TICKET)
        t = desplazable.cuerpo
        self._activo = SelectField(t, "Activo", ancho=36)
        self._activo.pack(fill="x")
        self._activo.al_cambiar(self._pulsar_activo)

        # --- tarjeta de la cuenta: saldo y posición en este activo
        cuenta = Card(t)
        cuenta.pack(fill="x", pady=(Spacing.MD, 0))
        c = cuenta.cuerpo
        self._rotulo(c, "Saldo disponible").pack(anchor="w")
        self._saldo = ttk.Label(c, text="—", font=Fonts.HEADING)
        self._saldo.pack(anchor="w")
        ttk.Separator(c).pack(fill="x", pady=Spacing.SM)
        self._rotulo_posicion = self._rotulo(c, "Tu posición")
        self._rotulo_posicion.pack(anchor="w")
        self._posicion = ttk.Label(c, text="—", font=Fonts.BODY, foreground=Palette.TEXTO)
        self._posicion.pack(anchor="w")
        self._promedio = ttk.Label(c, text="", font=Fonts.SMALL, foreground=Palette.TEXTO)
        self._promedio.pack(anchor="w")
        self._pnl = ttk.Label(c, text="", font=Fonts.BODY)
        self._pnl.pack(anchor="w")
        self._niveles_posicion = ttk.Label(c, text="", font=Fonts.SMALL, foreground=Palette.TEXTO)
        self._niveles_posicion.pack(anchor="w")

        # --- la orden: lado, tipo, cantidad, atajos y niveles
        self._lado = tk.StringVar(master=self, value=LadoOrden.COMPRA.value)
        lados = ttk.Frame(t)
        lados.pack(fill="x", pady=(Spacing.MD, 0))
        for columna, (lado, texto, estilo) in enumerate(((LadoOrden.COMPRA, "Comprar", ButtonStyle.TOGGLE_COMPRA),
                                                         (LadoOrden.VENTA, "Vender", ButtonStyle.TOGGLE_VENTA))):
            lados.columnconfigure(columna, weight=1, uniform="lado")
            ttk.Radiobutton(lados, text=texto, value=lado.value, variable=self._lado,
                            command=self._pulsar_lado, bootstyle=estilo
                            ).grid(row=0, column=columna, sticky="ew", ipady=4,
                                   padx=(0 if columna == 0 else Spacing.XS, 0))

        tipo_y_limite = ttk.Frame(t)
        tipo_y_limite.pack(fill="x", pady=(Spacing.MD, 0))
        tipo_y_limite.columnconfigure(0, weight=1, uniform="tipo")
        tipo_y_limite.columnconfigure(1, weight=1, uniform="tipo")
        izquierda = ttk.Frame(tipo_y_limite)
        izquierda.grid(row=0, column=0, sticky="ew", padx=(0, Spacing.XS))
        self._rotulo(izquierda, "Tipo de orden").pack(anchor="w", pady=(0, 2))
        self._tipo = SelectField(izquierda, None, _TIPOS_DE_ORDEN, ancho=10)
        self._tipo.pack(fill="x")
        self._tipo.al_cambiar(self._pulsar_tipo)
        marco, self._limite, self._entrada_limite = self._campo(tipo_y_limite, "Precio límite")
        marco.grid(row=0, column=1, sticky="ew", padx=(Spacing.XS, 0))

        self._rotulo(t, "Cantidad").pack(anchor="w", pady=(Spacing.MD, 2))
        fila = ttk.Frame(t)
        fila.pack(fill="x")
        self._cantidad = tk.StringVar(master=self)
        ttk.Entry(fila, textvariable=self._cantidad, font=Fonts.BODY).pack(side="left", fill="x", expand=True)
        ActionButton(fila, "Máx.", lambda: self._pulsar_porcentaje(100),
                     estilo=ButtonStyle.LIGHT_OUTLINE).pack(side="left", padx=(Spacing.SM, 0))
        atajos = ttk.Frame(t)
        atajos.pack(fill="x", pady=(Spacing.SM, 0))
        for columna, porcentaje_atajo in enumerate((25, 50, 75)):
            atajos.columnconfigure(columna, weight=1, uniform="atajo")
            ActionButton(atajos, "%d %%" % porcentaje_atajo,
                         lambda p=porcentaje_atajo: self._pulsar_porcentaje(p),
                         estilo=ButtonStyle.LIGHT_OUTLINE
                         ).grid(row=0, column=columna, sticky="ew",
                                padx=(0 if columna == 0 else Spacing.XS, 0))

        niveles = ttk.Frame(t)
        niveles.pack(fill="x", pady=(Spacing.MD, 0))
        niveles.columnconfigure(0, weight=1, uniform="nivel")
        niveles.columnconfigure(1, weight=1, uniform="nivel")
        marco, self._stop_loss, self._entrada_stop_loss = self._campo(niveles, "Stop-loss")
        marco.grid(row=0, column=0, sticky="ew", padx=(0, Spacing.XS))
        marco, self._take_profit, self._entrada_take_profit = self._campo(niveles, "Take-profit")
        marco.grid(row=0, column=1, sticky="ew", padx=(Spacing.XS, 0))

        # --- tarjeta de la calculadora de riesgo: cuántas unidades comprar para arriesgar un % del capital
        calculadora = Card(t)
        calculadora.pack(fill="x", pady=(Spacing.MD, 0))
        k = calculadora.cuerpo
        self._rotulo(k, "Calculadora de riesgo").pack(anchor="w")
        fila = ttk.Frame(k)
        fila.pack(fill="x", pady=(Spacing.SM, 0))
        ttk.Label(fila, text="Arriesgar (% del capital)", font=Fonts.BODY,
                  foreground=Palette.TEXTO).pack(side="left")
        self._riesgo = tk.StringVar(master=self, value="1")
        self._entrada_riesgo = ttk.Entry(fila, textvariable=self._riesgo, width=6, font=Fonts.BODY)
        self._entrada_riesgo.pack(side="right")
        self._boton_stop = ActionButton(k, "Sugerir stop (%d×ATR)" % cfg.MULTIPLO_ATR_STOP,
                                        self._pulsar_sugerir_stop, estilo=ButtonStyle.LIGHT_OUTLINE)
        self._boton_stop.pack(fill="x", pady=(Spacing.SM, 0))
        self._boton_calcular = ActionButton(k, "Calcular cantidad", self._pulsar_calcular_cantidad,
                                            estilo=ButtonStyle.LIGHT_OUTLINE)
        self._boton_calcular.pack(fill="x", pady=(Spacing.XS, 0))
        self._nota_riesgo = ttk.Label(k, text="", font=Fonts.SMALL, foreground=Palette.TEXTO,
                                      wraplength=_ANCHO_TICKET - 60, justify="left")
        self._nota_riesgo.pack(anchor="w", pady=(Spacing.XS, 0))

        # --- tarjeta con el resumen de la orden: etiquetas a la izquierda, valores a la derecha
        resumen = Card(t)
        resumen.pack(fill="x", pady=(Spacing.MD, 0))
        r = resumen.cuerpo
        r.columnconfigure(1, weight=1)
        self._est_titulos, self._est = {}, {}
        fila = 0
        for clave, titulo in (("precio", "Precio de ejecución"), ("monto", "Monto"), ("comision", "Comisión"),
                              ("separador", None), ("total", "Total"), ("saldo", "Saldo después"),
                              ("riesgo", "Riesgo hasta el stop"), ("ganancia", "Ganancia estimada")):
            if clave == "separador":
                ttk.Separator(r).grid(row=fila, column=0, columnspan=2, sticky="ew", pady=Spacing.SM)
            else:
                destacado = clave == "total"
                self._est_titulos[clave] = ttk.Label(
                    r, text=titulo, font=Fonts.VALUE if destacado else Fonts.BODY,
                    foreground="" if destacado else Palette.TEXTO)
                self._est_titulos[clave].grid(row=fila, column=0, sticky="w", pady=2)
                self._est[clave] = ttk.Label(r, text="—", font=Fonts.VALUE if destacado else Fonts.BODY)
                self._est[clave].grid(row=fila, column=1, sticky="e", padx=(Spacing.MD, 0), pady=2)
            fila += 1
        self._est_error = ttk.Label(t, text="", font=Fonts.SMALL, bootstyle=Colors.DANGER,
                                    wraplength=_ANCHO_TICKET - 40, justify="left")
        self._est_error.pack(anchor="w", pady=(Spacing.XS, 0))

        self._boton_enviar = ActionButton(t, "Enviar orden", self._pulsar_enviar, "Enviando...")
        self._boton_enviar.pack(fill="x", pady=(Spacing.SM, 0), ipady=6)
        return desplazable

    def _crear_tablas(self, padre) -> ttk.Notebook:
        self._cuaderno = ttk.Notebook(padre)

        self._tab_posiciones = ttk.Frame(self._cuaderno, padding=Spacing.SM)
        barra = ttk.Frame(self._tab_posiciones)
        barra.pack(side="bottom", fill="x", pady=(Spacing.SM, 0))     # primero la barra: queda abajo del todo
        self._boton_cerrar = ActionButton(barra, "Cerrar posición", self._pulsar_cerrar,
                                          estilo=ButtonStyle.DANGER_OUTLINE)
        self._boton_cerrar.pack(side="left")
        self._boton_proteccion = ActionButton(barra, "Editar SL/TP", self._abrir_proteccion,
                                              estilo=ButtonStyle.LIGHT_OUTLINE)
        self._boton_proteccion.pack(side="left", padx=(Spacing.SM, 0))
        self._boton_cerrar_todas = ActionButton(barra, "Cerrar todas", self._pulsar_cerrar_todas,
                                                estilo=ButtonStyle.DANGER_OUTLINE)
        self._boton_cerrar_todas.pack(side="left", padx=(Spacing.SM, 0))
        self._tabla_posiciones = DataTable(self._tab_posiciones, _COLUMNAS_POSICIONES)
        self._tabla_posiciones.pack(fill="both", expand=True)
        self._tabla_posiciones.al_seleccionar(lambda _iid: self._actualizar_botones())
        self._tabla_posiciones.al_doble_clic(lambda _iid: self._abrir_proteccion())
        self._cuaderno.add(self._tab_posiciones, text="Posiciones abiertas")

        self._tab_pendientes = ttk.Frame(self._cuaderno, padding=Spacing.SM)
        barra = ttk.Frame(self._tab_pendientes)
        barra.pack(side="bottom", fill="x", pady=(Spacing.SM, 0))
        self._boton_cancelar = ActionButton(barra, "Cancelar orden", self._pulsar_cancelar,
                                            estilo=ButtonStyle.DANGER_OUTLINE)
        self._boton_cancelar.pack(side="left")
        self._tabla_pendientes = DataTable(self._tab_pendientes, _COLUMNAS_PENDIENTES)
        self._tabla_pendientes.pack(fill="both", expand=True)
        self._tabla_pendientes.al_seleccionar(lambda _iid: self._actualizar_botones())
        self._cuaderno.add(self._tab_pendientes, text="Órdenes pendientes")

        historial = ttk.Frame(self._cuaderno, padding=Spacing.SM)
        self._tabla_historial = DataTable(historial, _COLUMNAS_HISTORIAL)
        self._tabla_historial.pack(fill="both", expand=True)
        self._cuaderno.add(historial, text="Historial de órdenes")
        self._actualizar_botones()
        return self._cuaderno

    def vincular_acciones(self, al_elegir_activo: Callable[[], None], al_cambiar_orden: Callable[[], None],
                          al_porcentaje: Callable[[int], None], al_enviar: Callable[[], None],
                          al_cerrar_posicion: Callable[[], None], al_cerrar_todas: Callable[[], None],
                          al_guardar_proteccion: Callable[[int, str, str], None],
                          al_cancelar_orden: Callable[[], None], al_sugerir_stop: Callable[[], None],
                          al_calcular_cantidad: Callable[[], None]) -> None:
        self._al_elegir_activo = al_elegir_activo
        self._al_cambiar_orden = al_cambiar_orden
        self._al_porcentaje = al_porcentaje
        self._al_enviar = al_enviar
        self._al_cerrar_posicion = al_cerrar_posicion
        self._al_cerrar_todas = al_cerrar_todas
        self._al_guardar_proteccion = al_guardar_proteccion
        self._al_cancelar_orden = al_cancelar_orden
        self._al_sugerir_stop = al_sugerir_stop
        self._al_calcular_cantidad = al_calcular_cantidad

    # --------------------------------------------- lo que el controlador lee
    def activo_elegido(self) -> Optional[int]:
        clave = self._activo.obtener()
        return int(clave) if clave else None

    def lado(self) -> LadoOrden:
        return LadoOrden(self._lado.get())

    def solicitud(self) -> SolicitudOrden:
        """Lo escrito en el ticket. Lo que no aplica (el límite en una orden a mercado, el stop-loss y el
        take-profit al vender) va vacío aunque la caja tenga texto."""
        tipo = TipoOrden(self._tipo.obtener() or TipoOrden.MERCADO.value)
        compra = self.lado() == LadoOrden.COMPRA
        return SolicitudOrden(
            lado=self.lado(), tipo=tipo, cantidad=self._cantidad.get(),
            precio_limite=self._limite.get() if tipo == TipoOrden.LIMITE else "",
            stop_loss=self._stop_loss.get() if compra else "",
            take_profit=self._take_profit.get() if compra else "")

    def riesgo_escrito(self) -> str:
        return self._riesgo.get()

    def posicion_elegida(self) -> Optional[int]:
        """El id del activo de la posición elegida en la tabla."""
        iid = self._tabla_posiciones.seleccionado()
        return int(iid) if iid in self._posiciones else None

    def orden_pendiente_elegida(self) -> Optional[int]:
        iid = self._tabla_pendientes.seleccionado()
        return int(iid) if iid in self._pendientes else None

    @property
    def ocupado(self) -> bool:
        return self._boton_enviar.ocupado

    def confirmar(self, mensaje: str) -> bool:
        return messagebox.askyesno("Confirmar", mensaje, parent=self)

    def confirmar_orden(self) -> bool:
        s = self.solicitud()
        ticker = self._tickers.get(self._activo.obtener() or "", "")
        accion = "la compra" if s.lado == LadoOrden.COMPRA else "la venta"
        como = ("con límite en %s" % s.precio_limite.strip()) if s.tipo == TipoOrden.LIMITE else "al precio de mercado"
        return self.confirmar("¿Confirmas %s de %s %s %s?" % (accion, s.cantidad.strip(), ticker, como))

    # ------------------------------------------- lo que el controlador ordena
    def establecer_ocupado(self, ocupado: bool) -> None:
        self._boton_enviar.establecer_ocupado(ocupado)
        self._actualizar_botones()

    def establecer_activos(self, items: List[ActivoCotizado]) -> None:
        self._tickers = {str(i.activo.id_activo): i.activo.ticker for i in items}
        self._activo.establecer_opciones(
            [(str(i.activo.id_activo), "%s · %s" % (i.activo.ticker, i.activo.nombre)) for i in items])

    def seleccionar_activo(self, id_activo: int) -> None:
        try:
            self._activo.establecer(str(id_activo))
        except ValueError:      # ese activo ya no está en la lista (deshabilitado): se deja el que estaba
            pass

    def establecer_cantidad(self, cantidad: Decimal) -> None:
        self._cantidad.set(unidades(cantidad))

    def mostrar_resumen(self, r: ResumenOperar) -> None:
        self._moneda = r.moneda
        a, p = r.item.activo, r.posicion
        self._saldo.configure(text=dinero(r.saldo_disponible, r.moneda))
        self._rotulo_posicion.configure(text=("Tu posición en %s" % a.ticker).upper())
        if p is None:
            self._posicion.configure(text="Aún no tienes %s" % a.ticker, font=Fonts.BODY, foreground=Palette.TEXTO)
            self._promedio.configure(text="")
            self._pnl.configure(text="")
            self._niveles_posicion.configure(text="")
        else:
            self._posicion.configure(text="%s %s" % (unidades(p.cantidad), a.ticker), font=Fonts.VALUE, foreground="")
            self._promedio.configure(text="Precio promedio %s %s" % (precio(p.precio_promedio_entrada), a.moneda))
            if r.ganancia is None:
                self._pnl.configure(text="")
            else:
                self._pnl.configure(
                    text="P&L %s (%s)" % (dinero(r.ganancia, r.moneda, con_signo=True),
                                          porcentaje(r.ganancia_pct, con_signo=True)),
                    bootstyle=Colors.DANGER if r.ganancia < 0 else Colors.SUCCESS)
            self._niveles_posicion.configure(
                text="" if p.stop_loss is None and p.take_profit is None
                else "SL %s · TP %s" % (_niveles(p.stop_loss), _niveles(p.take_profit)))
        texto = "Comisión (%s)" % porcentaje(r.comision_pct)
        if r.deslizamiento_pct > 0:
            texto += " + desliz. %s" % porcentaje(r.deslizamiento_pct)
        self._est_titulos["comision"].configure(text=texto)

    def mostrar_estimacion(self, e: Optional[Estimacion]) -> None:
        """Con `None` deja las cifras vacías (todavía no hay una cantidad válida)."""
        self._est_error.configure(text="")
        if e is None:
            for etiqueta in self._est.values():
                etiqueta.configure(text="—")
            return
        self._est["precio"].configure(text="%s %s" % (precio(e.precio), self._moneda))
        self._est["monto"].configure(text=dinero(e.monto, self._moneda))
        self._est["comision"].configure(text=dinero(e.comision, self._moneda))
        self._est["total"].configure(text=dinero(e.total, self._moneda))
        self._est["saldo"].configure(text=dinero(e.saldo_despues, self._moneda))
        self._est["riesgo"].configure(
            text="—" if e.riesgo is None else dinero(e.riesgo, self._moneda) + (
                "" if e.riesgo_pct is None else " (%s)" % porcentaje(e.riesgo_pct)))
        self._est["ganancia"].configure(
            text="—" if e.ganancia is None else dinero(e.ganancia, self._moneda, con_signo=True))

    def mostrar_error_estimacion(self, texto: str) -> None:
        self.mostrar_estimacion(None)
        self._est_error.configure(text=texto)

    def mostrar_posiciones(self, posiciones: List[PosicionValorada]) -> None:
        self._posiciones = {str(v.posicion.id_activo): v for v in posiciones}
        filas = []
        for v in posiciones:
            p = v.posicion
            base = (v.ticker, unidades(p.cantidad), precio(p.precio_promedio_entrada))
            niveles = (_niveles(p.stop_loss), _niveles(p.take_profit))
            if v.ganancia is None:
                valores, etiqueta = base + ("—", "—", "—", "—") + niveles, ""
            else:
                valores = base + (precio(v.precio_actual), dinero(v.valor, v.moneda),
                                  dinero(v.ganancia, v.moneda, con_signo=True),
                                  porcentaje(v.ganancia_pct, con_signo=True)) + niveles
                etiqueta = "alza" if v.ganancia > 0 else "baja" if v.ganancia < 0 else ""
            filas.append((str(p.id_activo), valores, etiqueta))
        self._tabla_posiciones.establecer_filas(filas)
        self._cuaderno.tab(self._tab_posiciones, text="Posiciones abiertas (%d)" % len(posiciones))
        self._actualizar_botones()

    def mostrar_pendientes(self, ordenes: List[Orden]) -> None:
        self._pendientes = {str(o.id_orden): o for o in ordenes}
        self._tabla_pendientes.establecer_filas([
            (str(o.id_orden),
             (str(o.id_orden), o.ticker, "Compra" if o.lado == LadoOrden.COMPRA else "Venta", _TIPO[o.tipo],
              unidades(o.cantidad), precio(o.precio_limite), _niveles(o.stop_loss), _niveles(o.take_profit),
              fecha_hora(o.creada_en)),
             "alza" if o.lado == LadoOrden.COMPRA else "baja")
            for o in ordenes
        ])
        self._cuaderno.tab(self._tab_pendientes, text="Órdenes pendientes (%d)" % len(ordenes))
        self._actualizar_botones()

    def mostrar_historial(self, ordenes: List[Orden]) -> None:
        self._tabla_historial.establecer_filas([
            (str(o.id_orden),
             (fecha_hora(o.ejecutada_en or o.cancelada_en or o.creada_en), o.ticker,
              "Compra" if o.lado == LadoOrden.COMPRA else "Venta", _TIPO[o.tipo], unidades(o.cantidad),
              "—" if o.precio_promedio is None else precio(o.precio_promedio),
              dinero(o.comision_total, self._moneda), _ESTADO[o.estado], o.motivo_rechazo or ""),
             "alza" if o.lado == LadoOrden.COMPRA else "baja")
            for o in ordenes
        ])

    def mostrar_stop_sugerido(self, s: SugerenciaStop) -> None:
        """Pone el stop-loss sugerido en su caja y explica de dónde sale."""
        self._stop_loss.set(unidades(s.stop_loss))
        self._nota_riesgo.configure(text="ATR diario %s · stop a %d×ATR de %s" % (
            precio(s.atr), cfg.MULTIPLO_ATR_STOP, precio(s.referencia)))

    def mostrar_cantidad_por_riesgo(self, c: CantidadPorRiesgo) -> None:
        """Pone la cantidad calculada y deja a la vista cuánto se arriesga con ella."""
        self.establecer_cantidad(c.cantidad)
        self._nota_riesgo.configure(text="Si el precio llega al stop pierdes unos %s (%s del capital)%s" % (
            dinero(c.riesgo, self._moneda), porcentaje(c.riesgo_pct),
            ". Limitada por tu saldo: con él no alcanza para arriesgar todo lo pedido." if c.limitada_por_saldo else "."))

    def mostrar_ejecucion(self, e: Ejecucion) -> None:
        """Confirma la operación hecha y deja el ticket listo para otra."""
        self._limpiar_orden()
        self.mostrar_exito("%s ejecutada: %s %s a %s (comisión %s)." % (
            "Compra" if e.lado == LadoOrden.COMPRA else "Venta", unidades(e.cantidad), e.ticker,
            precio(e.precio), dinero(e.comision, self._moneda)))

    def mostrar_pendiente(self, o: Orden) -> None:
        """Confirma que la orden límite quedó esperando su precio."""
        self._limpiar_orden()
        self.mostrar_exito("Orden límite enviada: %s de %s %s a %s. Queda pendiente hasta que el precio llegue." % (
            "compra" if o.lado == LadoOrden.COMPRA else "venta", unidades(o.cantidad), o.ticker,
            precio(o.precio_limite)))

    # ------------------------------- ventana de stop-loss y take-profit (y sobre cuál se abren los avisos)
    def _padre_aviso(self):
        """Los avisos se abren sobre la ventana de SL/TP si hay una abierta; si no, sobre el panel."""
        return self._dialogo if self._dialogo is not None and self._dialogo.esta_viva() else self

    def mostrar_errores_proteccion(self, errores: Dict[str, str]) -> None:
        if self._dialogo is not None and self._dialogo.esta_viva():
            self._dialogo.mostrar_errores(errores)
        else:
            for texto in errores.values():
                self.mostrar_error(texto)

    def limpiar_errores_proteccion(self) -> None:
        if self._dialogo is not None and self._dialogo.esta_viva():
            self._dialogo.limpiar_errores()

    def cerrar_proteccion(self) -> None:
        if self._dialogo is not None and self._dialogo.esta_viva():
            self._dialogo.destroy()
        self._dialogo = None

    def _abrir_proteccion(self) -> None:
        id_activo = self.posicion_elegida()
        if id_activo is None:
            return
        v = self._posiciones[str(id_activo)]
        p = v.posicion
        self._dialogo = EditarProteccionDialog(
            self, id_activo, v.ticker,
            "" if p.stop_loss is None else unidades(p.stop_loss),
            "" if p.take_profit is None else unidades(p.take_profit),
            al_guardar=self._pulsar_guardar_proteccion)

    # --------------------------------------------------------------- interno
    def _limpiar_orden(self) -> None:
        for variable in (self._cantidad, self._limite, self._stop_loss, self._take_profit):
            variable.set("")

    def _actualizar_lado(self) -> None:
        compra = self.lado() == LadoOrden.COMPRA
        self._boton_enviar.establecer_texto("Enviar orden de compra" if compra else "Enviar orden de venta")
        self._boton_enviar.configure(bootstyle=ButtonStyle.SUCCESS_OUTLINE if compra else ButtonStyle.DANGER_OUTLINE)
        self._est_titulos["total"].configure(text="Total a pagar" if compra else "Recibirás")

    def _actualizar_campos(self) -> None:
        """Cada caja solo se puede escribir cuando aplica: el límite en las órdenes límite; el stop-loss y el
        take-profit al comprar (al vender se editan en la posición)."""
        limite = self._tipo.obtener() == TipoOrden.LIMITE.value
        compra = self.lado() == LadoOrden.COMPRA
        self._entrada_limite.configure(state="normal" if limite else "disabled")
        for entrada in (self._entrada_stop_loss, self._entrada_take_profit, self._entrada_riesgo):
            entrada.configure(state="normal" if compra else "disabled")
        for boton in (self._boton_stop, self._boton_calcular):    # la calculadora es para compras
            boton.configure(state="normal" if compra else "disabled")
        self._est_titulos["precio"].configure(text="Precio límite" if limite else "Precio de ejecución")

    def _fijar_reparto(self) -> None:
        """Al abrir, el gráfico se lleva la mayor parte del alto (el borde se puede arrastrar)."""
        try:
            alto = self._derecha.winfo_height()
            if alto > 1:
                self._derecha.sashpos(0, int(alto * _PROPORCION_GRAFICO))
        except Exception:   # la ventana aún no tiene tamaño; el reparto por pesos queda igual
            pass

    def _actualizar_botones(self) -> None:
        libre = not self._boton_enviar.ocupado
        elegida = self._tabla_posiciones.seleccionado() in self._posiciones
        self._boton_cerrar.configure(state="normal" if libre and elegida else "disabled")
        self._boton_proteccion.configure(state="normal" if libre and elegida else "disabled")
        self._boton_cerrar_todas.configure(state="normal" if libre and self._posiciones else "disabled")
        self._boton_cancelar.configure(
            state="normal" if libre and self._tabla_pendientes.seleccionado() in self._pendientes else "disabled")

    # --------------------------------------------------------- eventos de la UI
    def _pulsar_activo(self) -> None:
        self._nota_riesgo.configure(text="")
        if self._al_elegir_activo:
            self._al_elegir_activo()

    def _pulsar_lado(self) -> None:
        self._actualizar_lado()
        self._actualizar_campos()
        self._pulsar_orden()

    def _pulsar_tipo(self) -> None:
        self._actualizar_campos()
        self._pulsar_orden()

    def _pulsar_orden(self) -> None:
        if self._al_cambiar_orden:
            self._al_cambiar_orden()

    def _pulsar_porcentaje(self, porcentaje_elegido: int) -> None:
        if self._al_porcentaje:
            self._al_porcentaje(porcentaje_elegido)

    def _pulsar_enviar(self) -> None:
        if self._al_enviar:
            self._al_enviar()

    def _pulsar_cerrar(self) -> None:
        if self._al_cerrar_posicion:
            self._al_cerrar_posicion()

    def _pulsar_cerrar_todas(self) -> None:
        if self._al_cerrar_todas:
            self._al_cerrar_todas()

    def _pulsar_sugerir_stop(self) -> None:
        if self._al_sugerir_stop:
            self._al_sugerir_stop()

    def _pulsar_calcular_cantidad(self) -> None:
        if self._al_calcular_cantidad:
            self._al_calcular_cantidad()

    def _pulsar_cancelar(self) -> None:
        if self._al_cancelar_orden:
            self._al_cancelar_orden()

    def _pulsar_guardar_proteccion(self, id_activo: int, stop_loss: str, take_profit: str) -> None:
        if self._al_guardar_proteccion:
            self._al_guardar_proteccion(id_activo, stop_loss, take_profit)
