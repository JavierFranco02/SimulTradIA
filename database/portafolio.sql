-- Portafolio: foto del patrimonio de cada cuenta, una fila por minuto (lo de más de 7 días se compacta a una por hora).
-- Ejecutar UNA vez sobre la base real (después de operar.sql):
--   psql -U postgres -d simulador_trading -v ON_ERROR_STOP=1 -f database/portafolio.sql
--
-- Más chica que la de la guía (schema.sql): sin rentabilidad_pct ni drawdown_pct, porque se
-- calculan al leer la curva (así no hay datos repetidos que mantener sincronizados).
-- El worker guarda una fila por minuto (y la pantalla Portafolio, la del minuto en que se abre).
BEGIN;

CREATE TABLE snapshots_portafolio (
    id_cuenta        bigint        NOT NULL REFERENCES cuentas_simuladas(id_cuenta) ON DELETE CASCADE,
    momento          timestamp with time zone NOT NULL,        -- inicio del minuto (UTC)
    saldo_disponible numeric(20,4) NOT NULL,
    valor_posiciones numeric(20,4) NOT NULL,
    patrimonio_total numeric(20,4) NOT NULL,                   -- saldo + posiciones
    PRIMARY KEY (id_cuenta, momento)
);

ALTER TABLE snapshots_portafolio OWNER TO postgres;

COMMIT;
