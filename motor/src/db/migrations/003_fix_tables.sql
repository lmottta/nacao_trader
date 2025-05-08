-- Este script corrige a estrutura das tabelas para resolver os erros de coleta
-- Execute este script no painel SQL do Supabase Studio

-- 1. Verificar e corrigir a tabela 'assets'

-- Garantir que a extensão UUID esteja ativa
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Adicionar coluna currency se não existir
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_schema = 'public' 
                   AND table_name = 'assets' 
                   AND column_name = 'currency') THEN
        ALTER TABLE public.assets ADD COLUMN currency VARCHAR(10) DEFAULT 'USD';
    END IF;
END
$$;

-- Adicionar coluna active se não existir
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_schema = 'public' 
                   AND table_name = 'assets' 
                   AND column_name = 'active') THEN
        ALTER TABLE public.assets ADD COLUMN active BOOLEAN DEFAULT TRUE;
    END IF;
END
$$;

-- Verificar e adicionar restrição única para symbol
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint c
        JOIN pg_namespace n ON n.oid = c.connamespace
        WHERE c.conname = 'assets_symbol_unique'
        AND n.nspname = 'public'
    ) THEN
        ALTER TABLE public.assets ADD CONSTRAINT assets_symbol_unique UNIQUE (symbol);
    END IF;
EXCEPTION
    WHEN others THEN
        RAISE NOTICE 'Erro ao adicionar restrição unique: %', SQLERRM;
END
$$;

-- 2. Verificar e corrigir a tabela 'price_history'

-- Adicionar restrição única para symbol + timestamp + timeframe
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint c
        JOIN pg_namespace n ON n.oid = c.connamespace
        WHERE c.conname = 'price_history_unique'
        AND n.nspname = 'public'
    ) THEN
        ALTER TABLE public.price_history ADD CONSTRAINT price_history_unique UNIQUE (symbol, timestamp, timeframe);
    END IF;
EXCEPTION
    WHEN others THEN
        RAISE NOTICE 'Erro ao adicionar restrição unique: %', SQLERRM;
END
$$;

-- 3. Configurar TimescaleDB se disponível
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
        IF NOT EXISTS (
            SELECT 1
            FROM _timescaledb_catalog.hypertable h
            JOIN _timescaledb_catalog.hypertable_schema s ON h.id = s.hypertable_id
            WHERE s.schema_name = 'public' AND h.table_name = 'price_history'
        ) THEN
            PERFORM create_hypertable('public.price_history', 'timestamp', 
                                 chunk_time_interval => interval '1 week',
                                 if_not_exists => TRUE);
        END IF;
    END IF;
EXCEPTION
    WHEN others THEN
        RAISE NOTICE 'Erro ao configurar TimescaleDB: %', SQLERRM;
END
$$; 