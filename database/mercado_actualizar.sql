-- =====================================================================
-- SIMULTRADIA · Actualiza el módulo MERCADO de la versión "solo criptomonedas" a la actual
-- =====================================================================
-- Úsalo UNA vez, si ya habías ejecutado el mercado.sql anterior:
--   psql -d simulador_trading -v ON_ERROR_STOP=1 -f database/mercado_actualizar.sql
-- Después puedes borrar este archivo. Hace tres cosas:
--   1. Crea la tabla fuentes_datos (Binance y Yahoo Finance) y le agrega id_fuente a activos.
--   2. Deja solo 5 criptomonedas (BTC, ETH, BNB, SOL, XRP). BORRA las otras 15 con sus precios:
--      eran datos de prueba y nada las usa todavía. (El administrador puede volver a agregarlas.)
--   3. Agrega 25 activos: 5 acciones, 5 ETF, 5 divisas, 5 índices y 5 bonos.
-- =====================================================================
BEGIN;

CREATE TABLE fuentes_datos (
    id_fuente  BIGSERIAL PRIMARY KEY,
    nombre     VARCHAR(80) NOT NULL UNIQUE,
    activa     BOOLEAN     NOT NULL DEFAULT TRUE
);
INSERT INTO fuentes_datos (nombre) VALUES ('Binance'), ('Yahoo Finance');

ALTER TABLE activos ADD COLUMN id_fuente BIGINT REFERENCES fuentes_datos(id_fuente);
UPDATE activos SET id_fuente = (SELECT id_fuente FROM fuentes_datos WHERE nombre = 'Binance');
ALTER TABLE activos ALTER COLUMN id_fuente SET NOT NULL;

DELETE FROM activos
WHERE ticker NOT IN ('BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT');

INSERT INTO activos (ticker, nombre, tipo, moneda, id_fuente) VALUES
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
