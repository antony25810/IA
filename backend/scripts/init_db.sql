-- scripts/init_db.sql
-- Script de inicialización de la base de datos

-- Habilitar extensiones
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Verificar instalación
SELECT PostGIS_Version();

-- Crear schema si no existe
CREATE SCHEMA IF NOT EXISTS public;

-- Mensaje de confirmación
DO $$
BEGIN
    RAISE NOTICE 'Base de datos inicializada correctamente';
    RAISE NOTICE 'PostGIS versión: %', PostGIS_Version();
END $$;