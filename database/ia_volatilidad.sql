-- =====================================================================
-- SIMULTRADIA · IA (predicción de volatilidad) · PostgreSQL 9.3
-- =====================================================================
-- Agrega UNA tabla y UN tipo. Ejecutar una vez sobre la base que ya tiene database/ia.sql:
--
--   psql -d simulador_trading -v ON_ERROR_STOP=1 -f database/ia_volatilidad.sql
--
-- Las tablas de dirección (predicciones_direccion, explicaciones_prediccion) NO se tocan:
-- quedan guardadas para el módulo experimental. El modelo de volatilidad reutiliza
-- modelos_ia (tipo 'volatilidad', nombre 'volatilidad_1d') y entrenamientos_modelo.
-- Los rangos son fracciones del precio (0.0230 = 2,3 %); fechas en UTC.
-- =====================================================================

BEGIN;

CREATE TYPE nivel_volatilidad AS ENUM ('baja', 'normal', 'alta');

CREATE TABLE predicciones_volatilidad (
    id_prediccion     BIGSERIAL PRIMARY KEY,
    id_activo         BIGINT            NOT NULL REFERENCES activos(id_activo) ON DELETE CASCADE,
    id_modelo         BIGINT            NOT NULL REFERENCES modelos_ia(id_modelo),
    generada_en       TIMESTAMPTZ       NOT NULL DEFAULT now(),
    fecha_objetivo    TIMESTAMPTZ       NOT NULL,            -- cuándo se podrá evaluar
    precio_referencia NUMERIC(20,8)     NOT NULL,            -- cierre de la última vela diaria cerrada
    rango_predicho    NUMERIC(10,6)     NOT NULL CHECK (rango_predicho > 0),
    rango_bajo        NUMERIC(10,6)     NOT NULL CHECK (rango_bajo > 0),   -- intervalo de ~80 %
    rango_alto        NUMERIC(10,6)     NOT NULL CHECK (rango_alto > 0),
    rango_hoy         NUMERIC(10,6)     NOT NULL,            -- rango de la última vela cerrada (la base «repetir hoy»)
    rango_normal      NUMERIC(10,6)     NOT NULL,            -- media de los últimos 20 rangos (la base «normal»)
    umbral_bajo       NUMERIC(10,6)     NOT NULL,            -- percentil 25 de los últimos 90 rangos
    umbral_alto       NUMERIC(10,6)     NOT NULL,            -- percentil 75
    nivel             nivel_volatilidad NOT NULL,            -- nivel esperado
    factores          JSON              NOT NULL DEFAULT '[]', -- [{"factor","aporte","valor"}]
    -- Se completan cuando existe la vela objetivo:
    rango_real        NUMERIC(10,6),
    nivel_real        nivel_volatilidad,
    acierto_nivel     BOOLEAN,
    evaluada_en       TIMESTAMPTZ,
    UNIQUE (id_activo, id_modelo, generada_en)
);
-- UNA predicción por día (UTC) para cada activo y modelo
CREATE UNIQUE INDEX uq_pred_vol_una_por_dia
    ON predicciones_volatilidad (id_activo, id_modelo, ((generada_en AT TIME ZONE 'UTC')::date));
CREATE INDEX idx_pred_vol_activo ON predicciones_volatilidad (id_activo, generada_en DESC);
-- Para el proceso que evalúa las vencidas
CREATE INDEX idx_pred_vol_pendientes ON predicciones_volatilidad (fecha_objetivo) WHERE rango_real IS NULL;

COMMIT;
