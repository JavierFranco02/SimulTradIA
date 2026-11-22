--
-- PostgreSQL database dump
--

SET statement_timeout = 0;
SET lock_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;

--
-- Name: plpgsql; Type: EXTENSION; Schema: -; Owner: 
--

CREATE EXTENSION IF NOT EXISTS plpgsql WITH SCHEMA pg_catalog;


--
-- Name: EXTENSION plpgsql; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION plpgsql IS 'PL/pgSQL procedural language';


SET search_path = public, pg_catalog;

--
-- Name: direccion_prediccion; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE direccion_prediccion AS ENUM (
    'alcista',
    'bajista',
    'lateral'
);


ALTER TYPE public.direccion_prediccion OWNER TO postgres;

--
-- Name: estado_modelo; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE estado_modelo AS ENUM (
    'entrenando',
    'activo',
    'archivado',
    'fallido'
);


ALTER TYPE public.estado_modelo OWNER TO postgres;

--
-- Name: estado_orden; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE estado_orden AS ENUM (
    'pendiente',
    'parcial',
    'ejecutada',
    'cancelada',
    'rechazada',
    'expirada'
);


ALTER TYPE public.estado_orden OWNER TO postgres;

--
-- Name: estado_proceso; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE estado_proceso AS ENUM (
    'pendiente',
    'ejecutando',
    'completado',
    'fallido'
);


ALTER TYPE public.estado_proceso OWNER TO postgres;

--
-- Name: intervalo_vela; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE intervalo_vela AS ENUM (
    '1m',
    '5m',
    '15m',
    '1h',
    '4h',
    '1d',
    '1w'
);


ALTER TYPE public.intervalo_vela OWNER TO postgres;

--
-- Name: lado_orden; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE lado_orden AS ENUM (
    'compra',
    'venta'
);


ALTER TYPE public.lado_orden OWNER TO postgres;

--
-- Name: nivel_volatilidad; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE nivel_volatilidad AS ENUM (
    'baja',
    'normal',
    'alta'
);


ALTER TYPE public.nivel_volatilidad OWNER TO postgres;

--
-- Name: rol_usuario; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE rol_usuario AS ENUM (
    'usuario',
    'admin'
);


ALTER TYPE public.rol_usuario OWNER TO postgres;

--
-- Name: tipo_activo; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE tipo_activo AS ENUM (
    'accion',
    'cripto',
    'etf',
    'divisa',
    'indice',
    'bono'
);


ALTER TYPE public.tipo_activo OWNER TO postgres;

--
-- Name: tipo_modelo_ia; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE tipo_modelo_ia AS ENUM (
    'direccion',
    'volatilidad',
    'sentimiento',
    'regimen'
);


ALTER TYPE public.tipo_modelo_ia OWNER TO postgres;

--
-- Name: tipo_orden; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE tipo_orden AS ENUM (
    'mercado',
    'limite',
    'stop_loss',
    'take_profit',
    'stop_limite'
);


ALTER TYPE public.tipo_orden OWNER TO postgres;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: activos; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE activos (
    id_activo bigint NOT NULL,
    ticker character varying(20) NOT NULL,
    nombre character varying(150) NOT NULL,
    tipo tipo_activo NOT NULL,
    moneda character(3) DEFAULT 'USD'::bpchar NOT NULL,
    activo boolean DEFAULT true NOT NULL,
    creado_en timestamp with time zone DEFAULT now() NOT NULL,
    id_fuente bigint NOT NULL
);


ALTER TABLE public.activos OWNER TO postgres;

--
-- Name: activos_id_activo_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE activos_id_activo_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.activos_id_activo_seq OWNER TO postgres;

--
-- Name: activos_id_activo_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE activos_id_activo_seq OWNED BY activos.id_activo;


--
-- Name: cotizaciones_actuales; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE cotizaciones_actuales (
    id_activo bigint NOT NULL,
    precio numeric(20,8) NOT NULL,
    cierre_anterior numeric(20,8),
    variacion_pct_dia numeric(12,4),
    maximo_dia numeric(20,8),
    minimo_dia numeric(20,8),
    volumen_dia numeric(28,4),
    actualizado_en timestamp with time zone DEFAULT now() NOT NULL
);


ALTER TABLE public.cotizaciones_actuales OWNER TO postgres;

--
-- Name: cuentas_simuladas; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE cuentas_simuladas (
    id_cuenta bigint NOT NULL,
    id_usuario bigint NOT NULL,
    nombre character varying(100) NOT NULL,
    moneda character(3) DEFAULT 'USD'::bpchar NOT NULL,
    capital_inicial numeric(20,4) NOT NULL,
    saldo_disponible numeric(20,4) NOT NULL,
    comision_pct numeric(6,4) DEFAULT 0.1000 NOT NULL,
    deslizamiento_pct numeric(6,4) DEFAULT 0 NOT NULL,
    es_replay boolean DEFAULT false NOT NULL,
    activa boolean DEFAULT true NOT NULL,
    creada_en timestamp with time zone DEFAULT now() NOT NULL,
    reiniciada_en timestamp with time zone,
    CONSTRAINT cuentas_simuladas_capital_inicial_check CHECK ((capital_inicial > (0)::numeric)),
    CONSTRAINT cuentas_simuladas_comision_pct_check CHECK ((comision_pct >= (0)::numeric)),
    CONSTRAINT cuentas_simuladas_deslizamiento_pct_check CHECK ((deslizamiento_pct >= (0)::numeric)),
    CONSTRAINT cuentas_simuladas_saldo_disponible_check CHECK ((saldo_disponible >= (0)::numeric))
);


ALTER TABLE public.cuentas_simuladas OWNER TO postgres;

--
-- Name: cuentas_simuladas_id_cuenta_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE cuentas_simuladas_id_cuenta_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.cuentas_simuladas_id_cuenta_seq OWNER TO postgres;

--
-- Name: cuentas_simuladas_id_cuenta_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE cuentas_simuladas_id_cuenta_seq OWNED BY cuentas_simuladas.id_cuenta;


--
-- Name: ejecuciones; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE ejecuciones (
    id_ejecucion bigint NOT NULL,
    id_orden bigint NOT NULL,
    id_cuenta bigint NOT NULL,
    id_activo bigint NOT NULL,
    lado lado_orden NOT NULL,
    cantidad numeric(28,10) NOT NULL,
    precio numeric(20,8) NOT NULL,
    comision numeric(20,4) DEFAULT 0 NOT NULL,
    ejecutada_en timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT ejecuciones_cantidad_check CHECK ((cantidad > (0)::numeric)),
    CONSTRAINT ejecuciones_comision_check CHECK ((comision >= (0)::numeric)),
    CONSTRAINT ejecuciones_precio_check CHECK ((precio > (0)::numeric))
);


ALTER TABLE public.ejecuciones OWNER TO postgres;

--
-- Name: ejecuciones_id_ejecucion_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE ejecuciones_id_ejecucion_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.ejecuciones_id_ejecucion_seq OWNER TO postgres;

--
-- Name: ejecuciones_id_ejecucion_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE ejecuciones_id_ejecucion_seq OWNED BY ejecuciones.id_ejecucion;


--
-- Name: entrenamientos_modelo; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE entrenamientos_modelo (
    id_entrenamiento bigint NOT NULL,
    id_modelo bigint NOT NULL,
    solicitado_por bigint,
    estado estado_proceso DEFAULT 'pendiente'::estado_proceso NOT NULL,
    metricas json DEFAULT '{}'::json NOT NULL,
    mensaje_error text,
    inicio_en timestamp with time zone DEFAULT now() NOT NULL,
    fin_en timestamp with time zone
);


ALTER TABLE public.entrenamientos_modelo OWNER TO postgres;

--
-- Name: entrenamientos_modelo_id_entrenamiento_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE entrenamientos_modelo_id_entrenamiento_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.entrenamientos_modelo_id_entrenamiento_seq OWNER TO postgres;

--
-- Name: entrenamientos_modelo_id_entrenamiento_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE entrenamientos_modelo_id_entrenamiento_seq OWNED BY entrenamientos_modelo.id_entrenamiento;


--
-- Name: explicaciones_prediccion; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE explicaciones_prediccion (
    id_prediccion bigint NOT NULL,
    factor character varying(60) NOT NULL,
    importancia numeric(8,6) NOT NULL,
    valor_factor numeric(20,8)
);


ALTER TABLE public.explicaciones_prediccion OWNER TO postgres;

--
-- Name: fuentes_datos; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE fuentes_datos (
    id_fuente bigint NOT NULL,
    nombre character varying(80) NOT NULL,
    activa boolean DEFAULT true NOT NULL
);


ALTER TABLE public.fuentes_datos OWNER TO postgres;

--
-- Name: fuentes_datos_id_fuente_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE fuentes_datos_id_fuente_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.fuentes_datos_id_fuente_seq OWNER TO postgres;

--
-- Name: fuentes_datos_id_fuente_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE fuentes_datos_id_fuente_seq OWNED BY fuentes_datos.id_fuente;


--
-- Name: modelos_ia; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE modelos_ia (
    id_modelo bigint NOT NULL,
    nombre character varying(100) NOT NULL,
    version character varying(30) NOT NULL,
    tipo tipo_modelo_ia NOT NULL,
    algoritmo character varying(60),
    horizonte_dias integer,
    parametros json DEFAULT '{}'::json NOT NULL,
    metricas_entrenamiento json DEFAULT '{}'::json NOT NULL,
    ruta_artefacto text,
    estado estado_modelo DEFAULT 'entrenando'::estado_modelo NOT NULL,
    entrenado_en timestamp with time zone,
    creado_en timestamp with time zone DEFAULT now() NOT NULL,
    CONSTRAINT modelos_ia_horizonte_dias_check CHECK ((horizonte_dias > 0))
);


ALTER TABLE public.modelos_ia OWNER TO postgres;

--
-- Name: modelos_ia_id_modelo_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE modelos_ia_id_modelo_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.modelos_ia_id_modelo_seq OWNER TO postgres;

--
-- Name: modelos_ia_id_modelo_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE modelos_ia_id_modelo_seq OWNED BY modelos_ia.id_modelo;


--
-- Name: operaciones_cerradas; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE operaciones_cerradas (
    id_operacion_cerrada bigint NOT NULL,
    id_cuenta bigint NOT NULL,
    id_activo bigint NOT NULL,
    cantidad numeric(28,10) NOT NULL,
    precio_entrada numeric(20,8) NOT NULL,
    precio_salida numeric(20,8) NOT NULL,
    comisiones numeric(20,4) DEFAULT 0 NOT NULL,
    ganancia_realizada numeric(20,4) NOT NULL,
    abierta_en timestamp with time zone NOT NULL,
    cerrada_en timestamp with time zone NOT NULL,
    CONSTRAINT operaciones_cerradas_cantidad_check CHECK ((cantidad > (0)::numeric))
);


ALTER TABLE public.operaciones_cerradas OWNER TO postgres;

--
-- Name: operaciones_cerradas_id_operacion_cerrada_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE operaciones_cerradas_id_operacion_cerrada_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.operaciones_cerradas_id_operacion_cerrada_seq OWNER TO postgres;

--
-- Name: operaciones_cerradas_id_operacion_cerrada_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE operaciones_cerradas_id_operacion_cerrada_seq OWNED BY operaciones_cerradas.id_operacion_cerrada;


--
-- Name: ordenes; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE ordenes (
    id_orden bigint NOT NULL,
    id_cuenta bigint NOT NULL,
    id_activo bigint NOT NULL,
    lado lado_orden NOT NULL,
    tipo tipo_orden DEFAULT 'mercado'::tipo_orden NOT NULL,
    estado estado_orden DEFAULT 'pendiente'::estado_orden NOT NULL,
    cantidad numeric(28,10) NOT NULL,
    precio_promedio numeric(20,8),
    comision_total numeric(20,4) DEFAULT 0 NOT NULL,
    creada_en timestamp with time zone DEFAULT now() NOT NULL,
    ejecutada_en timestamp with time zone,
    precio_limite numeric(20,8),
    stop_loss numeric(20,8),
    take_profit numeric(20,8),
    motivo_rechazo text,
    cancelada_en timestamp with time zone,
    CONSTRAINT ck_orden_limite CHECK (((tipo <> 'limite'::tipo_orden) OR (precio_limite IS NOT NULL))),
    CONSTRAINT ordenes_cantidad_check CHECK ((cantidad > (0)::numeric)),
    CONSTRAINT ordenes_comision_total_check CHECK ((comision_total >= (0)::numeric)),
    CONSTRAINT ordenes_precio_limite_check CHECK ((precio_limite > (0)::numeric)),
    CONSTRAINT ordenes_stop_loss_check CHECK ((stop_loss > (0)::numeric)),
    CONSTRAINT ordenes_take_profit_check CHECK ((take_profit > (0)::numeric))
);


ALTER TABLE public.ordenes OWNER TO postgres;

--
-- Name: ordenes_id_orden_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE ordenes_id_orden_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.ordenes_id_orden_seq OWNER TO postgres;

--
-- Name: ordenes_id_orden_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE ordenes_id_orden_seq OWNED BY ordenes.id_orden;


--
-- Name: posiciones; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE posiciones (
    id_posicion bigint NOT NULL,
    id_cuenta bigint NOT NULL,
    id_activo bigint NOT NULL,
    cantidad numeric(28,10) NOT NULL,
    precio_promedio_entrada numeric(20,8) NOT NULL,
    comisiones_pagadas numeric(20,4) DEFAULT 0 NOT NULL,
    abierta_en timestamp with time zone DEFAULT now() NOT NULL,
    stop_loss numeric(20,8),
    take_profit numeric(20,8),
    CONSTRAINT posiciones_cantidad_check CHECK ((cantidad > (0)::numeric)),
    CONSTRAINT posiciones_comisiones_pagadas_check CHECK ((comisiones_pagadas >= (0)::numeric)),
    CONSTRAINT posiciones_precio_promedio_entrada_check CHECK ((precio_promedio_entrada > (0)::numeric)),
    CONSTRAINT posiciones_stop_loss_check CHECK ((stop_loss > (0)::numeric)),
    CONSTRAINT posiciones_take_profit_check CHECK ((take_profit > (0)::numeric))
);


ALTER TABLE public.posiciones OWNER TO postgres;

--
-- Name: posiciones_id_posicion_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE posiciones_id_posicion_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.posiciones_id_posicion_seq OWNER TO postgres;

--
-- Name: posiciones_id_posicion_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE posiciones_id_posicion_seq OWNED BY posiciones.id_posicion;


--
-- Name: precios_velas; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE precios_velas (
    id_activo bigint NOT NULL,
    intervalo intervalo_vela NOT NULL,
    momento timestamp with time zone NOT NULL,
    apertura numeric(20,8) NOT NULL,
    maximo numeric(20,8) NOT NULL,
    minimo numeric(20,8) NOT NULL,
    cierre numeric(20,8) NOT NULL,
    volumen numeric(28,4) DEFAULT 0 NOT NULL,
    CONSTRAINT precios_velas_check CHECK ((maximo >= minimo)),
    CONSTRAINT precios_velas_check1 CHECK (((maximo >= apertura) AND (maximo >= cierre))),
    CONSTRAINT precios_velas_check2 CHECK (((minimo <= apertura) AND (minimo <= cierre))),
    CONSTRAINT precios_velas_volumen_check CHECK ((volumen >= (0)::numeric))
);


ALTER TABLE public.precios_velas OWNER TO postgres;

--
-- Name: predicciones_direccion; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE predicciones_direccion (
    id_prediccion bigint NOT NULL,
    id_activo bigint NOT NULL,
    id_modelo bigint NOT NULL,
    generada_en timestamp with time zone DEFAULT now() NOT NULL,
    horizonte_dias integer NOT NULL,
    fecha_objetivo timestamp with time zone NOT NULL,
    direccion direccion_prediccion NOT NULL,
    prob_alcista numeric(5,4) NOT NULL,
    prob_bajista numeric(5,4) NOT NULL,
    prob_lateral numeric(5,4) NOT NULL,
    confianza numeric(5,4) NOT NULL,
    precio_referencia numeric(20,8) NOT NULL,
    precio_resultado numeric(20,8),
    direccion_real direccion_prediccion,
    acierto boolean,
    evaluada_en timestamp with time zone,
    CONSTRAINT ck_probabilidades CHECK ((abs((((prob_alcista + prob_bajista) + prob_lateral) - (1)::numeric)) < 0.001)),
    CONSTRAINT predicciones_direccion_confianza_check CHECK (((confianza >= (0)::numeric) AND (confianza <= (1)::numeric))),
    CONSTRAINT predicciones_direccion_horizonte_dias_check CHECK ((horizonte_dias > 0)),
    CONSTRAINT predicciones_direccion_prob_alcista_check CHECK (((prob_alcista >= (0)::numeric) AND (prob_alcista <= (1)::numeric))),
    CONSTRAINT predicciones_direccion_prob_bajista_check CHECK (((prob_bajista >= (0)::numeric) AND (prob_bajista <= (1)::numeric))),
    CONSTRAINT predicciones_direccion_prob_lateral_check CHECK (((prob_lateral >= (0)::numeric) AND (prob_lateral <= (1)::numeric)))
);


ALTER TABLE public.predicciones_direccion OWNER TO postgres;

--
-- Name: predicciones_direccion_id_prediccion_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE predicciones_direccion_id_prediccion_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.predicciones_direccion_id_prediccion_seq OWNER TO postgres;

--
-- Name: predicciones_direccion_id_prediccion_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE predicciones_direccion_id_prediccion_seq OWNED BY predicciones_direccion.id_prediccion;


--
-- Name: predicciones_volatilidad; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE predicciones_volatilidad (
    id_prediccion bigint NOT NULL,
    id_activo bigint NOT NULL,
    id_modelo bigint NOT NULL,
    generada_en timestamp with time zone DEFAULT now() NOT NULL,
    fecha_objetivo timestamp with time zone NOT NULL,
    precio_referencia numeric(20,8) NOT NULL,
    rango_predicho numeric(10,6) NOT NULL,
    rango_bajo numeric(10,6) NOT NULL,
    rango_alto numeric(10,6) NOT NULL,
    rango_hoy numeric(10,6) NOT NULL,
    rango_normal numeric(10,6) NOT NULL,
    umbral_bajo numeric(10,6) NOT NULL,
    umbral_alto numeric(10,6) NOT NULL,
    nivel nivel_volatilidad NOT NULL,
    factores json DEFAULT '[]'::json NOT NULL,
    rango_real numeric(10,6),
    nivel_real nivel_volatilidad,
    acierto_nivel boolean,
    evaluada_en timestamp with time zone,
    CONSTRAINT predicciones_volatilidad_rango_alto_check CHECK ((rango_alto > (0)::numeric)),
    CONSTRAINT predicciones_volatilidad_rango_bajo_check CHECK ((rango_bajo > (0)::numeric)),
    CONSTRAINT predicciones_volatilidad_rango_predicho_check CHECK ((rango_predicho > (0)::numeric))
);


ALTER TABLE public.predicciones_volatilidad OWNER TO postgres;

--
-- Name: predicciones_volatilidad_id_prediccion_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE predicciones_volatilidad_id_prediccion_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.predicciones_volatilidad_id_prediccion_seq OWNER TO postgres;

--
-- Name: predicciones_volatilidad_id_prediccion_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE predicciones_volatilidad_id_prediccion_seq OWNED BY predicciones_volatilidad.id_prediccion;


--
-- Name: snapshots_portafolio; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE snapshots_portafolio (
    id_cuenta bigint NOT NULL,
    momento timestamp with time zone NOT NULL,
    saldo_disponible numeric(20,4) NOT NULL,
    valor_posiciones numeric(20,4) NOT NULL,
    patrimonio_total numeric(20,4) NOT NULL
);


ALTER TABLE public.snapshots_portafolio OWNER TO postgres;

--
-- Name: usuarios; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE usuarios (
    id_usuario bigint NOT NULL,
    nombre character varying(100) NOT NULL,
    email character varying(255) NOT NULL,
    password_hash text NOT NULL,
    rol rol_usuario DEFAULT 'usuario'::rol_usuario NOT NULL,
    activo boolean DEFAULT true NOT NULL,
    ultimo_login_en timestamp with time zone,
    creado_en timestamp with time zone DEFAULT now() NOT NULL,
    actualizado_en timestamp with time zone DEFAULT now() NOT NULL,
    debe_cambiar_password boolean DEFAULT false NOT NULL
);


ALTER TABLE public.usuarios OWNER TO postgres;

--
-- Name: usuarios_id_usuario_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE usuarios_id_usuario_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.usuarios_id_usuario_seq OWNER TO postgres;

--
-- Name: usuarios_id_usuario_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE usuarios_id_usuario_seq OWNED BY usuarios.id_usuario;


--
-- Name: id_activo; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY activos ALTER COLUMN id_activo SET DEFAULT nextval('activos_id_activo_seq'::regclass);


--
-- Name: id_cuenta; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY cuentas_simuladas ALTER COLUMN id_cuenta SET DEFAULT nextval('cuentas_simuladas_id_cuenta_seq'::regclass);


--
-- Name: id_ejecucion; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY ejecuciones ALTER COLUMN id_ejecucion SET DEFAULT nextval('ejecuciones_id_ejecucion_seq'::regclass);


--
-- Name: id_entrenamiento; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY entrenamientos_modelo ALTER COLUMN id_entrenamiento SET DEFAULT nextval('entrenamientos_modelo_id_entrenamiento_seq'::regclass);


--
-- Name: id_fuente; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY fuentes_datos ALTER COLUMN id_fuente SET DEFAULT nextval('fuentes_datos_id_fuente_seq'::regclass);


--
-- Name: id_modelo; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY modelos_ia ALTER COLUMN id_modelo SET DEFAULT nextval('modelos_ia_id_modelo_seq'::regclass);


--
-- Name: id_operacion_cerrada; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY operaciones_cerradas ALTER COLUMN id_operacion_cerrada SET DEFAULT nextval('operaciones_cerradas_id_operacion_cerrada_seq'::regclass);


--
-- Name: id_orden; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY ordenes ALTER COLUMN id_orden SET DEFAULT nextval('ordenes_id_orden_seq'::regclass);


--
-- Name: id_posicion; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY posiciones ALTER COLUMN id_posicion SET DEFAULT nextval('posiciones_id_posicion_seq'::regclass);


--
-- Name: id_prediccion; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY predicciones_direccion ALTER COLUMN id_prediccion SET DEFAULT nextval('predicciones_direccion_id_prediccion_seq'::regclass);


--
-- Name: id_prediccion; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY predicciones_volatilidad ALTER COLUMN id_prediccion SET DEFAULT nextval('predicciones_volatilidad_id_prediccion_seq'::regclass);


--
-- Name: id_usuario; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY usuarios ALTER COLUMN id_usuario SET DEFAULT nextval('usuarios_id_usuario_seq'::regclass);


--
-- Name: activos_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY activos
    ADD CONSTRAINT activos_pkey PRIMARY KEY (id_activo);


--
-- Name: activos_ticker_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY activos
    ADD CONSTRAINT activos_ticker_key UNIQUE (ticker);


--
-- Name: cotizaciones_actuales_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY cotizaciones_actuales
    ADD CONSTRAINT cotizaciones_actuales_pkey PRIMARY KEY (id_activo);


--
-- Name: cuentas_simuladas_id_usuario_nombre_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY cuentas_simuladas
    ADD CONSTRAINT cuentas_simuladas_id_usuario_nombre_key UNIQUE (id_usuario, nombre);


--
-- Name: cuentas_simuladas_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY cuentas_simuladas
    ADD CONSTRAINT cuentas_simuladas_pkey PRIMARY KEY (id_cuenta);


--
-- Name: ejecuciones_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY ejecuciones
    ADD CONSTRAINT ejecuciones_pkey PRIMARY KEY (id_ejecucion);


--
-- Name: entrenamientos_modelo_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY entrenamientos_modelo
    ADD CONSTRAINT entrenamientos_modelo_pkey PRIMARY KEY (id_entrenamiento);


--
-- Name: explicaciones_prediccion_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY explicaciones_prediccion
    ADD CONSTRAINT explicaciones_prediccion_pkey PRIMARY KEY (id_prediccion, factor);


--
-- Name: fuentes_datos_nombre_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY fuentes_datos
    ADD CONSTRAINT fuentes_datos_nombre_key UNIQUE (nombre);


--
-- Name: fuentes_datos_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY fuentes_datos
    ADD CONSTRAINT fuentes_datos_pkey PRIMARY KEY (id_fuente);


--
-- Name: modelos_ia_nombre_version_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY modelos_ia
    ADD CONSTRAINT modelos_ia_nombre_version_key UNIQUE (nombre, version);


--
-- Name: modelos_ia_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY modelos_ia
    ADD CONSTRAINT modelos_ia_pkey PRIMARY KEY (id_modelo);


--
-- Name: operaciones_cerradas_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY operaciones_cerradas
    ADD CONSTRAINT operaciones_cerradas_pkey PRIMARY KEY (id_operacion_cerrada);


--
-- Name: ordenes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY ordenes
    ADD CONSTRAINT ordenes_pkey PRIMARY KEY (id_orden);


--
-- Name: posiciones_id_cuenta_id_activo_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY posiciones
    ADD CONSTRAINT posiciones_id_cuenta_id_activo_key UNIQUE (id_cuenta, id_activo);


--
-- Name: posiciones_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY posiciones
    ADD CONSTRAINT posiciones_pkey PRIMARY KEY (id_posicion);


--
-- Name: precios_velas_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY precios_velas
    ADD CONSTRAINT precios_velas_pkey PRIMARY KEY (id_activo, intervalo, momento);


--
-- Name: predicciones_direccion_id_activo_id_modelo_horizonte_dias_g_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY predicciones_direccion
    ADD CONSTRAINT predicciones_direccion_id_activo_id_modelo_horizonte_dias_g_key UNIQUE (id_activo, id_modelo, horizonte_dias, generada_en);


--
-- Name: predicciones_direccion_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY predicciones_direccion
    ADD CONSTRAINT predicciones_direccion_pkey PRIMARY KEY (id_prediccion);


--
-- Name: predicciones_volatilidad_id_activo_id_modelo_generada_en_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY predicciones_volatilidad
    ADD CONSTRAINT predicciones_volatilidad_id_activo_id_modelo_generada_en_key UNIQUE (id_activo, id_modelo, generada_en);


--
-- Name: predicciones_volatilidad_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY predicciones_volatilidad
    ADD CONSTRAINT predicciones_volatilidad_pkey PRIMARY KEY (id_prediccion);


--
-- Name: snapshots_portafolio_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY snapshots_portafolio
    ADD CONSTRAINT snapshots_portafolio_pkey PRIMARY KEY (id_cuenta, momento);


--
-- Name: usuarios_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY usuarios
    ADD CONSTRAINT usuarios_pkey PRIMARY KEY (id_usuario);


--
-- Name: idx_ejecuciones_cuenta; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX idx_ejecuciones_cuenta ON ejecuciones USING btree (id_cuenta, ejecutada_en DESC);


--
-- Name: idx_ejecuciones_orden; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX idx_ejecuciones_orden ON ejecuciones USING btree (id_orden);


--
-- Name: idx_entrenamientos_modelo; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX idx_entrenamientos_modelo ON entrenamientos_modelo USING btree (id_modelo, inicio_en DESC);


--
-- Name: idx_modelos_ia_activos; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX idx_modelos_ia_activos ON modelos_ia USING btree (nombre) WHERE (estado = 'activo'::estado_modelo);


--
-- Name: idx_op_cerradas_cuenta; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX idx_op_cerradas_cuenta ON operaciones_cerradas USING btree (id_cuenta, cerrada_en DESC);


--
-- Name: idx_ordenes_cuenta; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX idx_ordenes_cuenta ON ordenes USING btree (id_cuenta, creada_en DESC);


--
-- Name: idx_ordenes_pendientes; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX idx_ordenes_pendientes ON ordenes USING btree (id_activo) WHERE (estado = 'pendiente'::estado_orden);


--
-- Name: idx_pred_dir_activo; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX idx_pred_dir_activo ON predicciones_direccion USING btree (id_activo, generada_en DESC);


--
-- Name: idx_pred_dir_pendientes; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX idx_pred_dir_pendientes ON predicciones_direccion USING btree (fecha_objetivo) WHERE (acierto IS NULL);


--
-- Name: idx_pred_vol_activo; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX idx_pred_vol_activo ON predicciones_volatilidad USING btree (id_activo, generada_en DESC);


--
-- Name: idx_pred_vol_pendientes; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX idx_pred_vol_pendientes ON predicciones_volatilidad USING btree (fecha_objetivo) WHERE (rango_real IS NULL);


--
-- Name: uq_pred_dir_una_por_dia; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE UNIQUE INDEX uq_pred_dir_una_por_dia ON predicciones_direccion USING btree (id_activo, id_modelo, horizonte_dias, ((timezone('UTC'::text, generada_en))::date));


--
-- Name: uq_pred_vol_una_por_dia; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE UNIQUE INDEX uq_pred_vol_una_por_dia ON predicciones_volatilidad USING btree (id_activo, id_modelo, ((timezone('UTC'::text, generada_en))::date));


--
-- Name: uq_usuarios_email; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE UNIQUE INDEX uq_usuarios_email ON usuarios USING btree (lower((email)::text));


--
-- Name: activos_id_fuente_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY activos
    ADD CONSTRAINT activos_id_fuente_fkey FOREIGN KEY (id_fuente) REFERENCES fuentes_datos(id_fuente);


--
-- Name: cotizaciones_actuales_id_activo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY cotizaciones_actuales
    ADD CONSTRAINT cotizaciones_actuales_id_activo_fkey FOREIGN KEY (id_activo) REFERENCES activos(id_activo) ON DELETE CASCADE;


--
-- Name: cuentas_simuladas_id_usuario_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY cuentas_simuladas
    ADD CONSTRAINT cuentas_simuladas_id_usuario_fkey FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario) ON DELETE CASCADE;


--
-- Name: ejecuciones_id_activo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY ejecuciones
    ADD CONSTRAINT ejecuciones_id_activo_fkey FOREIGN KEY (id_activo) REFERENCES activos(id_activo);


--
-- Name: ejecuciones_id_cuenta_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY ejecuciones
    ADD CONSTRAINT ejecuciones_id_cuenta_fkey FOREIGN KEY (id_cuenta) REFERENCES cuentas_simuladas(id_cuenta) ON DELETE CASCADE;


--
-- Name: ejecuciones_id_orden_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY ejecuciones
    ADD CONSTRAINT ejecuciones_id_orden_fkey FOREIGN KEY (id_orden) REFERENCES ordenes(id_orden) ON DELETE CASCADE;


--
-- Name: entrenamientos_modelo_id_modelo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY entrenamientos_modelo
    ADD CONSTRAINT entrenamientos_modelo_id_modelo_fkey FOREIGN KEY (id_modelo) REFERENCES modelos_ia(id_modelo) ON DELETE CASCADE;


--
-- Name: entrenamientos_modelo_solicitado_por_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY entrenamientos_modelo
    ADD CONSTRAINT entrenamientos_modelo_solicitado_por_fkey FOREIGN KEY (solicitado_por) REFERENCES usuarios(id_usuario) ON DELETE SET NULL;


--
-- Name: explicaciones_prediccion_id_prediccion_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY explicaciones_prediccion
    ADD CONSTRAINT explicaciones_prediccion_id_prediccion_fkey FOREIGN KEY (id_prediccion) REFERENCES predicciones_direccion(id_prediccion) ON DELETE CASCADE;


--
-- Name: operaciones_cerradas_id_activo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY operaciones_cerradas
    ADD CONSTRAINT operaciones_cerradas_id_activo_fkey FOREIGN KEY (id_activo) REFERENCES activos(id_activo);


--
-- Name: operaciones_cerradas_id_cuenta_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY operaciones_cerradas
    ADD CONSTRAINT operaciones_cerradas_id_cuenta_fkey FOREIGN KEY (id_cuenta) REFERENCES cuentas_simuladas(id_cuenta) ON DELETE CASCADE;


--
-- Name: ordenes_id_activo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY ordenes
    ADD CONSTRAINT ordenes_id_activo_fkey FOREIGN KEY (id_activo) REFERENCES activos(id_activo);


--
-- Name: ordenes_id_cuenta_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY ordenes
    ADD CONSTRAINT ordenes_id_cuenta_fkey FOREIGN KEY (id_cuenta) REFERENCES cuentas_simuladas(id_cuenta) ON DELETE CASCADE;


--
-- Name: posiciones_id_activo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY posiciones
    ADD CONSTRAINT posiciones_id_activo_fkey FOREIGN KEY (id_activo) REFERENCES activos(id_activo);


--
-- Name: posiciones_id_cuenta_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY posiciones
    ADD CONSTRAINT posiciones_id_cuenta_fkey FOREIGN KEY (id_cuenta) REFERENCES cuentas_simuladas(id_cuenta) ON DELETE CASCADE;


--
-- Name: precios_velas_id_activo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY precios_velas
    ADD CONSTRAINT precios_velas_id_activo_fkey FOREIGN KEY (id_activo) REFERENCES activos(id_activo) ON DELETE CASCADE;


--
-- Name: predicciones_direccion_id_activo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY predicciones_direccion
    ADD CONSTRAINT predicciones_direccion_id_activo_fkey FOREIGN KEY (id_activo) REFERENCES activos(id_activo) ON DELETE CASCADE;


--
-- Name: predicciones_direccion_id_modelo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY predicciones_direccion
    ADD CONSTRAINT predicciones_direccion_id_modelo_fkey FOREIGN KEY (id_modelo) REFERENCES modelos_ia(id_modelo);


--
-- Name: predicciones_volatilidad_id_activo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY predicciones_volatilidad
    ADD CONSTRAINT predicciones_volatilidad_id_activo_fkey FOREIGN KEY (id_activo) REFERENCES activos(id_activo) ON DELETE CASCADE;


--
-- Name: predicciones_volatilidad_id_modelo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY predicciones_volatilidad
    ADD CONSTRAINT predicciones_volatilidad_id_modelo_fkey FOREIGN KEY (id_modelo) REFERENCES modelos_ia(id_modelo);


--
-- Name: snapshots_portafolio_id_cuenta_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY snapshots_portafolio
    ADD CONSTRAINT snapshots_portafolio_id_cuenta_fkey FOREIGN KEY (id_cuenta) REFERENCES cuentas_simuladas(id_cuenta) ON DELETE CASCADE;


--
-- Name: public; Type: ACL; Schema: -; Owner: postgres
--

REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM postgres;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO PUBLIC;


--
-- PostgreSQL database dump complete
--

