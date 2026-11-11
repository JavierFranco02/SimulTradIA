-- =====================================================================
-- SIMULTRADIA · Tablas del módulo OPERAR (PostgreSQL 9.3)
-- =====================================================================
-- Órdenes a mercado (comprar y vender al precio actual). Crea:
--   ordenes · ejecuciones · posiciones · operaciones_cerradas
--   (+ los tipos lado_orden, tipo_orden y estado_orden)
-- Requiere que ya existan cuentas_simuladas y activos.
--
-- Ejecutar UNA vez, desde la carpeta del proyecto:
--   psql -d simulador_trading -v ON_ERROR_STOP=1 -f database/operar.sql
-- Si ya habías ejecutado schema.sql completo, estas tablas y tipos ya existen: no la corras.
--
-- Solo llevan las columnas que se usan hoy. Las de las órdenes límite, stop-loss y take-profit
-- (precio_limite, precio_disparo, vence_en...) se agregan después con ALTER TABLE ... ADD COLUMN.
-- Los tipos enumerados SÍ traen ya todos sus valores: en PostgreSQL 9.3 agregar uno a un ENUM
-- no se puede hacer dentro de una transacción.
-- =====================================================================
BEGIN;

CREATE TYPE lado_orden   AS ENUM ('compra', 'venta');
CREATE TYPE tipo_orden   AS ENUM ('mercado', 'limite', 'stop_loss', 'take_profit', 'stop_limite');
CREATE TYPE estado_orden AS ENUM ('pendiente', 'parcial', 'ejecutada', 'cancelada', 'rechazada', 'expirada');

-- Lo que el usuario pidió. Las órdenes a mercado nacen y quedan 'ejecutada' en el acto.
CREATE TABLE ordenes (
    id_orden         BIGSERIAL PRIMARY KEY,
    id_cuenta        BIGINT         NOT NULL REFERENCES cuentas_simuladas(id_cuenta) ON DELETE CASCADE,
    id_activo        BIGINT         NOT NULL REFERENCES activos(id_activo),
    lado             lado_orden     NOT NULL,
    tipo             tipo_orden     NOT NULL DEFAULT 'mercado',
    estado           estado_orden   NOT NULL DEFAULT 'pendiente',
    cantidad         NUMERIC(28,10) NOT NULL CHECK (cantidad > 0),
    precio_promedio  NUMERIC(20,8),                          -- a qué precio se ejecutó
    comision_total   NUMERIC(20,4)  NOT NULL DEFAULT 0 CHECK (comision_total >= 0),
    creada_en        TIMESTAMPTZ    NOT NULL DEFAULT now(),
    ejecutada_en     TIMESTAMPTZ
);
CREATE INDEX idx_ordenes_cuenta ON ordenes (id_cuenta, creada_en DESC);

-- Lo que realmente ocurrió: el historial sale de aquí.
CREATE TABLE ejecuciones (
    id_ejecucion  BIGSERIAL PRIMARY KEY,
    id_orden      BIGINT         NOT NULL REFERENCES ordenes(id_orden) ON DELETE CASCADE,
    id_cuenta     BIGINT         NOT NULL REFERENCES cuentas_simuladas(id_cuenta) ON DELETE CASCADE,
    id_activo     BIGINT         NOT NULL REFERENCES activos(id_activo),
    lado          lado_orden     NOT NULL,
    cantidad      NUMERIC(28,10) NOT NULL CHECK (cantidad > 0),
    precio        NUMERIC(20,8)  NOT NULL CHECK (precio > 0),   -- ya con el deslizamiento aplicado
    comision      NUMERIC(20,4)  NOT NULL DEFAULT 0 CHECK (comision >= 0),
    ejecutada_en  TIMESTAMPTZ    NOT NULL DEFAULT now()
);
CREATE INDEX idx_ejecuciones_cuenta ON ejecuciones (id_cuenta, ejecutada_en DESC);
CREATE INDEX idx_ejecuciones_orden  ON ejecuciones (id_orden);

-- Lo que posee ahora (solo posiciones largas). Al vender todo, la aplicación borra la fila.
-- comisiones_pagadas = lo pagado en comisiones al comprar lo que aún se tiene (para calcular
-- la ganancia real al vender).
CREATE TABLE posiciones (
    id_posicion              BIGSERIAL PRIMARY KEY,
    id_cuenta                BIGINT         NOT NULL REFERENCES cuentas_simuladas(id_cuenta) ON DELETE CASCADE,
    id_activo                BIGINT         NOT NULL REFERENCES activos(id_activo),
    cantidad                 NUMERIC(28,10) NOT NULL CHECK (cantidad > 0),
    precio_promedio_entrada  NUMERIC(20,8)  NOT NULL CHECK (precio_promedio_entrada > 0),
    comisiones_pagadas       NUMERIC(20,4)  NOT NULL DEFAULT 0 CHECK (comisiones_pagadas >= 0),
    abierta_en               TIMESTAMPTZ    NOT NULL DEFAULT now(),
    UNIQUE (id_cuenta, id_activo)
);

-- Una fila por cada VENTA (total o parcial): lo vendido, a qué precio entró y salió, y la ganancia.
-- Alimenta el % de aciertos, la ganancia promedio y el coach.
CREATE TABLE operaciones_cerradas (
    id_operacion_cerrada  BIGSERIAL PRIMARY KEY,
    id_cuenta             BIGINT         NOT NULL REFERENCES cuentas_simuladas(id_cuenta) ON DELETE CASCADE,
    id_activo             BIGINT         NOT NULL REFERENCES activos(id_activo),
    cantidad              NUMERIC(28,10) NOT NULL CHECK (cantidad > 0),
    precio_entrada        NUMERIC(20,8)  NOT NULL,
    precio_salida         NUMERIC(20,8)  NOT NULL,
    comisiones            NUMERIC(20,4)  NOT NULL DEFAULT 0,      -- las de entrada (proporcional) + la de salida
    ganancia_realizada    NUMERIC(20,4)  NOT NULL,                -- ya descontadas las comisiones
    abierta_en            TIMESTAMPTZ    NOT NULL,
    cerrada_en            TIMESTAMPTZ    NOT NULL
);
CREATE INDEX idx_op_cerradas_cuenta ON operaciones_cerradas (id_cuenta, cerrada_en DESC);

COMMIT;
