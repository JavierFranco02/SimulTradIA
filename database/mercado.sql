-- =====================================================================
-- SIMULTRADIA · Tablas del módulo MERCADO (PostgreSQL 9.3)
-- =====================================================================
-- Crea lo que necesitan Mercado, el gráfico y la ingesta de datos:
--   fuentes_datos · activos · precios_velas · cotizaciones_actuales
--   (+ los tipos tipo_activo e intervalo_vela)
-- y carga 30 activos: 5 de cada categoría (cripto, acción, ETF, divisa, índice y bono).
--
-- Ejecutar UNA vez, desde la carpeta del proyecto, sobre una base SIN estas tablas:
--   psql -d simulador_trading -v ON_ERROR_STOP=1 -f database/mercado.sql
--
-- Si ya habías ejecutado la versión anterior de este archivo (solo criptomonedas), usa
-- database/mercado_actualizar.sql en su lugar. Si ya habías ejecutado schema.sql completo, estos
-- tipos y tablas ya existen: no la corras.
--
-- fuentes_datos.nombre es la clave que enlaza cada fuente con su cliente en el código
-- (clients/): no lo cambies. Los pares en USDT de Binance se tratan como dólares.
-- Los bonos se representan con ETF de bonos: un rendimiento (%) no es un precio que se opere.
-- =====================================================================
BEGIN;

CREATE TYPE tipo_activo    AS ENUM ('accion', 'cripto', 'etf', 'divisa', 'indice', 'bono');
CREATE TYPE intervalo_vela AS ENUM ('1m', '5m', '15m', '1h', '4h', '1d', '1w');

CREATE TABLE fuentes_datos (
    id_fuente  BIGSERIAL PRIMARY KEY,
    nombre     VARCHAR(80) NOT NULL UNIQUE,             -- Binance, Yahoo Finance
    activa     BOOLEAN     NOT NULL DEFAULT TRUE        -- FALSE = sus activos dejan de actualizarse
);

CREATE TABLE activos (
    id_activo  BIGSERIAL PRIMARY KEY,
    ticker     VARCHAR(20)  NOT NULL UNIQUE,            -- BTC/USDT, AAPL, EURUSD=X, ^GSPC
    nombre     VARCHAR(150) NOT NULL,
    tipo       tipo_activo  NOT NULL,
    moneda     CHAR(3)      NOT NULL DEFAULT 'USD',
    activo     BOOLEAN      NOT NULL DEFAULT TRUE,      -- FALSE = ya no se actualiza ni se muestra
    id_fuente  BIGINT       NOT NULL REFERENCES fuentes_datos(id_fuente),
    creado_en  TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- Velas OHLCV históricas. Es la tabla que más crece.
CREATE TABLE precios_velas (
    id_activo  BIGINT         NOT NULL REFERENCES activos(id_activo) ON DELETE CASCADE,
    intervalo  intervalo_vela NOT NULL,
    momento    TIMESTAMPTZ    NOT NULL,                 -- inicio de la vela (UTC)
    apertura   NUMERIC(20,8)  NOT NULL,
    maximo     NUMERIC(20,8)  NOT NULL,
    minimo     NUMERIC(20,8)  NOT NULL,
    cierre     NUMERIC(20,8)  NOT NULL,
    volumen    NUMERIC(28,4)  NOT NULL DEFAULT 0,
    PRIMARY KEY (id_activo, intervalo, momento),
    CHECK (maximo >= minimo),
    CHECK (maximo >= apertura AND maximo >= cierre),
    CHECK (minimo <= apertura AND minimo <= cierre),
    CHECK (volumen >= 0)
);

-- Último precio de cada activo (UNA fila por activo; no depende del intervalo del gráfico)
CREATE TABLE cotizaciones_actuales (
    id_activo         BIGINT PRIMARY KEY REFERENCES activos(id_activo) ON DELETE CASCADE,
    precio            NUMERIC(20,8) NOT NULL,
    cierre_anterior   NUMERIC(20,8),                    -- precio del día (o de las 24 h) anterior
    variacion_pct_dia NUMERIC(12,4),                    -- 5.25 = 5,25 %
    maximo_dia        NUMERIC(20,8),
    minimo_dia        NUMERIC(20,8),
    volumen_dia       NUMERIC(28,4),                    -- en dólares
    actualizado_en    TIMESTAMPTZ   NOT NULL DEFAULT now()
);

INSERT INTO fuentes_datos (nombre) VALUES ('Binance'), ('Yahoo Finance');

INSERT INTO activos (ticker, nombre, tipo, moneda, id_fuente) VALUES
    ('BTC/USDT', 'Bitcoin', 'cripto', 'USD', (SELECT id_fuente FROM fuentes_datos WHERE nombre = 'Binance')),
    ('ETH/USDT', 'Ethereum', 'cripto', 'USD', (SELECT id_fuente FROM fuentes_datos WHERE nombre = 'Binance')),
    ('BNB/USDT', 'BNB', 'cripto', 'USD', (SELECT id_fuente FROM fuentes_datos WHERE nombre = 'Binance')),
    ('SOL/USDT', 'Solana', 'cripto', 'USD', (SELECT id_fuente FROM fuentes_datos WHERE nombre = 'Binance')),
    ('XRP/USDT', 'XRP', 'cripto', 'USD', (SELECT id_fuente FROM fuentes_datos WHERE nombre = 'Binance')),
    ('AAPL', 'Apple', 'accion', 'USD', (SELECT id_fuente FROM fuentes_datos WHERE nombre = 'Yahoo Finance')),
    ('MSFT', 'Microsoft', 'accion', 'USD', (SELECT id_fuente FROM fuentes_datos WHERE nombre = 'Yahoo Finance')),
    ('NVDA', 'NVIDIA', 'accion', 'USD', (SELECT id_fuente FROM fuentes_datos WHERE nombre = 'Yahoo Finance')),
    ('TSLA', 'Tesla', 'accion', 'USD', (SELECT id_fuente FROM fuentes_datos WHERE nombre = 'Yahoo Finance')),
    ('AMZN', 'Amazon', 'accion', 'USD', (SELECT id_fuente FROM fuentes_datos WHERE nombre = 'Yahoo Finance')),
    ('SPY', 'SPDR S&P 500 ETF', 'etf', 'USD', (SELECT id_fuente FROM fuentes_datos WHERE nombre = 'Yahoo Finance')),
    ('QQQ', 'Invesco QQQ (Nasdaq 100)', 'etf', 'USD', (SELECT id_fuente FROM fuentes_datos WHERE nombre = 'Yahoo Finance')),
    ('VTI', 'Vanguard Total Stock Market', 'etf', 'USD', (SELECT id_fuente FROM fuentes_datos WHERE nombre = 'Yahoo Finance')),
    ('GLD', 'SPDR Gold Shares (oro)', 'etf', 'USD', (SELECT id_fuente FROM fuentes_datos WHERE nombre = 'Yahoo Finance')),
    ('IWM', 'iShares Russell 2000', 'etf', 'USD', (SELECT id_fuente FROM fuentes_datos WHERE nombre = 'Yahoo Finance')),
    ('EURUSD=X', 'Euro / Dólar', 'divisa', 'USD', (SELECT id_fuente FROM fuentes_datos WHERE nombre = 'Yahoo Finance')),
    ('GBPUSD=X', 'Libra / Dólar', 'divisa', 'USD', (SELECT id_fuente FROM fuentes_datos WHERE nombre = 'Yahoo Finance')),
    ('USDJPY=X', 'Dólar / Yen', 'divisa', 'JPY', (SELECT id_fuente FROM fuentes_datos WHERE nombre = 'Yahoo Finance')),
    ('AUDUSD=X', 'Dólar australiano / Dólar', 'divisa', 'USD', (SELECT id_fuente FROM fuentes_datos WHERE nombre = 'Yahoo Finance')),
    ('USDCAD=X', 'Dólar / Dólar canadiense', 'divisa', 'CAD', (SELECT id_fuente FROM fuentes_datos WHERE nombre = 'Yahoo Finance')),
    ('^GSPC', 'S&P 500', 'indice', 'USD', (SELECT id_fuente FROM fuentes_datos WHERE nombre = 'Yahoo Finance')),
    ('^IXIC', 'Nasdaq Composite', 'indice', 'USD', (SELECT id_fuente FROM fuentes_datos WHERE nombre = 'Yahoo Finance')),
    ('^DJI', 'Dow Jones', 'indice', 'USD', (SELECT id_fuente FROM fuentes_datos WHERE nombre = 'Yahoo Finance')),
    ('^GDAXI', 'DAX (Alemania)', 'indice', 'EUR', (SELECT id_fuente FROM fuentes_datos WHERE nombre = 'Yahoo Finance')),
    ('^N225', 'Nikkei 225 (Japón)', 'indice', 'JPY', (SELECT id_fuente FROM fuentes_datos WHERE nombre = 'Yahoo Finance')),
    ('TLT', 'Bonos del Tesoro 20+ años', 'bono', 'USD', (SELECT id_fuente FROM fuentes_datos WHERE nombre = 'Yahoo Finance')),
    ('IEF', 'Bonos del Tesoro 7-10 años', 'bono', 'USD', (SELECT id_fuente FROM fuentes_datos WHERE nombre = 'Yahoo Finance')),
    ('SHY', 'Bonos del Tesoro 1-3 años', 'bono', 'USD', (SELECT id_fuente FROM fuentes_datos WHERE nombre = 'Yahoo Finance')),
    ('BND', 'Bonos totales EE. UU.', 'bono', 'USD', (SELECT id_fuente FROM fuentes_datos WHERE nombre = 'Yahoo Finance')),
    ('LQD', 'Bonos corporativos', 'bono', 'USD', (SELECT id_fuente FROM fuentes_datos WHERE nombre = 'Yahoo Finance'));

COMMIT;
