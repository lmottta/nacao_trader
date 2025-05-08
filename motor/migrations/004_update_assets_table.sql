-- Migração para adicionar campos que faltam na tabela assets

-- Verificar se as colunas existem antes de tentar adicioná-las
DO $$ 
BEGIN
    -- Adicionar coluna market_status, se não existir
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'assets' AND column_name = 'market_status') THEN
        ALTER TABLE public.assets ADD COLUMN market_status VARCHAR(20);
        COMMENT ON COLUMN public.assets.market_status IS 'Status atual do mercado para este ativo (open, closed, pre, post, etc.)';
    END IF;

    -- Adicionar coluna market_status_source, se não existir
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'assets' AND column_name = 'market_status_source') THEN
        ALTER TABLE public.assets ADD COLUMN market_status_source VARCHAR(50);
        COMMENT ON COLUMN public.assets.market_status_source IS 'Fonte da informação de status do mercado';
    END IF;

    -- Adicionar coluna last_status_update, se não existir
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'assets' AND column_name = 'last_status_update') THEN
        ALTER TABLE public.assets ADD COLUMN last_status_update TIMESTAMPTZ;
        COMMENT ON COLUMN public.assets.last_status_update IS 'Timestamp da última atualização do status do mercado';
    END IF;

    -- Adicionar coluna currency, se não existir
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'assets' AND column_name = 'currency') THEN
        ALTER TABLE public.assets ADD COLUMN currency VARCHAR(10);
        COMMENT ON COLUMN public.assets.currency IS 'Moeda do ativo (USD, BRL, etc.)';
    END IF;

    -- Adicionar coluna metadata, se não existir
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'assets' AND column_name = 'metadata') THEN
        ALTER TABLE public.assets ADD COLUMN metadata JSONB DEFAULT '{}'::jsonb;
        COMMENT ON COLUMN public.assets.metadata IS 'Dados adicionais específicos do ativo em formato JSON';
    END IF;

    -- Adicionar coluna ticker, se não existir
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'assets' AND column_name = 'ticker') THEN
        ALTER TABLE public.assets ADD COLUMN ticker VARCHAR(50);
        COMMENT ON COLUMN public.assets.ticker IS 'Ticker original usado para busca, pode ser diferente do symbol';
    END IF;

    -- Adicionar coluna active, se não existir
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'assets' AND column_name = 'active') THEN
        ALTER TABLE public.assets ADD COLUMN active BOOLEAN DEFAULT true;
        COMMENT ON COLUMN public.assets.active IS 'Indica se o ativo está ativo/disponível para trading';
    END IF;
END $$; 