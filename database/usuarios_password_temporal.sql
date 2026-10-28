-- =====================================================================
-- SIMULTRADIA · Contraseña temporal (el administrador la entrega y el usuario debe cambiarla al entrar)
-- =====================================================================
-- Ejecutar UNA vez ANTES de usar esta versión de la aplicación (sin esta columna el login falla):
--   psql -d simulador_trading -v ON_ERROR_STOP=1 -f database/usuarios_password_temporal.sql
-- Después puedes borrar este archivo.
-- =====================================================================
ALTER TABLE usuarios ADD COLUMN debe_cambiar_password BOOLEAN NOT NULL DEFAULT FALSE;
