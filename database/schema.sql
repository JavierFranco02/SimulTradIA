-- =====================================================================
-- SIMULTRADIA  ·  Esquema PostgreSQL 9.3 (corre también en versiones más nuevas)
-- =====================================================================
-- ESQUEMA DE GUÍA: muestra lo que la base podría llegar a tener. La base real se
-- ajusta según cada módulo; no es la fuente de verdad.
--
-- Pensado para ejecutarse sobre una base de datos VACÍA, desde la carpeta del proyecto:
--
--   createdb simulador_trading
--   psql -d simulador_trading -v ON_ERROR_STOP=1 -f database/schema.sql
--
-- Todo el script corre dentro de una transacción: si algo falla, no queda nada a medias.
--
-- PostgreSQL 9.3: BIGSERIAL (no IDENTITY), JSON (no JSONB), COUNT(CASE WHEN ...)
-- (no FILTER), EXECUTE PROCEDURE en triggers, sin ON CONFLICT ni TimescaleDB.
--
-- Módulos:  1 Cuenta · 2 Mercado · 4 Watchlists · 5 Alertas · 6 Operar · 7 Portafolio
--           8 Backtesting · 9 IA · 10 Aprendizaje (glosario y replay) · 12 Administración
-- Descartados: social, tutoriales/retos, chat, datos fundamentales, calendario,
--              configuraciones de gráfico y posiciones cortas.
--
-- Convenciones:
--   · Claves primarias:  id_<entidad>  (usuarios.id_usuario, activos.id_activo...).
--     Las claves foráneas llevan el MISMO nombre que la clave a la que apuntan
--     (cuentas_simuladas.id_usuario -> usuarios.id_usuario).
--   · Dinero:        NUMERIC(20,4)
--   · Precios:       NUMERIC(20,8)  (soporta criptos de precio muy bajo)
--   · Cantidades:    NUMERIC(28,10) (soporta fracciones de cripto)
--   · Porcentajes:   número "legible": 5.25 = 5,25 %
--   · Probabilidades de la IA: de 0 a 1
--   · Fechas/horas:  TIMESTAMPTZ (siempre en UTC desde la aplicación)
-- =====================================================================

BEGIN;

-- ---------------------------------------------------------------------
-- 0. TIPOS ENUMERADOS
-- ---------------------------------------------------------------------
CREATE TYPE rol_usuario          AS ENUM ('usuario', 'admin');
CREATE TYPE tipo_activo          AS ENUM ('accion', 'cripto', 'etf', 'divisa', 'indice', 'bono');
CREATE TYPE intervalo_vela       AS ENUM ('1m', '5m', '15m', '1h', '4h', '1d', '1w');
CREATE TYPE lado_orden           AS ENUM ('compra', 'venta');
CREATE TYPE tipo_orden           AS ENUM ('mercado', 'limite', 'stop_loss', 'take_profit', 'stop_limite');
CREATE TYPE estado_orden         AS ENUM ('pendiente', 'parcial', 'ejecutada', 'cancelada', 'rechazada', 'expirada');
CREATE TYPE tipo_alerta          AS ENUM ('precio', 'indicador', 'prediccion_ia');
CREATE TYPE condicion_alerta     AS ENUM ('mayor_que', 'menor_que', 'cruza_arriba', 'cruza_abajo');
CREATE TYPE estado_alerta        AS ENUM ('activa', 'disparada', 'pausada');
CREATE TYPE direccion_prediccion AS ENUM ('alcista', 'bajista', 'lateral');
CREATE TYPE regimen_mercado      AS ENUM ('tendencia_alcista', 'tendencia_bajista', 'lateral');
CREATE TYPE sentimiento_noticia  AS ENUM ('positivo', 'neutro', 'negativo');
CREATE TYPE nivel_riesgo         AS ENUM ('bajo', 'medio', 'alto');
CREATE TYPE tipo_modelo_ia       AS ENUM ('direccion', 'volatilidad', 'sentimiento', 'regimen');
CREATE TYPE estado_modelo        AS ENUM ('entrenando', 'activo', 'archivado', 'fallido');
CREATE TYPE estado_proceso       AS ENUM ('pendiente', 'ejecutando', 'completado', 'fallido');


-- =====================================================================
-- 1. CUENTA Y CONFIGURACIÓN
-- =====================================================================
CREATE TABLE usuarios (
    id_usuario                BIGSERIAL PRIMARY KEY,
    nombre            VARCHAR(100)      NOT NULL,
    email             VARCHAR(255)      NOT NULL,
    password_hash     TEXT              NOT NULL,          -- nunca la contraseña en texto plano
    rol               rol_usuario       NOT NULL DEFAULT 'usuario',
    activo            BOOLEAN           NOT NULL DEFAULT TRUE,
    ultimo_login_en   TIMESTAMPTZ,
    creado_en         TIMESTAMPTZ       NOT NULL DEFAULT now(),
    actualizado_en    TIMESTAMPTZ       NOT NULL DEFAULT now()
);
-- Email único sin distinguir mayúsculas/minúsculas
CREATE UNIQUE INDEX uq_usuarios_email ON usuarios (lower(email));

CREATE TABLE preferencias_usuario (
    id_usuario       BIGINT PRIMARY KEY REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
    tema             VARCHAR(10) NOT NULL DEFAULT 'claro'
                     CHECK (tema IN ('claro', 'oscuro', 'sistema')),
    moneda_preferida CHAR(3)     NOT NULL DEFAULT 'USD',
    idioma           VARCHAR(5)  NOT NULL DEFAULT 'es',
    notificar_email  BOOLEAN     NOT NULL DEFAULT TRUE,
    notificar_in_app BOOLEAN     NOT NULL DEFAULT TRUE,
    actualizado_en   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =====================================================================
-- 2. MERCADO (DATOS REALES)
-- =====================================================================
CREATE TABLE activos (
    id_activo          BIGSERIAL PRIMARY KEY,
    ticker      VARCHAR(20)  NOT NULL UNIQUE,              -- AAPL, BTC-USD, ^GSPC...
    nombre      VARCHAR(150) NOT NULL,
    tipo        tipo_activo  NOT NULL,
    bolsa       VARCHAR(50),                               -- NASDAQ, NYSE, Binance...
    moneda      CHAR(3)      NOT NULL DEFAULT 'USD',
    sector      VARCHAR(100),
    industria   VARCHAR(100),
    pais        VARCHAR(60),
    descripcion TEXT,
    logo_url    TEXT,
    activo      BOOLEAN      NOT NULL DEFAULT TRUE,        -- FALSE = ya no se actualiza/opera
    creado_en   TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX idx_activos_tipo   ON activos (tipo);
CREATE INDEX idx_activos_sector ON activos (sector);
-- Búsqueda rápida por nombre o ticker (prefijo)
CREATE INDEX idx_activos_nombre_lower ON activos (lower(nombre) text_pattern_ops);
CREATE INDEX idx_activos_ticker_lower ON activos (lower(ticker) text_pattern_ops);

-- Velas OHLCV históricas. Es la tabla que más va a crecer.
-- (Si algún día crece demasiado, en 9.3 la opción es el particionado por
--  herencia, por ejemplo una tabla hija por año. No hace falta al inicio.)
CREATE TABLE precios_velas (
    id_activo  BIGINT         NOT NULL REFERENCES activos(id_activo) ON DELETE CASCADE,
    intervalo  intervalo_vela NOT NULL,
    momento    TIMESTAMPTZ    NOT NULL,                    -- inicio de la vela
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

-- Última cotización de cada activo (caché que lee casi toda la app)
CREATE TABLE cotizaciones_actuales (
    id_activo         BIGINT PRIMARY KEY REFERENCES activos(id_activo) ON DELETE CASCADE,
    precio            NUMERIC(20,8) NOT NULL,
    cierre_anterior   NUMERIC(20,8),
    variacion_dia     NUMERIC(20,8),
    variacion_pct_dia NUMERIC(12,4),
    maximo_dia        NUMERIC(20,8),
    minimo_dia        NUMERIC(20,8),
    volumen_dia       NUMERIC(28,4),
    capitalizacion    NUMERIC(24,2),
    actualizado_en    TIMESTAMPTZ   NOT NULL DEFAULT now()
);
-- Para los listados "más ganadores / más perdedores / más volumen"
CREATE INDEX idx_cotiz_variacion ON cotizaciones_actuales (variacion_pct_dia DESC);
CREATE INDEX idx_cotiz_volumen   ON cotizaciones_actuales (volumen_dia DESC);

-- Indicadores técnicos precalculados (RSI, MACD, SMA...).
-- 'indicador' incluye el parámetro, p. ej. 'RSI_14', 'SMA_50', 'MACD_12_26_9'.
CREATE TABLE indicadores_tecnicos (
    id_activo  BIGINT         NOT NULL REFERENCES activos(id_activo) ON DELETE CASCADE,
    intervalo  intervalo_vela NOT NULL,
    momento    TIMESTAMPTZ    NOT NULL,
    indicador  VARCHAR(30)    NOT NULL,
    valores    JSON          NOT NULL,                    -- ej. {"rsi": 41.7} o {"macd":..,"senal":..,"hist":..}
    PRIMARY KEY (id_activo, intervalo, momento, indicador)
);

CREATE TABLE noticias (
    id_noticia           BIGSERIAL PRIMARY KEY,
    titulo       TEXT        NOT NULL,
    resumen      TEXT,
    url          TEXT        NOT NULL UNIQUE,              -- evita duplicados
    fuente       VARCHAR(100),
    imagen_url   TEXT,
    publicada_en TIMESTAMPTZ NOT NULL,
    creado_en    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_noticias_publicada ON noticias (publicada_en DESC);

-- Una noticia puede mencionar varios activos
CREATE TABLE noticias_activos (
    id_noticia BIGINT NOT NULL REFERENCES noticias(id_noticia) ON DELETE CASCADE,
    id_activo  BIGINT NOT NULL REFERENCES activos(id_activo)  ON DELETE CASCADE,
    PRIMARY KEY (id_noticia, id_activo)
);
CREATE INDEX idx_noticias_activos_activo ON noticias_activos (id_activo);



-- =====================================================================
-- 4. WATCHLISTS
-- =====================================================================
CREATE TABLE listas_seguimiento (
    id_lista         BIGSERIAL PRIMARY KEY,
    id_usuario BIGINT       NOT NULL REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
    nombre     VARCHAR(100) NOT NULL,
    orden      INT          NOT NULL DEFAULT 0,
    creada_en  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    UNIQUE (id_usuario, nombre)
);

CREATE TABLE listas_seguimiento_activos (
    id_lista    BIGINT      NOT NULL REFERENCES listas_seguimiento(id_lista) ON DELETE CASCADE,
    id_activo   BIGINT      NOT NULL REFERENCES activos(id_activo)            ON DELETE CASCADE,
    orden       INT         NOT NULL DEFAULT 0,
    agregado_en TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (id_lista, id_activo)
);
CREATE INDEX idx_lista_activos_activo ON listas_seguimiento_activos (id_activo);


-- =====================================================================
-- 5. ALERTAS Y NOTIFICACIONES
-- =====================================================================
CREATE TABLE alertas (
    id_alerta                 BIGSERIAL PRIMARY KEY,
    id_usuario         BIGINT           NOT NULL REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
    id_activo          BIGINT           NOT NULL REFERENCES activos(id_activo)  ON DELETE CASCADE,
    tipo               tipo_alerta      NOT NULL,
    condicion          condicion_alerta,
    valor_umbral       NUMERIC(20,8),                       -- precio o valor del indicador
    indicador          VARCHAR(30),                         -- 'RSI_14', 'SMA_50'... (tipo = indicador)
    direccion_objetivo direccion_prediccion,                -- (tipo = prediccion_ia)
    confianza_minima   NUMERIC(5,4)
                       CHECK (confianza_minima IS NULL OR confianza_minima BETWEEN 0 AND 1),
    estado             estado_alerta    NOT NULL DEFAULT 'activa',
    notificar_email    BOOLEAN          NOT NULL DEFAULT FALSE,
    notificar_in_app   BOOLEAN          NOT NULL DEFAULT TRUE,
    creada_en          TIMESTAMPTZ      NOT NULL DEFAULT now(),
    disparada_en       TIMESTAMPTZ,
    vence_en           TIMESTAMPTZ,
    CONSTRAINT ck_alerta_coherente CHECK (
        (tipo = 'precio'        AND condicion IS NOT NULL AND valor_umbral IS NOT NULL) OR
        (tipo = 'indicador'     AND condicion IS NOT NULL AND valor_umbral IS NOT NULL
                                AND indicador IS NOT NULL) OR
        (tipo = 'prediccion_ia' AND direccion_objetivo IS NOT NULL)
    )
);
CREATE INDEX idx_alertas_usuario ON alertas (id_usuario);
-- El proceso que revisa alertas solo mira las activas
CREATE INDEX idx_alertas_activas ON alertas (id_activo) WHERE estado = 'activa';

CREATE TABLE notificaciones (
    id_notificacion         BIGSERIAL PRIMARY KEY,
    id_usuario BIGINT       NOT NULL REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
    tipo       VARCHAR(30)  NOT NULL
               CHECK (tipo IN ('alerta', 'orden', 'ia', 'sistema')),
    titulo     VARCHAR(200) NOT NULL,
    mensaje    TEXT,
    id_alerta  BIGINT       REFERENCES alertas(id_alerta) ON DELETE SET NULL,
    leida      BOOLEAN      NOT NULL DEFAULT FALSE,
    creada_en  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    leida_en   TIMESTAMPTZ
);
CREATE INDEX idx_notif_usuario_pendientes ON notificaciones (id_usuario, creada_en DESC)
    WHERE leida = FALSE;


-- =====================================================================
-- 6. OPERAR EN EL SIMULADOR
-- =====================================================================
CREATE TABLE cuentas_simuladas (
    id_cuenta                BIGSERIAL PRIMARY KEY,
    id_usuario        BIGINT        NOT NULL REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
    nombre            VARCHAR(100)  NOT NULL,
    moneda            CHAR(3)       NOT NULL DEFAULT 'USD',
    capital_inicial   NUMERIC(20,4) NOT NULL CHECK (capital_inicial > 0),
    saldo_disponible  NUMERIC(20,4) NOT NULL CHECK (saldo_disponible >= 0),
    comision_pct      NUMERIC(6,4)  NOT NULL DEFAULT 0.1000 CHECK (comision_pct >= 0),   -- 0.1 = 0,1 %
    deslizamiento_pct NUMERIC(6,4)  NOT NULL DEFAULT 0      CHECK (deslizamiento_pct >= 0),
    es_replay         BOOLEAN       NOT NULL DEFAULT FALSE,  -- TRUE = cuenta de una sesión de repetición histórica
    activa            BOOLEAN       NOT NULL DEFAULT TRUE,
    creada_en         TIMESTAMPTZ   NOT NULL DEFAULT now(),
    reiniciada_en     TIMESTAMPTZ,
    UNIQUE (id_usuario, nombre)
);

-- Cada vez que el usuario reinicia una cuenta se guarda cómo le fue
CREATE TABLE reinicios_cuenta (
    id_reinicio               BIGSERIAL PRIMARY KEY,
    id_cuenta        BIGINT        NOT NULL REFERENCES cuentas_simuladas(id_cuenta) ON DELETE CASCADE,
    capital_inicial  NUMERIC(20,4) NOT NULL,
    patrimonio_final NUMERIC(20,4) NOT NULL,
    rentabilidad_pct NUMERIC(12,4) NOT NULL,
    reiniciado_en    TIMESTAMPTZ   NOT NULL DEFAULT now()
);

CREATE TABLE ordenes (
    id_orden                   BIGSERIAL PRIMARY KEY,
    id_cuenta            BIGINT         NOT NULL REFERENCES cuentas_simuladas(id_cuenta) ON DELETE CASCADE,
    id_activo            BIGINT         NOT NULL REFERENCES activos(id_activo),
    lado                 lado_orden     NOT NULL,
    tipo                 tipo_orden     NOT NULL,
    cantidad             NUMERIC(28,10) CHECK (cantidad > 0),          -- por unidades...
    monto_solicitado     NUMERIC(20,4)  CHECK (monto_solicitado > 0),  -- ...o por monto en dinero
    precio_limite        NUMERIC(20,8)  CHECK (precio_limite > 0),     -- limite y stop_limite
    precio_disparo       NUMERIC(20,8)  CHECK (precio_disparo > 0),    -- stop_loss, take_profit, stop_limite
    id_orden_padre       BIGINT         REFERENCES ordenes(id_orden) ON DELETE CASCADE,  -- SL/TP ligado a una orden
    estado               estado_orden   NOT NULL DEFAULT 'pendiente',
    cantidad_ejecutada   NUMERIC(28,10) NOT NULL DEFAULT 0 CHECK (cantidad_ejecutada >= 0),
    precio_promedio      NUMERIC(20,8),                                -- promedio de las ejecuciones
    comision_total       NUMERIC(20,4)  NOT NULL DEFAULT 0 CHECK (comision_total >= 0),
    origen               VARCHAR(12)    NOT NULL DEFAULT 'manual'
                         CHECK (origen IN ('manual', 'estrategia', 'sistema')),
    id_estrategia        BIGINT,                                       -- FK se agrega en el módulo 8
    motivo_rechazo       TEXT,
    creada_en            TIMESTAMPTZ    NOT NULL DEFAULT now(),
    vence_en             TIMESTAMPTZ,
    ejecutada_en         TIMESTAMPTZ,
    cancelada_en         TIMESTAMPTZ,
    CONSTRAINT ck_orden_tamano   CHECK (cantidad IS NOT NULL OR monto_solicitado IS NOT NULL),
    CONSTRAINT ck_orden_limite   CHECK (tipo NOT IN ('limite', 'stop_limite') OR precio_limite IS NOT NULL),
    CONSTRAINT ck_orden_disparo  CHECK (tipo NOT IN ('stop_loss', 'take_profit', 'stop_limite')
                                        OR precio_disparo IS NOT NULL),
    CONSTRAINT ck_orden_ejecutada CHECK (cantidad IS NULL OR cantidad_ejecutada <= cantidad)
);
CREATE INDEX idx_ordenes_cuenta ON ordenes (id_cuenta, creada_en DESC);
-- El motor que dispara órdenes límite/stop solo revisa las pendientes
CREATE INDEX idx_ordenes_pendientes ON ordenes (id_activo)
    WHERE estado IN ('pendiente', 'parcial');

-- Cada "fill": una orden puede ejecutarse en una o varias partes.
-- 'ejecutada_en' es el momento de MERCADO (en cuentas replay será la fecha simulada);
-- 'registrada_en' es cuándo se grabó realmente en la base de datos.
CREATE TABLE ejecuciones (
    id_ejecucion            BIGSERIAL PRIMARY KEY,
    id_orden      BIGINT         NOT NULL REFERENCES ordenes(id_orden) ON DELETE CASCADE,
    id_cuenta     BIGINT         NOT NULL REFERENCES cuentas_simuladas(id_cuenta) ON DELETE CASCADE,
    id_activo     BIGINT         NOT NULL REFERENCES activos(id_activo),
    lado          lado_orden     NOT NULL,
    cantidad      NUMERIC(28,10) NOT NULL CHECK (cantidad > 0),
    precio        NUMERIC(20,8)  NOT NULL CHECK (precio > 0),
    comision      NUMERIC(20,4)  NOT NULL DEFAULT 0 CHECK (comision >= 0),
    deslizamiento NUMERIC(20,4)  NOT NULL DEFAULT 0,
    ejecutada_en  TIMESTAMPTZ    NOT NULL,
    registrada_en TIMESTAMPTZ    NOT NULL DEFAULT now()
);
CREATE INDEX idx_ejecuciones_cuenta ON ejecuciones (id_cuenta, ejecutada_en DESC);
CREATE INDEX idx_ejecuciones_orden  ON ejecuciones (id_orden);


-- =====================================================================
-- 7. PORTAFOLIO
-- =====================================================================
-- Posiciones abiertas. Cuando una posición se cierra por completo,
-- la aplicación borra la fila y registra la operación en operaciones_cerradas.
CREATE TABLE posiciones (
    id_posicion                     BIGSERIAL PRIMARY KEY,
    id_cuenta              BIGINT         NOT NULL REFERENCES cuentas_simuladas(id_cuenta) ON DELETE CASCADE,
    id_activo              BIGINT         NOT NULL REFERENCES activos(id_activo),
    cantidad               NUMERIC(28,10) NOT NULL CHECK (cantidad > 0),
    precio_promedio_entrada NUMERIC(20,8) NOT NULL CHECK (precio_promedio_entrada > 0),
    abierta_en             TIMESTAMPTZ    NOT NULL DEFAULT now(),
    actualizado_en         TIMESTAMPTZ    NOT NULL DEFAULT now(),
    UNIQUE (id_cuenta, id_activo)
);

-- Operaciones completadas (alimenta win rate, ganancia promedio, etc.)
CREATE TABLE operaciones_cerradas (
    id_operacion_cerrada                BIGSERIAL PRIMARY KEY,
    id_cuenta         BIGINT         NOT NULL REFERENCES cuentas_simuladas(id_cuenta) ON DELETE CASCADE,
    id_activo         BIGINT         NOT NULL REFERENCES activos(id_activo),
    cantidad          NUMERIC(28,10) NOT NULL CHECK (cantidad > 0),
    precio_entrada    NUMERIC(20,8)  NOT NULL,
    precio_salida     NUMERIC(20,8)  NOT NULL,
    comisiones        NUMERIC(20,4)  NOT NULL DEFAULT 0,
    ganancia_realizada NUMERIC(20,4) NOT NULL,                -- ya descontadas las comisiones
    abierta_en        TIMESTAMPTZ    NOT NULL,
    cerrada_en        TIMESTAMPTZ    NOT NULL
);
CREATE INDEX idx_op_cerradas_cuenta ON operaciones_cerradas (id_cuenta, cerrada_en DESC);

-- Foto diaria del patrimonio: permite graficar su evolución sin recalcular todo
CREATE TABLE snapshots_portafolio (
    id_snapshot                BIGSERIAL PRIMARY KEY,
    id_cuenta         BIGINT        NOT NULL REFERENCES cuentas_simuladas(id_cuenta) ON DELETE CASCADE,
    fecha             DATE          NOT NULL,
    saldo_disponible  NUMERIC(20,4) NOT NULL,
    valor_posiciones  NUMERIC(20,4) NOT NULL,
    patrimonio_total  NUMERIC(20,4) NOT NULL,
    rentabilidad_pct  NUMERIC(12,4) NOT NULL,                 -- vs capital inicial
    drawdown_pct      NUMERIC(12,4) NOT NULL DEFAULT 0,       -- caída desde el máximo histórico
    UNIQUE (id_cuenta, fecha)
);


-- =====================================================================
-- 8. BACKTESTING
-- =====================================================================
CREATE TABLE estrategias (
    id_estrategia              BIGSERIAL PRIMARY KEY,
    id_usuario      BIGINT       NOT NULL REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
    nombre          VARCHAR(100) NOT NULL,
    descripcion     TEXT,
    -- Reglas de la estrategia. Ejemplo:
    -- {"entrada":[{"indicador":"RSI_14","condicion":"menor_que","valor":30}],
    --  "salida": [{"indicador":"RSI_14","condicion":"mayor_que","valor":70}],
    --  "stop_loss_pct":5, "take_profit_pct":10, "tamano_posicion_pct":100}
    definicion      JSON        NOT NULL,
    -- Opcional: ejecutar la estrategia sola ("bot") en una cuenta simulada
    bot_habilitado  BOOLEAN      NOT NULL DEFAULT FALSE,
    id_bot_cuenta   BIGINT       REFERENCES cuentas_simuladas(id_cuenta) ON DELETE SET NULL,
    id_bot_activo   BIGINT       REFERENCES activos(id_activo) ON DELETE SET NULL,
    creada_en       TIMESTAMPTZ  NOT NULL DEFAULT now(),
    actualizado_en  TIMESTAMPTZ  NOT NULL DEFAULT now(),
    UNIQUE (id_usuario, nombre),
    CONSTRAINT ck_bot_completo CHECK (
        bot_habilitado = FALSE OR (id_bot_cuenta IS NOT NULL AND id_bot_activo IS NOT NULL)
    )
);

-- Ahora que existe 'estrategias', se completa la relación desde 'ordenes'
ALTER TABLE ordenes
    ADD CONSTRAINT fk_ordenes_estrategia
    FOREIGN KEY (id_estrategia) REFERENCES estrategias(id_estrategia) ON DELETE SET NULL;

CREATE TABLE backtests (
    id_backtest                BIGSERIAL PRIMARY KEY,
    id_usuario        BIGINT         NOT NULL REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
    id_estrategia     BIGINT         NOT NULL REFERENCES estrategias(id_estrategia) ON DELETE CASCADE,
    id_activo         BIGINT         NOT NULL REFERENCES activos(id_activo),
    intervalo         intervalo_vela NOT NULL DEFAULT '1d',
    fecha_inicio      DATE           NOT NULL,
    fecha_fin         DATE           NOT NULL,
    capital_inicial   NUMERIC(20,4)  NOT NULL CHECK (capital_inicial > 0),
    comision_pct      NUMERIC(6,4)   NOT NULL DEFAULT 0.1000 CHECK (comision_pct >= 0),
    estado            estado_proceso NOT NULL DEFAULT 'pendiente',
    mensaje_error     TEXT,
    creado_en         TIMESTAMPTZ    NOT NULL DEFAULT now(),
    completado_en     TIMESTAMPTZ,
    CHECK (fecha_fin > fecha_inicio)
);
CREATE INDEX idx_backtests_usuario    ON backtests (id_usuario, creado_en DESC);
CREATE INDEX idx_backtests_estrategia ON backtests (id_estrategia);

CREATE TABLE backtest_resultados (
    id_backtest                 BIGINT PRIMARY KEY REFERENCES backtests(id_backtest) ON DELETE CASCADE,
    capital_final               NUMERIC(20,4)  NOT NULL,
    rentabilidad_pct            NUMERIC(12,4)  NOT NULL,
    rentabilidad_buy_hold_pct   NUMERIC(12,4),             -- comparación: comprar y mantener
    drawdown_max_pct            NUMERIC(12,4),
    num_operaciones             INT            NOT NULL DEFAULT 0,
    operaciones_ganadoras       INT            NOT NULL DEFAULT 0,
    win_rate_pct                NUMERIC(8,4),
    ratio_sharpe                NUMERIC(10,4),
    volatilidad_anual_pct       NUMERIC(12,4)
);

CREATE TABLE backtest_curva_capital (
    id_backtest BIGINT        NOT NULL REFERENCES backtests(id_backtest) ON DELETE CASCADE,
    momento     TIMESTAMPTZ   NOT NULL,
    capital     NUMERIC(20,4) NOT NULL,
    PRIMARY KEY (id_backtest, momento)
);

CREATE TABLE backtest_operaciones (
    id_backtest_operacion             BIGSERIAL PRIMARY KEY,
    id_backtest    BIGINT         NOT NULL REFERENCES backtests(id_backtest) ON DELETE CASCADE,
    cantidad       NUMERIC(28,10) NOT NULL,
    fecha_entrada  TIMESTAMPTZ    NOT NULL,
    precio_entrada NUMERIC(20,8)  NOT NULL,
    fecha_salida   TIMESTAMPTZ,
    precio_salida  NUMERIC(20,8),
    ganancia       NUMERIC(20,4)
);
CREATE INDEX idx_bt_operaciones ON backtest_operaciones (id_backtest, fecha_entrada);


-- =====================================================================
-- 9. INTELIGENCIA ARTIFICIAL
-- =====================================================================
CREATE TABLE modelos_ia (
    id_modelo                    BIGSERIAL PRIMARY KEY,
    nombre                VARCHAR(100)   NOT NULL,
    version               VARCHAR(30)    NOT NULL,
    tipo                  tipo_modelo_ia NOT NULL,
    algoritmo             VARCHAR(60),                      -- 'LightGBM', 'LSTM', 'FinBERT'...
    horizonte_dias        INT            CHECK (horizonte_dias > 0),  -- NULL si no aplica
    parametros            JSON          NOT NULL DEFAULT '{}',
    metricas_entrenamiento JSON         NOT NULL DEFAULT '{}',
    ruta_artefacto        TEXT,                              -- dónde está el archivo del modelo
    estado                estado_modelo  NOT NULL DEFAULT 'entrenando',
    entrenado_en          TIMESTAMPTZ,
    creado_en             TIMESTAMPTZ    NOT NULL DEFAULT now(),
    UNIQUE (nombre, version)
);

-- Predicción de dirección (alcista / bajista / lateral) con probabilidades
CREATE TABLE predicciones_direccion (
    id_prediccion               BIGSERIAL PRIMARY KEY,
    id_activo        BIGINT               NOT NULL REFERENCES activos(id_activo)    ON DELETE CASCADE,
    id_modelo        BIGINT               NOT NULL REFERENCES modelos_ia(id_modelo),
    generada_en      TIMESTAMPTZ          NOT NULL DEFAULT now(),
    horizonte_dias   INT                  NOT NULL CHECK (horizonte_dias > 0),
    fecha_objetivo   TIMESTAMPTZ          NOT NULL,         -- cuándo se podrá evaluar
    direccion        direccion_prediccion NOT NULL,
    prob_alcista     NUMERIC(5,4)         NOT NULL CHECK (prob_alcista BETWEEN 0 AND 1),
    prob_bajista     NUMERIC(5,4)         NOT NULL CHECK (prob_bajista BETWEEN 0 AND 1),
    prob_lateral     NUMERIC(5,4)         NOT NULL CHECK (prob_lateral BETWEEN 0 AND 1),
    confianza        NUMERIC(5,4)         NOT NULL CHECK (confianza BETWEEN 0 AND 1),
    precio_referencia NUMERIC(20,8)       NOT NULL,         -- precio al momento de predecir
    -- Se completan cuando llega la fecha objetivo (para medir aciertos):
    precio_resultado NUMERIC(20,8),
    direccion_real   direccion_prediccion,
    acierto          BOOLEAN,
    evaluada_en      TIMESTAMPTZ,
    CONSTRAINT ck_probabilidades CHECK (abs(prob_alcista + prob_bajista + prob_lateral - 1) < 0.001),
    UNIQUE (id_activo, id_modelo, horizonte_dias, generada_en)
);
CREATE INDEX idx_pred_dir_activo ON predicciones_direccion (id_activo, generada_en DESC);
-- Para el proceso que evalúa predicciones vencidas
CREATE INDEX idx_pred_dir_pendientes ON predicciones_direccion (fecha_objetivo)
    WHERE acierto IS NULL;

-- Qué factores pesaron en cada predicción (explicabilidad)
CREATE TABLE explicaciones_prediccion (
    id_prediccion BIGINT       NOT NULL REFERENCES predicciones_direccion(id_prediccion) ON DELETE CASCADE,
    factor        VARCHAR(60)  NOT NULL,                    -- 'RSI_14', 'sentimiento_noticias', 'volumen'...
    importancia   NUMERIC(8,6) NOT NULL,                    -- puede ser negativa (empuja a la baja)
    valor_factor  NUMERIC(20,8),
    PRIMARY KEY (id_prediccion, factor)
);

CREATE TABLE predicciones_volatilidad (
    id_prediccion_volatilidad                     BIGSERIAL PRIMARY KEY,
    id_activo              BIGINT       NOT NULL REFERENCES activos(id_activo) ON DELETE CASCADE,
    id_modelo              BIGINT       NOT NULL REFERENCES modelos_ia(id_modelo),
    generada_en            TIMESTAMPTZ  NOT NULL DEFAULT now(),
    horizonte_dias         INT          NOT NULL CHECK (horizonte_dias > 0),
    volatilidad_esperada_pct NUMERIC(10,4) NOT NULL,
    nivel_riesgo           nivel_riesgo NOT NULL,
    UNIQUE (id_activo, id_modelo, horizonte_dias, generada_en)
);
CREATE INDEX idx_pred_vol_activo ON predicciones_volatilidad (id_activo, generada_en DESC);

CREATE TABLE regimenes_mercado (
    id_regimen         BIGSERIAL PRIMARY KEY,
    id_activo  BIGINT         NOT NULL REFERENCES activos(id_activo) ON DELETE CASCADE,
    id_modelo  BIGINT         NOT NULL REFERENCES modelos_ia(id_modelo),
    fecha      DATE           NOT NULL,
    regimen    regimen_mercado NOT NULL,
    confianza  NUMERIC(5,4)   NOT NULL CHECK (confianza BETWEEN 0 AND 1),
    UNIQUE (id_activo, id_modelo, fecha)
);

CREATE TABLE sentimiento_noticias (
    id_noticia BIGINT              NOT NULL REFERENCES noticias(id_noticia)    ON DELETE CASCADE,
    id_activo  BIGINT              NOT NULL REFERENCES activos(id_activo)     ON DELETE CASCADE,
    id_modelo  BIGINT              NOT NULL REFERENCES modelos_ia(id_modelo),
    sentimiento sentimiento_noticia NOT NULL,
    puntaje    NUMERIC(5,4)        NOT NULL CHECK (puntaje BETWEEN -1 AND 1),
    confianza  NUMERIC(5,4)        CHECK (confianza BETWEEN 0 AND 1),
    creado_en  TIMESTAMPTZ         NOT NULL DEFAULT now(),
    PRIMARY KEY (id_noticia, id_activo, id_modelo)
);
CREATE INDEX idx_sentimiento_activo ON sentimiento_noticias (id_activo, creado_en DESC);




-- =====================================================================
-- 10. APRENDIZAJE
-- =====================================================================
CREATE TABLE glosario (
    id_termino         BIGSERIAL PRIMARY KEY,
    termino    VARCHAR(100) NOT NULL UNIQUE,
    definicion TEXT         NOT NULL,
    categoria  VARCHAR(50)
);


-- Modo repetición histórica (replay): el usuario "viaja" a una fecha pasada
-- y opera mientras las velas avanzan. Usa su propia cuenta (es_replay = TRUE).
CREATE TABLE sesiones_replay (
    id_sesion             BIGSERIAL PRIMARY KEY,
    id_usuario     BIGINT         NOT NULL REFERENCES usuarios(id_usuario) ON DELETE CASCADE,
    id_cuenta      BIGINT         NOT NULL UNIQUE REFERENCES cuentas_simuladas(id_cuenta) ON DELETE CASCADE,
    id_activo      BIGINT         NOT NULL REFERENCES activos(id_activo),
    intervalo      intervalo_vela NOT NULL DEFAULT '1d',
    fecha_inicio   TIMESTAMPTZ    NOT NULL,
    fecha_fin      TIMESTAMPTZ    NOT NULL,
    momento_actual TIMESTAMPTZ    NOT NULL,                 -- hasta dónde ha avanzado
    estado         VARCHAR(12)    NOT NULL DEFAULT 'en_curso'
                   CHECK (estado IN ('en_curso', 'finalizada')),
    creada_en      TIMESTAMPTZ    NOT NULL DEFAULT now(),
    CHECK (fecha_fin > fecha_inicio),
    CHECK (momento_actual BETWEEN fecha_inicio AND fecha_fin)
);
CREATE INDEX idx_replay_usuario ON sesiones_replay (id_usuario, estado);


-- =====================================================================
-- 12. ADMINISTRACIÓN
-- =====================================================================
CREATE TABLE fuentes_datos (
    id_fuente       BIGSERIAL PRIMARY KEY,
    nombre   VARCHAR(80) NOT NULL UNIQUE,
    tipo     VARCHAR(30) NOT NULL,                          -- mercado, cripto, noticias
    url_base TEXT,
    activa   BOOLEAN     NOT NULL DEFAULT TRUE
);

CREATE TABLE registros_ingesta (
    id_registro               BIGSERIAL PRIMARY KEY,
    id_fuente        BIGINT         NOT NULL REFERENCES fuentes_datos(id_fuente),
    id_activo        BIGINT         REFERENCES activos(id_activo) ON DELETE SET NULL,
    tipo_dato        VARCHAR(20)    NOT NULL
                     CHECK (tipo_dato IN ('velas', 'cotizaciones', 'noticias')),
    estado           estado_proceso NOT NULL DEFAULT 'ejecutando',
    filas_procesadas INT            NOT NULL DEFAULT 0,
    mensaje_error    TEXT,
    inicio_en        TIMESTAMPTZ    NOT NULL DEFAULT now(),
    fin_en           TIMESTAMPTZ
);
CREATE INDEX idx_ingesta_fecha  ON registros_ingesta (inicio_en DESC);
CREATE INDEX idx_ingesta_errores ON registros_ingesta (inicio_en DESC) WHERE estado = 'fallido';

CREATE TABLE entrenamientos_modelo (
    id_entrenamiento            BIGSERIAL PRIMARY KEY,
    id_modelo     BIGINT         NOT NULL REFERENCES modelos_ia(id_modelo) ON DELETE CASCADE,
    solicitado_por BIGINT        REFERENCES usuarios(id_usuario) ON DELETE SET NULL,
    estado        estado_proceso NOT NULL DEFAULT 'pendiente',
    metricas      JSON          NOT NULL DEFAULT '{}',
    mensaje_error TEXT,
    inicio_en     TIMESTAMPTZ    NOT NULL DEFAULT now(),
    fin_en        TIMESTAMPTZ
);
CREATE INDEX idx_entrenamientos_modelo ON entrenamientos_modelo (id_modelo, inicio_en DESC);

CREATE TABLE auditoria_admin (
    id_auditoria         BIGSERIAL PRIMARY KEY,
    id_admin   BIGINT       REFERENCES usuarios(id_usuario) ON DELETE SET NULL,
    accion     VARCHAR(80)  NOT NULL,                       -- 'desactivar_usuario', 'reentrenar_modelo'...
    entidad    VARCHAR(60),
    id_entidad BIGINT,
    detalle    JSON        NOT NULL DEFAULT '{}',
    creado_en  TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX idx_auditoria_fecha ON auditoria_admin (creado_en DESC);


-- =====================================================================
-- VISTAS ÚTILES
-- =====================================================================
-- Posiciones abiertas con precio actual y ganancia/pérdida no realizada.
-- Nota: para cuentas replay, la aplicación valora con la vela simulada,
-- no con cotizaciones_actuales.
CREATE VIEW vista_posiciones_valoradas AS
SELECT
    p.id_posicion,
    p.id_cuenta,
    p.id_activo,
    a.ticker,
    a.nombre                     AS activo,
    a.tipo,
    p.cantidad,
    p.precio_promedio_entrada,
    COALESCE(q.precio, p.precio_promedio_entrada)                AS precio_actual,
    p.cantidad * COALESCE(q.precio, p.precio_promedio_entrada)   AS valor_mercado,
    (COALESCE(q.precio, p.precio_promedio_entrada) - p.precio_promedio_entrada)
        * p.cantidad                                             AS ganancia_no_realizada,
    ROUND((COALESCE(q.precio, p.precio_promedio_entrada) - p.precio_promedio_entrada)
          / p.precio_promedio_entrada * 100, 4)                  AS ganancia_pct
FROM posiciones p
JOIN activos a                     ON a.id_activo = p.id_activo
LEFT JOIN cotizaciones_actuales q  ON q.id_activo = p.id_activo;

-- Resumen de cada cuenta: saldo + valor de posiciones = patrimonio.
CREATE VIEW vista_resumen_cuenta AS
SELECT
    c.id_cuenta,
    c.id_usuario,
    c.nombre,
    c.moneda,
    c.capital_inicial,
    c.saldo_disponible,
    COALESCE(SUM(v.valor_mercado), 0)     AS valor_posiciones,
    c.saldo_disponible + COALESCE(SUM(v.valor_mercado), 0) AS patrimonio_total,
    COALESCE(SUM(v.ganancia_no_realizada), 0)              AS ganancia_no_realizada,
    ROUND(
        ((c.saldo_disponible + COALESCE(SUM(v.valor_mercado), 0)) - c.capital_inicial)
        / c.capital_inicial * 100, 4)     AS rentabilidad_pct
FROM cuentas_simuladas c
LEFT JOIN vista_posiciones_valoradas v ON v.id_cuenta = c.id_cuenta
GROUP BY c.id_cuenta;

-- Estadísticas de operaciones cerradas por cuenta
CREATE VIEW vista_estadisticas_operaciones AS
SELECT
    id_cuenta,
    COUNT(*)                                             AS total_operaciones,
    COUNT(CASE WHEN ganancia_realizada > 0  THEN 1 END)  AS ganadoras,
    COUNT(CASE WHEN ganancia_realizada <= 0 THEN 1 END)  AS perdedoras,
    ROUND(COUNT(CASE WHEN ganancia_realizada > 0 THEN 1 END)::NUMERIC
          / NULLIF(COUNT(*), 0) * 100, 2)                AS win_rate_pct,
    SUM(ganancia_realizada)                              AS ganancia_total,
    ROUND(AVG(ganancia_realizada), 4)                    AS ganancia_promedio
FROM operaciones_cerradas
GROUP BY id_cuenta;

-- Historial de aciertos de la IA (transparencia): total y últimos 90 días
CREATE VIEW vista_precision_modelos AS
SELECT
    m.id_modelo,
    m.nombre,
    m.version,
    p.horizonte_dias,
    COUNT(*)                                AS predicciones_evaluadas,
    COUNT(CASE WHEN p.acierto THEN 1 END)   AS aciertos,
    ROUND(COUNT(CASE WHEN p.acierto THEN 1 END)::NUMERIC / COUNT(*) * 100, 2) AS precision_pct,
    COUNT(CASE WHEN p.evaluada_en >= now() - INTERVAL '90 days' THEN 1 END)   AS evaluadas_90d,
    ROUND(
        COUNT(CASE WHEN p.acierto AND p.evaluada_en >= now() - INTERVAL '90 days' THEN 1 END)::NUMERIC
        / NULLIF(COUNT(CASE WHEN p.evaluada_en >= now() - INTERVAL '90 days' THEN 1 END), 0) * 100, 2
    )                                       AS precision_90d_pct
FROM predicciones_direccion p
JOIN modelos_ia m ON m.id_modelo = p.id_modelo
WHERE p.acierto IS NOT NULL
GROUP BY m.id_modelo, m.nombre, m.version, p.horizonte_dias;


-- =====================================================================
-- FUNCIONES Y TRIGGERS
-- =====================================================================
-- Mantiene 'actualizado_en' al día automáticamente
CREATE FUNCTION fn_actualizar_timestamp() RETURNS TRIGGER AS $$
BEGIN
    NEW.actualizado_en = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DO $$
DECLARE
    t TEXT;
BEGIN
    FOREACH t IN ARRAY ARRAY['usuarios', 'preferencias_usuario', 'posiciones', 'estrategias']
    LOOP
        EXECUTE format(
            'CREATE TRIGGER trg_%I_actualizado BEFORE UPDATE ON %I
             FOR EACH ROW EXECUTE PROCEDURE fn_actualizar_timestamp()', t, t);
    END LOOP;
END $$;

-- Al crear un usuario se le crean sus preferencias por defecto
CREATE FUNCTION fn_crear_preferencias() RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO preferencias_usuario (id_usuario) VALUES (NEW.id_usuario);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_usuarios_preferencias
    AFTER INSERT ON usuarios
    FOR EACH ROW EXECUTE PROCEDURE fn_crear_preferencias();

-- Reinicia una cuenta: guarda cómo le fue, borra operaciones y restaura el capital.
-- Uso:  SELECT reiniciar_cuenta(1);
CREATE FUNCTION reiniciar_cuenta(p_id_cuenta BIGINT) RETURNS VOID AS $$
DECLARE
    v_capital    NUMERIC;
    v_patrimonio NUMERIC;
BEGIN
    SELECT capital_inicial INTO v_capital
    FROM cuentas_simuladas WHERE id_cuenta = p_id_cuenta FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'La cuenta % no existe', p_id_cuenta;
    END IF;

    SELECT patrimonio_total INTO v_patrimonio
    FROM vista_resumen_cuenta WHERE id_cuenta = p_id_cuenta;

    INSERT INTO reinicios_cuenta (id_cuenta, capital_inicial, patrimonio_final, rentabilidad_pct)
    VALUES (p_id_cuenta, v_capital, v_patrimonio,
            ROUND((v_patrimonio - v_capital) / v_capital * 100, 4));

    DELETE FROM ordenes              WHERE id_cuenta = p_id_cuenta;  -- borra también sus ejecuciones
    DELETE FROM posiciones           WHERE id_cuenta = p_id_cuenta;
    DELETE FROM operaciones_cerradas WHERE id_cuenta = p_id_cuenta;
    DELETE FROM snapshots_portafolio WHERE id_cuenta = p_id_cuenta;

    UPDATE cuentas_simuladas
    SET saldo_disponible = capital_inicial,
        reiniciada_en    = now()
    WHERE id_cuenta = p_id_cuenta;
END;
$$ LANGUAGE plpgsql;


-- =====================================================================
-- DATOS INICIALES (semilla). Puedes borrar esta sección si prefieres.
-- =====================================================================
INSERT INTO fuentes_datos (nombre, tipo, url_base) VALUES
    ('yfinance',      'mercado',       'https://finance.yahoo.com'),
    ('Binance',       'cripto',        'https://api.binance.com'),
    ('Finnhub',       'noticias',      'https://finnhub.io/api/v1');

INSERT INTO activos (ticker, nombre, tipo, bolsa, moneda, sector) VALUES
    ('AAPL',    'Apple Inc.',            'accion', 'NASDAQ',    'USD', 'Tecnología'),
    ('MSFT',    'Microsoft Corporation', 'accion', 'NASDAQ',    'USD', 'Tecnología'),
    ('TSLA',    'Tesla, Inc.',           'accion', 'NASDAQ',    'USD', 'Automoción'),
    ('SPY',     'SPDR S&P 500 ETF Trust','etf',    'NYSE Arca', 'USD', NULL),
    ('^GSPC',   'S&P 500',               'indice', NULL,        'USD', NULL),
    ('BTC-USD', 'Bitcoin',               'cripto', NULL,        'USD', NULL),
    ('ETH-USD', 'Ethereum',              'cripto', NULL,        'USD', NULL);

INSERT INTO glosario (termino, definicion, categoria) VALUES
    ('Vela japonesa',  'Representación gráfica de un periodo que muestra precio de apertura, máximo, mínimo y cierre.', 'Gráficos'),
    ('SMA',            'Media móvil simple: promedio del precio de cierre de los últimos N periodos. Suaviza el gráfico y ayuda a ver la tendencia.', 'Indicadores'),
    ('RSI',            'Índice de fuerza relativa: oscila entre 0 y 100. Por debajo de 30 suele indicar sobreventa y por encima de 70, sobrecompra.', 'Indicadores'),
    ('MACD',           'Indicador que compara dos medias móviles exponenciales para detectar cambios de tendencia y de impulso.', 'Indicadores'),
    ('Stop-loss',      'Orden que vende automáticamente una posición si el precio cae hasta un nivel definido, para limitar la pérdida.', 'Órdenes'),
    ('Take-profit',    'Orden que vende automáticamente una posición cuando el precio alcanza la ganancia deseada.', 'Órdenes'),
    ('Orden límite',   'Orden que solo se ejecuta si el precio alcanza o mejora el valor que el usuario fijó.', 'Órdenes'),
    ('Drawdown',       'Caída porcentual desde el valor máximo alcanzado por el patrimonio hasta su punto más bajo posterior.', 'Riesgo'),
    ('Volatilidad',    'Medida de cuánto varía el precio de un activo en el tiempo. Más volatilidad implica más riesgo y más oportunidad.', 'Riesgo'),
    ('Backtesting',    'Probar una estrategia con datos históricos para ver cómo habría funcionado en el pasado.', 'Estrategias');

COMMIT;
