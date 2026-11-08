"""Reglas puras de operar: a qué precio se ejecuta una orden, cuánto cuesta y qué queda después.

Las usan Operar y, más adelante, Replay, Backtesting y el worker: por eso hay UNA sola
implementación. Python puro (sin BD, sin tkinter, sin red). Dinero con Decimal.

Comisión: porcentaje del monto de la operación; se cobra al comprar y al vender.
Ganancia de una venta = (precio de salida - precio promedio de entrada) x cantidad
                        - la parte de la comisión de compra que corresponde a lo vendido
                        - la comisión de la venta.
Ganancia NO realizada de una posición = (precio de mercado - precio promedio) x cantidad
                        (lo que se ganaría o perdería si se vendiera ahora, sin contar comisiones).
"""
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import ROUND_DOWN, ROUND_HALF_UP, ROUND_UP, Decimal
from typing import Optional, Tuple

from simultradia.domain.entities.operacion_cerrada_entity import OperacionCerrada
from simultradia.domain.entities.posicion_entity import Posicion
from simultradia.domain.enums import LadoOrden, TipoOrden

_CIEN = Decimal(100)
_DINERO = Decimal(1).scaleb(-4)     # NUMERIC(20,4)
_PRECIO = Decimal(1).scaleb(-8)     # NUMERIC(20,8)
_CANTIDAD = Decimal(1).scaleb(-10)  # NUMERIC(28,10)
_TOPE_CANTIDAD = Decimal(10) ** 12 - 1


def redondear_dinero(valor: Decimal) -> Decimal:
    return valor.quantize(_DINERO, rounding=ROUND_HALF_UP)


def precio_de_ejecucion(precio: Decimal, lado: LadoOrden, deslizamiento_pct: Decimal) -> Decimal:
    """El precio al que se ejecuta una orden a mercado: el del mercado, un poco peor para quien opera
    (la compra paga más y la venta recibe menos) cuando la cuenta tiene deslizamiento."""
    factor = deslizamiento_pct / _CIEN
    ejecutado = precio * (1 + factor) if lado == LadoOrden.COMPRA else precio * (1 - factor)
    return ejecutado.quantize(_PRECIO, rounding=ROUND_HALF_UP)


def calcular_comision(monto: Decimal, comision_pct: Decimal) -> Decimal:
    return redondear_dinero(monto * comision_pct / _CIEN)


def calcular_compra(cantidad: Decimal, precio: Decimal, comision_pct: Decimal) -> Tuple[Decimal, Decimal]:
    """(monto, comisión) de comprar `cantidad` a `precio`. Lo que se descuenta del saldo es la suma."""
    monto = redondear_dinero(cantidad * precio)
    return monto, calcular_comision(monto, comision_pct)


def cantidad_maxima_compra(saldo: Decimal, precio: Decimal, comision_pct: Decimal) -> Decimal:
    """La mayor cantidad que alcanza a comprar el saldo, comisión incluida (`precio` es el de ejecución)."""
    if saldo <= 0 or precio <= 0:
        return Decimal(0)
    cruda = min(saldo / (precio * (1 + comision_pct / _CIEN)), _TOPE_CANTIDAD)
    cantidad = cruda.quantize(_CANTIDAD, rounding=ROUND_DOWN)
    for _ in range(5):   # el redondeo del dinero puede pasarse por centavos: se corrige
        monto, comision = calcular_compra(cantidad, precio, comision_pct)
        exceso = monto + comision - saldo
        if exceso <= 0:
            break
        cantidad -= (exceso / precio).quantize(_CANTIDAD, rounding=ROUND_UP) + _CANTIDAD
    return max(cantidad, Decimal(0))


def aplicar_compra(posicion: Posicion, cantidad: Decimal, precio: Decimal, comision: Decimal) -> Posicion:
    """La posición después de comprar. Si aún no se tenía el activo, se parte de una con cantidad 0.
    El precio promedio es ponderado y no incluye comisiones (estas se acumulan aparte)."""
    total = posicion.cantidad + cantidad
    promedio = (posicion.cantidad * posicion.precio_promedio_entrada + cantidad * precio) / total
    return replace(
        posicion,
        cantidad=total,
        precio_promedio_entrada=promedio.quantize(_PRECIO, rounding=ROUND_HALF_UP),
        comisiones_pagadas=posicion.comisiones_pagadas + comision,
    )


@dataclass(frozen=True)
class ResultadoVenta:
    posicion: Optional[Posicion]     # lo que queda; None si se vendió todo
    ingreso_neto: Decimal            # lo que entra al saldo (ya sin la comisión de la venta)
    comision: Decimal                # comisión de la venta
    operacion: OperacionCerrada


def aplicar_venta(posicion: Posicion, cantidad: Decimal, precio: Decimal, comision_pct: Decimal,
                  ahora: datetime) -> ResultadoVenta:
    """Vende `cantidad` (que no puede superar la de la posición; eso lo comprueba el servicio)."""
    bruto = redondear_dinero(cantidad * precio)
    comision_venta = calcular_comision(bruto, comision_pct)
    comision_entrada = redondear_dinero(posicion.comisiones_pagadas * (cantidad / posicion.cantidad))
    comisiones = comision_entrada + comision_venta
    ganancia = redondear_dinero((precio - posicion.precio_promedio_entrada) * cantidad) - comisiones

    resto = posicion.cantidad - cantidad
    restante = None if resto == 0 else replace(
        posicion, cantidad=resto, comisiones_pagadas=posicion.comisiones_pagadas - comision_entrada)
    operacion = OperacionCerrada(
        id_cuenta=posicion.id_cuenta, id_activo=posicion.id_activo, cantidad=cantidad,
        precio_entrada=posicion.precio_promedio_entrada, precio_salida=precio,
        comisiones=comisiones, ganancia_realizada=ganancia,
        abierta_en=posicion.abierta_en, cerrada_en=ahora)
    return ResultadoVenta(restante, bruto - comision_venta, comision_venta, operacion)


@dataclass(frozen=True)
class Estimacion:
    """Lo que costaría (o dejaría) una orden, antes de enviarla."""
    precio: Decimal                  # de ejecución, ya con el deslizamiento
    monto: Decimal
    comision: Decimal
    total: Decimal                   # compra: lo que se paga (monto + comisión); venta: lo que se recibe
    saldo_despues: Decimal
    ganancia: Optional[Decimal]      # solo en ventas: ganancia realizada, ya sin comisiones


def estimar_orden(lado: LadoOrden, cantidad: Decimal, precio_mercado: Decimal, saldo: Decimal,
                  posicion: Optional[Posicion], comision_pct: Decimal, deslizamiento_pct: Decimal,
                  ahora: datetime) -> Estimacion:
    """Calcula una orden a mercado sin ejecutarla. No valida (saldo, cantidad en posición): eso es del servicio.
    Para vender, `posicion` debe existir y tener al menos `cantidad`."""
    precio = precio_de_ejecucion(precio_mercado, lado, deslizamiento_pct)
    if lado == LadoOrden.COMPRA:
        monto, comision = calcular_compra(cantidad, precio, comision_pct)
        total = monto + comision
        return Estimacion(precio, monto, comision, total, saldo - total, None)
    r = aplicar_venta(posicion, cantidad, precio, comision_pct, ahora)
    return Estimacion(precio, redondear_dinero(cantidad * precio), r.comision, r.ingreso_neto,
                      saldo + r.ingreso_neto, r.operacion.ganancia_realizada)


def valorar_posicion(posicion: Posicion, precio_actual: Decimal) -> Tuple[Decimal, Decimal, Decimal]:
    """(valor de mercado, ganancia no realizada, ganancia en %) de una posición al precio de ahora."""
    valor = redondear_dinero(posicion.cantidad * precio_actual)
    costo = redondear_dinero(posicion.cantidad * posicion.precio_promedio_entrada)
    ganancia = valor - costo
    porcentaje = (ganancia / costo * _CIEN).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP) if costo else Decimal(0)
    return valor, ganancia, porcentaje


def limite_alcanzado(lado: LadoOrden, precio_limite: Decimal, precio: Decimal) -> bool:
    """¿Ya se puede ejecutar una orden límite? La compra espera a que el precio BAJE hasta el límite;
    la venta, a que SUBA hasta él."""
    return precio <= precio_limite if lado == LadoOrden.COMPRA else precio >= precio_limite


def proteccion_alcanzada(stop_loss: Optional[Decimal], take_profit: Optional[Decimal],
                         precio: Decimal) -> Optional[TipoOrden]:
    """Qué protección de una posición se dispara con este precio (None si ninguna): el stop-loss cuando
    el precio cae hasta él o por debajo; el take-profit cuando sube hasta él o por encima."""
    if stop_loss is not None and precio <= stop_loss:
        return TipoOrden.STOP_LOSS
    if take_profit is not None and precio >= take_profit:
        return TipoOrden.TAKE_PROFIT
    return None
