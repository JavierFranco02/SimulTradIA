--
-- PostgreSQL database dump
--

-- Dumped from database version 9.3.5
-- Dumped by pg_dump version 9.3.5
-- Started on 2026-11-11 10:23:47

SET statement_timeout = 0;
SET lock_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;

--
-- TOC entry 188 (class 3079 OID 11750)
-- Name: plpgsql; Type: EXTENSION; Schema: -; Owner: 
--

CREATE EXTENSION IF NOT EXISTS plpgsql WITH SCHEMA pg_catalog;


--
-- TOC entry 2111 (class 0 OID 0)
-- Dependencies: 188
-- Name: EXTENSION plpgsql; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION plpgsql IS 'PL/pgSQL procedural language';


SET search_path = public, pg_catalog;

--
-- TOC entry 572 (class 1247 OID 90556)
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
-- TOC entry 548 (class 1247 OID 74194)
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
-- TOC entry 566 (class 1247 OID 90539)
-- Name: lado_orden; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE lado_orden AS ENUM (
    'compra',
    'venta'
);


ALTER TYPE public.lado_orden OWNER TO postgres;

--
-- TOC entry 534 (class 1247 OID 65987)
-- Name: rol_usuario; Type: TYPE; Schema: public; Owner: postgres
--

CREATE TYPE rol_usuario AS ENUM (
    'usuario',
    'admin'
);


ALTER TYPE public.rol_usuario OWNER TO postgres;

--
-- TOC entry 545 (class 1247 OID 74180)
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
-- TOC entry 569 (class 1247 OID 90544)
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
-- TOC entry 175 (class 1259 OID 74211)
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
-- TOC entry 174 (class 1259 OID 74209)
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
-- TOC entry 2112 (class 0 OID 0)
-- Dependencies: 174
-- Name: activos_id_activo_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE activos_id_activo_seq OWNED BY activos.id_activo;


--
-- TOC entry 177 (class 1259 OID 74237)
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
-- TOC entry 173 (class 1259 OID 74156)
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
-- TOC entry 172 (class 1259 OID 74154)
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
-- TOC entry 2113 (class 0 OID 0)
-- Dependencies: 172
-- Name: cuentas_simuladas_id_cuenta_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE cuentas_simuladas_id_cuenta_seq OWNED BY cuentas_simuladas.id_cuenta;


--
-- TOC entry 183 (class 1259 OID 90596)
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
-- TOC entry 182 (class 1259 OID 90594)
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
-- TOC entry 2114 (class 0 OID 0)
-- Dependencies: 182
-- Name: ejecuciones_id_ejecucion_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE ejecuciones_id_ejecucion_seq OWNED BY ejecuciones.id_ejecucion;


--
-- TOC entry 179 (class 1259 OID 74250)
-- Name: fuentes_datos; Type: TABLE; Schema: public; Owner: postgres; Tablespace: 
--

CREATE TABLE fuentes_datos (
    id_fuente bigint NOT NULL,
    nombre character varying(80) NOT NULL,
    activa boolean DEFAULT true NOT NULL
);


ALTER TABLE public.fuentes_datos OWNER TO postgres;

--
-- TOC entry 178 (class 1259 OID 74248)
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
-- TOC entry 2115 (class 0 OID 0)
-- Dependencies: 178
-- Name: fuentes_datos_id_fuente_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE fuentes_datos_id_fuente_seq OWNED BY fuentes_datos.id_fuente;


--
-- TOC entry 187 (class 1259 OID 90651)
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
-- TOC entry 186 (class 1259 OID 90649)
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
-- TOC entry 2116 (class 0 OID 0)
-- Dependencies: 186
-- Name: operaciones_cerradas_id_operacion_cerrada_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE operaciones_cerradas_id_operacion_cerrada_seq OWNED BY operaciones_cerradas.id_operacion_cerrada;


--
-- TOC entry 181 (class 1259 OID 90571)
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
-- TOC entry 180 (class 1259 OID 90569)
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
-- TOC entry 2117 (class 0 OID 0)
-- Dependencies: 180
-- Name: ordenes_id_orden_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE ordenes_id_orden_seq OWNED BY ordenes.id_orden;


--
-- TOC entry 185 (class 1259 OID 90626)
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
-- TOC entry 184 (class 1259 OID 90624)
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
-- TOC entry 2118 (class 0 OID 0)
-- Dependencies: 184
-- Name: posiciones_id_posicion_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE posiciones_id_posicion_seq OWNED BY posiciones.id_posicion;


--
-- TOC entry 176 (class 1259 OID 74222)
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
-- TOC entry 171 (class 1259 OID 65993)
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
-- TOC entry 170 (class 1259 OID 65991)
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
-- TOC entry 2119 (class 0 OID 0)
-- Dependencies: 170
-- Name: usuarios_id_usuario_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE usuarios_id_usuario_seq OWNED BY usuarios.id_usuario;


--
-- TOC entry 1910 (class 2604 OID 74214)
-- Name: id_activo; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY activos ALTER COLUMN id_activo SET DEFAULT nextval('activos_id_activo_seq'::regclass);


--
-- TOC entry 1899 (class 2604 OID 74159)
-- Name: id_cuenta; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY cuentas_simuladas ALTER COLUMN id_cuenta SET DEFAULT nextval('cuentas_simuladas_id_cuenta_seq'::regclass);


--
-- TOC entry 1933 (class 2604 OID 90599)
-- Name: id_ejecucion; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY ejecuciones ALTER COLUMN id_ejecucion SET DEFAULT nextval('ejecuciones_id_ejecucion_seq'::regclass);


--
-- TOC entry 1920 (class 2604 OID 74253)
-- Name: id_fuente; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY fuentes_datos ALTER COLUMN id_fuente SET DEFAULT nextval('fuentes_datos_id_fuente_seq'::regclass);


--
-- TOC entry 1947 (class 2604 OID 90654)
-- Name: id_operacion_cerrada; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY operaciones_cerradas ALTER COLUMN id_operacion_cerrada SET DEFAULT nextval('operaciones_cerradas_id_operacion_cerrada_seq'::regclass);


--
-- TOC entry 1922 (class 2604 OID 90574)
-- Name: id_orden; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY ordenes ALTER COLUMN id_orden SET DEFAULT nextval('ordenes_id_orden_seq'::regclass);


--
-- TOC entry 1939 (class 2604 OID 90629)
-- Name: id_posicion; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY posiciones ALTER COLUMN id_posicion SET DEFAULT nextval('posiciones_id_posicion_seq'::regclass);


--
-- TOC entry 1893 (class 2604 OID 65996)
-- Name: id_usuario; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY usuarios ALTER COLUMN id_usuario SET DEFAULT nextval('usuarios_id_usuario_seq'::regclass);


--
-- TOC entry 1958 (class 2606 OID 74219)
-- Name: activos_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY activos
    ADD CONSTRAINT activos_pkey PRIMARY KEY (id_activo);


--
-- TOC entry 1960 (class 2606 OID 74221)
-- Name: activos_ticker_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY activos
    ADD CONSTRAINT activos_ticker_key UNIQUE (ticker);


--
-- TOC entry 1964 (class 2606 OID 74242)
-- Name: cotizaciones_actuales_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY cotizaciones_actuales
    ADD CONSTRAINT cotizaciones_actuales_pkey PRIMARY KEY (id_activo);


--
-- TOC entry 1954 (class 2606 OID 74173)
-- Name: cuentas_simuladas_id_usuario_nombre_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY cuentas_simuladas
    ADD CONSTRAINT cuentas_simuladas_id_usuario_nombre_key UNIQUE (id_usuario, nombre);


--
-- TOC entry 1956 (class 2606 OID 74171)
-- Name: cuentas_simuladas_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY cuentas_simuladas
    ADD CONSTRAINT cuentas_simuladas_pkey PRIMARY KEY (id_cuenta);


--
-- TOC entry 1974 (class 2606 OID 90606)
-- Name: ejecuciones_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY ejecuciones
    ADD CONSTRAINT ejecuciones_pkey PRIMARY KEY (id_ejecucion);


--
-- TOC entry 1966 (class 2606 OID 74258)
-- Name: fuentes_datos_nombre_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY fuentes_datos
    ADD CONSTRAINT fuentes_datos_nombre_key UNIQUE (nombre);


--
-- TOC entry 1968 (class 2606 OID 74256)
-- Name: fuentes_datos_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY fuentes_datos
    ADD CONSTRAINT fuentes_datos_pkey PRIMARY KEY (id_fuente);


--
-- TOC entry 1983 (class 2606 OID 90658)
-- Name: operaciones_cerradas_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY operaciones_cerradas
    ADD CONSTRAINT operaciones_cerradas_pkey PRIMARY KEY (id_operacion_cerrada);


--
-- TOC entry 1972 (class 2606 OID 90582)
-- Name: ordenes_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY ordenes
    ADD CONSTRAINT ordenes_pkey PRIMARY KEY (id_orden);


--
-- TOC entry 1978 (class 2606 OID 90638)
-- Name: posiciones_id_cuenta_id_activo_key; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY posiciones
    ADD CONSTRAINT posiciones_id_cuenta_id_activo_key UNIQUE (id_cuenta, id_activo);


--
-- TOC entry 1980 (class 2606 OID 90636)
-- Name: posiciones_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY posiciones
    ADD CONSTRAINT posiciones_pkey PRIMARY KEY (id_posicion);


--
-- TOC entry 1962 (class 2606 OID 74231)
-- Name: precios_velas_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY precios_velas
    ADD CONSTRAINT precios_velas_pkey PRIMARY KEY (id_activo, intervalo, momento);


--
-- TOC entry 1952 (class 2606 OID 66005)
-- Name: usuarios_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres; Tablespace: 
--

ALTER TABLE ONLY usuarios
    ADD CONSTRAINT usuarios_pkey PRIMARY KEY (id_usuario);


--
-- TOC entry 1975 (class 1259 OID 90622)
-- Name: idx_ejecuciones_cuenta; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX idx_ejecuciones_cuenta ON ejecuciones USING btree (id_cuenta, ejecutada_en DESC);


--
-- TOC entry 1976 (class 1259 OID 90623)
-- Name: idx_ejecuciones_orden; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX idx_ejecuciones_orden ON ejecuciones USING btree (id_orden);


--
-- TOC entry 1981 (class 1259 OID 90669)
-- Name: idx_op_cerradas_cuenta; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX idx_op_cerradas_cuenta ON operaciones_cerradas USING btree (id_cuenta, cerrada_en DESC);


--
-- TOC entry 1969 (class 1259 OID 90593)
-- Name: idx_ordenes_cuenta; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX idx_ordenes_cuenta ON ordenes USING btree (id_cuenta, creada_en DESC);


--
-- TOC entry 1970 (class 1259 OID 90681)
-- Name: idx_ordenes_pendientes; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE INDEX idx_ordenes_pendientes ON ordenes USING btree (id_activo) WHERE (estado = 'pendiente'::estado_orden);


--
-- TOC entry 1950 (class 1259 OID 66006)
-- Name: uq_usuarios_email; Type: INDEX; Schema: public; Owner: postgres; Tablespace: 
--

CREATE UNIQUE INDEX uq_usuarios_email ON usuarios USING btree (lower((email)::text));


--
-- TOC entry 1985 (class 2606 OID 74259)
-- Name: activos_id_fuente_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY activos
    ADD CONSTRAINT activos_id_fuente_fkey FOREIGN KEY (id_fuente) REFERENCES fuentes_datos(id_fuente);


--
-- TOC entry 1987 (class 2606 OID 74243)
-- Name: cotizaciones_actuales_id_activo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY cotizaciones_actuales
    ADD CONSTRAINT cotizaciones_actuales_id_activo_fkey FOREIGN KEY (id_activo) REFERENCES activos(id_activo) ON DELETE CASCADE;


--
-- TOC entry 1984 (class 2606 OID 74174)
-- Name: cuentas_simuladas_id_usuario_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY cuentas_simuladas
    ADD CONSTRAINT cuentas_simuladas_id_usuario_fkey FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario) ON DELETE CASCADE;


--
-- TOC entry 1992 (class 2606 OID 90617)
-- Name: ejecuciones_id_activo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY ejecuciones
    ADD CONSTRAINT ejecuciones_id_activo_fkey FOREIGN KEY (id_activo) REFERENCES activos(id_activo);


--
-- TOC entry 1991 (class 2606 OID 90612)
-- Name: ejecuciones_id_cuenta_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY ejecuciones
    ADD CONSTRAINT ejecuciones_id_cuenta_fkey FOREIGN KEY (id_cuenta) REFERENCES cuentas_simuladas(id_cuenta) ON DELETE CASCADE;


--
-- TOC entry 1990 (class 2606 OID 90607)
-- Name: ejecuciones_id_orden_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY ejecuciones
    ADD CONSTRAINT ejecuciones_id_orden_fkey FOREIGN KEY (id_orden) REFERENCES ordenes(id_orden) ON DELETE CASCADE;


--
-- TOC entry 1996 (class 2606 OID 90664)
-- Name: operaciones_cerradas_id_activo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY operaciones_cerradas
    ADD CONSTRAINT operaciones_cerradas_id_activo_fkey FOREIGN KEY (id_activo) REFERENCES activos(id_activo);


--
-- TOC entry 1995 (class 2606 OID 90659)
-- Name: operaciones_cerradas_id_cuenta_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY operaciones_cerradas
    ADD CONSTRAINT operaciones_cerradas_id_cuenta_fkey FOREIGN KEY (id_cuenta) REFERENCES cuentas_simuladas(id_cuenta) ON DELETE CASCADE;


--
-- TOC entry 1989 (class 2606 OID 90588)
-- Name: ordenes_id_activo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY ordenes
    ADD CONSTRAINT ordenes_id_activo_fkey FOREIGN KEY (id_activo) REFERENCES activos(id_activo);


--
-- TOC entry 1988 (class 2606 OID 90583)
-- Name: ordenes_id_cuenta_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY ordenes
    ADD CONSTRAINT ordenes_id_cuenta_fkey FOREIGN KEY (id_cuenta) REFERENCES cuentas_simuladas(id_cuenta) ON DELETE CASCADE;


--
-- TOC entry 1993 (class 2606 OID 90644)
-- Name: posiciones_id_activo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY posiciones
    ADD CONSTRAINT posiciones_id_activo_fkey FOREIGN KEY (id_activo) REFERENCES activos(id_activo);


--
-- TOC entry 1994 (class 2606 OID 90639)
-- Name: posiciones_id_cuenta_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY posiciones
    ADD CONSTRAINT posiciones_id_cuenta_fkey FOREIGN KEY (id_cuenta) REFERENCES cuentas_simuladas(id_cuenta) ON DELETE CASCADE;


--
-- TOC entry 1986 (class 2606 OID 74232)
-- Name: precios_velas_id_activo_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY precios_velas
    ADD CONSTRAINT precios_velas_id_activo_fkey FOREIGN KEY (id_activo) REFERENCES activos(id_activo) ON DELETE CASCADE;


--
-- TOC entry 2110 (class 0 OID 0)
-- Dependencies: 5
-- Name: public; Type: ACL; Schema: -; Owner: postgres
--

REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM postgres;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO PUBLIC;


-- Completed on 2026-11-11 10:23:47

--
-- PostgreSQL database dump complete
--

