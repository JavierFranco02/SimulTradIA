-- =====================================================================
-- SIMULTRADIA · OPERAR, fase 2: órdenes límite, stop-loss y take-profit (PostgreSQL 9.3)
-- =====================================================================
-- Agrega columnas a ordenes y posiciones (ya creadas por operar.sql) y un índice.
--
-- Ejecutar UNA vez, desde la carpeta del proyecto:
--   psql -d simulador_trading -v ON_ERROR_STOP=1 -f database/operar_fase2.sql
-- Después puedes borrar este archivo.
--
--   ordenes.precio_limite   precio de una orden límite (compra: baja hasta él; venta: sube hasta él)
--   ordenes.stop_loss / take_profit   niveles que se le ponen a la posición cuando una compra límite se ejecuta
--   ordenes.motivo_rechazo  por qué una orden pendiente no pudo ejecutarse (saldo insuficiente...)
--   ordenes.cancelada_en    cuándo la canceló el usuario
--   posiciones.stop_loss / take_profit   vende todo si el precio cae hasta el primero o sube hasta el segundo
-- =====================================================================
BEGIN;

ALTER TABLE ordenes ADD COLUMN precio_limite  NUMERIC(20,8) CHECK (precio_limite > 0);
ALTER TABLE ordenes ADD COLUMN stop_loss      NUMERIC(20,8) CHECK (stop_loss > 0);
ALTER TABLE ordenes ADD COLUMN take_profit    NUMERIC(20,8) CHECK (take_profit > 0);
ALTER TABLE ordenes ADD COLUMN motivo_rechazo TEXT;
ALTER TABLE ordenes ADD COLUMN cancelada_en   TIMESTAMPTZ;
ALTER TABLE ordenes ADD CONSTRAINT ck_orden_limite
    CHECK (tipo <> 'limite' OR precio_limite IS NOT NULL);

ALTER TABLE posiciones ADD COLUMN stop_loss   NUMERIC(20,8) CHECK (stop_loss > 0);
ALTER TABLE posiciones ADD COLUMN take_profit NUMERIC(20,8) CHECK (take_profit > 0);

-- El worker solo revisa las órdenes pendientes
CREATE INDEX idx_ordenes_pendientes ON ordenes (id_activo) WHERE estado = 'pendiente';

COMMIT;
