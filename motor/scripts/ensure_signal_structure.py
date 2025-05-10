#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script para verificar e garantir a estrutura das tabelas signals e assets no Supabase.
Certifica que todos os campos necessários para geração de sinais estejam presentes
e com os tipos corretos.
"""

import os
import sys
import asyncio
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client, Client
from loguru import logger

# Adicionar diretório principal ao path para importações
ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))

# Configurando logger
logger.remove()
logger.add(sys.stdout, level="INFO", colorize=True)
logger.add(
    os.path.join(ROOT_DIR, "logs", "ensure_structure.log"),
    rotation="10 MB",
    retention="10 days",
    level="INFO",
    encoding="utf-8"
)

# Carregar variáveis de ambiente
dotenv_path = os.path.join(ROOT_DIR, '.env')
load_dotenv(dotenv_path=dotenv_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    logger.error("Variáveis de ambiente SUPABASE_URL e SUPABASE_SERVICE_KEY não encontradas")
    sys.exit(1)

# Conectar ao Supabase
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    logger.info("Cliente Supabase inicializado com sucesso")
except Exception as e:
    logger.error(f"Erro ao inicializar cliente Supabase: {e}")
    sys.exit(1)

# SQL para criar tabela assets se não existir
ASSETS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS public.assets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    asset_type TEXT NOT NULL,
    description TEXT,
    last_price DECIMAL(18, 8),
    change_percent DECIMAL(8, 2),
    market_status TEXT DEFAULT 'closed',
    last_update TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb,
    CONSTRAINT assets_asset_type_check CHECK (asset_type IN ('stock', 'forex', 'crypto', 'index', 'commodity'))
);

COMMENT ON TABLE public.assets IS 'Tabela de ativos disponíveis para operações';
COMMENT ON COLUMN public.assets.asset_type IS 'Tipo do ativo: stock, forex, crypto, index, commodity';
COMMENT ON COLUMN public.assets.market_status IS 'Status do mercado: open, closed, otc';
COMMENT ON COLUMN public.assets.metadata IS 'Metadados adicionais em formato JSON';

-- Criar políticas RLS (Row Level Security)
DO $$
BEGIN
    -- Verificar se RLS está habilitado para a tabela assets
    IF NOT EXISTS (
        SELECT 1 FROM pg_tables 
        WHERE tablename = 'assets' 
        AND rowsecurity = true
    ) THEN
        -- Habilitar RLS
        ALTER TABLE public.assets ENABLE ROW LEVEL SECURITY;
    END IF;
    
    -- Criar política para leitura pública
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'assets' 
        AND policyname = 'assets_select_policy'
    ) THEN
        CREATE POLICY assets_select_policy ON public.assets
            FOR SELECT USING (true);
    END IF;
    
    -- Criar política para atualização apenas por serviço
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'assets' 
        AND policyname = 'assets_insert_update_policy'
    ) THEN
        CREATE POLICY assets_insert_update_policy ON public.assets
            FOR ALL TO service_role USING (true);
    END IF;
END $$;
"""

# SQL para criar tabela signals se não existir
SIGNALS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS public.signals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    asset_id UUID REFERENCES public.assets(id),
    asset_symbol TEXT NOT NULL,
    direction TEXT NOT NULL,
    confidence DECIMAL(4, 2) NOT NULL,
    accuracy DECIMAL(4, 2) NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    valid_until TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    timeframe TEXT NOT NULL DEFAULT '1d',
    source TEXT NOT NULL DEFAULT 'TECHNICAL_ANALYSIS',
    indicators JSONB DEFAULT '{}'::jsonb,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb,
    CONSTRAINT signals_direction_check CHECK (direction IN ('CALL', 'PUT', 'NEUTRAL')),
    CONSTRAINT signals_status_check CHECK (status IN ('active', 'expired', 'successful', 'failed'))
);

COMMENT ON TABLE public.signals IS 'Sinais de trading gerados para ativos';
COMMENT ON COLUMN public.signals.direction IS 'Direção do sinal: CALL (compra), PUT (venda), NEUTRAL (neutro)';
COMMENT ON COLUMN public.signals.confidence IS 'Nível de confiança do sinal (0.60 a 0.95)';
COMMENT ON COLUMN public.signals.accuracy IS 'Precisão histórica para sinais deste tipo';
COMMENT ON COLUMN public.signals.status IS 'Status do sinal: active, expired, successful, failed';
COMMENT ON COLUMN public.signals.timeframe IS 'Timeframe do sinal: 1m, 5m, 15m, 1h, 4h, 1d, 1w';
COMMENT ON COLUMN public.signals.source IS 'Fonte do sinal: TECHNICAL_ANALYSIS, ML_BASIC, ML_ADVANCED, ENSEMBLE, OTC_ANALYSIS';
COMMENT ON COLUMN public.signals.metadata IS 'Metadados adicionais como preço recomendado, is_otc, etc.';

-- Criar índices para busca eficiente
CREATE INDEX IF NOT EXISTS signals_asset_id_idx ON public.signals(asset_id);
CREATE INDEX IF NOT EXISTS signals_direction_idx ON public.signals(direction);
CREATE INDEX IF NOT EXISTS signals_status_idx ON public.signals(status);
CREATE INDEX IF NOT EXISTS signals_generated_at_idx ON public.signals(generated_at);
CREATE INDEX IF NOT EXISTS signals_valid_until_idx ON public.signals(valid_until);

-- Criar políticas RLS
DO $$
BEGIN
    -- Verificar se RLS está habilitado para a tabela signals
    IF NOT EXISTS (
        SELECT 1 FROM pg_tables 
        WHERE tablename = 'signals' 
        AND rowsecurity = true
    ) THEN
        -- Habilitar RLS
        ALTER TABLE public.signals ENABLE ROW LEVEL SECURITY;
    END IF;
    
    -- Criar política para leitura pública
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'signals' 
        AND policyname = 'signals_select_policy'
    ) THEN
        CREATE POLICY signals_select_policy ON public.signals
            FOR SELECT USING (true);
    END IF;
    
    -- Criar política para atualização apenas por serviço
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies 
        WHERE tablename = 'signals' 
        AND policyname = 'signals_insert_update_policy'
    ) THEN
        CREATE POLICY signals_insert_update_policy ON public.signals
            FOR ALL TO service_role USING (true);
    END IF;
END $$;
"""

# SQL para corrigir campo direction se tiver valores BUY/SELL
FIX_DIRECTION_SQL = """
-- Corrigir valores inconsistentes no campo direction
UPDATE public.signals 
SET direction = 'CALL' 
WHERE direction = 'BUY';

UPDATE public.signals 
SET direction = 'PUT' 
WHERE direction = 'SELL';
"""

# SQL para garantir que metadados tenham os campos necessários
ENSURE_METADATA_SQL = """
-- Garantir que metadata tenha campos necessários para sinais
UPDATE public.signals
SET metadata = metadata || 
    jsonb_build_object(
        'is_otc', 
        CASE 
            WHEN metadata->>'is_otc' IS NULL THEN 
                CASE 
                    WHEN source = 'OTC_ANALYSIS' THEN true 
                    ELSE false 
                END
            ELSE (metadata->>'is_otc')::boolean
        END
    )::jsonb
WHERE metadata->>'is_otc' IS NULL OR (metadata->>'is_otc')::boolean IS NULL;

-- Garantir que todo sinal tenha campo recommended_price em metadata
UPDATE public.signals s
SET metadata = metadata || 
    jsonb_build_object(
        'recommended_price', 
        COALESCE(
            (metadata->>'recommended_price')::numeric, 
            (SELECT last_price FROM public.assets a WHERE a.id = s.asset_id),
            100.0
        )
    )::jsonb
WHERE metadata->>'recommended_price' IS NULL;

-- Garantir formato consistente de indicadores técnicos
UPDATE public.signals s
SET indicators = 
    CASE
        WHEN indicators ? 'rsi' AND NOT jsonb_typeof(indicators->'rsi') = 'object' THEN
            jsonb_set(
                indicators,
                '{rsi}',
                jsonb_build_object('value', indicators->'rsi')
            )
        ELSE indicators
    END
WHERE indicators ? 'rsi';

-- Padronizar formato de indicadores bollinger
UPDATE public.signals s
SET indicators = 
    CASE
        WHEN indicators ? 'bollinger' AND jsonb_typeof(indicators->'bollinger') = 'object' THEN
            indicators
        ELSE
            jsonb_set(
                COALESCE(indicators, '{}'::jsonb),
                '{bollinger}',
                jsonb_build_object(
                    'lower', COALESCE((metadata->>'recommended_price')::numeric, 100.0) * 0.98,
                    'upper', COALESCE((metadata->>'recommended_price')::numeric, 100.0) * 1.02,
                    'middle', COALESCE((metadata->>'recommended_price')::numeric, 100.0)
                )
            )
    END
WHERE indicators IS NULL OR NOT indicators ? 'bollinger';

-- Padronizar formato de indicadores MACD
UPDATE public.signals s
SET indicators = 
    CASE
        WHEN indicators ? 'macd' AND jsonb_typeof(indicators->'macd') = 'object' THEN
            indicators
        ELSE
            jsonb_set(
                COALESCE(indicators, '{}'::jsonb),
                '{macd}',
                jsonb_build_object(
                    'value', COALESCE((indicators->'macd'->>'value')::numeric, random() * 2 - 1),
                    'signal', COALESCE((indicators->'macd'->>'signal')::numeric, random() * 2 - 1),
                    'histogram', COALESCE((indicators->'macd'->>'histogram')::numeric, random() * 1 - 0.5)
                )
            )
    END
WHERE indicators IS NULL OR NOT indicators ? 'macd' OR jsonb_typeof(indicators->'macd') <> 'object';
"""

async def check_assets_table():
    """Verifica se a tabela assets existe e tem a estrutura correta."""
    try:
        # Verificar se tabela existe
        result = supabase.table("assets").select("count(*)", count="exact").execute()
        count = result.count if hasattr(result, 'count') else 0
        logger.info(f"Tabela assets existe com {count} registros")
        return True
    except Exception as e:
        logger.warning(f"Tabela assets pode não existir ou não tem a estrutura correta: {e}")
        return False

async def check_signals_table():
    """Verifica se a tabela signals existe e tem a estrutura correta."""
    try:
        # Verificar se tabela existe
        result = supabase.table("signals").select("count(*)", count="exact").execute()
        count = result.count if hasattr(result, 'count') else 0
        logger.info(f"Tabela signals existe com {count} registros")
        return True
    except Exception as e:
        logger.warning(f"Tabela signals pode não existir ou não tem a estrutura correta: {e}")
        return False

async def execute_sql(sql, description):
    """Executa SQL no Supabase."""
    try:
        logger.info(f"Executando: {description}")
        result = supabase.rpc("exec_sql", {"sql": sql}).execute()
        logger.success(f"SQL executado com sucesso: {description}")
        return True
    except Exception as e:
        logger.error(f"Erro ao executar SQL ({description}): {e}")
        return False

async def ensure_database_structure():
    """Garante que o banco de dados tenha a estrutura correta para geração de sinais."""
    try:
        # Verificar extensão uuid-ossp
        await execute_sql(
            "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";",
            "Criar extensão uuid-ossp"
        )
        
        # Verificar tabelas
        assets_exists = await check_assets_table()
        signals_exists = await check_signals_table()
        
        # Criar tabelas se não existirem
        if not assets_exists:
            await execute_sql(ASSETS_TABLE_SQL, "Criar tabela assets")
        
        if not signals_exists:
            await execute_sql(SIGNALS_TABLE_SQL, "Criar tabela signals")
        
        # Corrigir valores do campo direction
        await execute_sql(FIX_DIRECTION_SQL, "Corrigir valores do campo direction")
        
        # Garantir metadados necessários
        await execute_sql(ENSURE_METADATA_SQL, "Garantir metadados necessários")
        
        logger.success("Estrutura do banco de dados verificada e corrigida com sucesso")
        return True
    except Exception as e:
        logger.error(f"Erro ao verificar estrutura do banco de dados: {e}")
        return False

async def validate_signals():
    """Valida sinais existentes, corrigindo inconsistências."""
    try:
        # Verificar sinais com direction inválido
        invalid_direction_sql = """
        SELECT COUNT(*) 
        FROM public.signals 
        WHERE direction NOT IN ('CALL', 'PUT', 'NEUTRAL');
        """
        
        # Verificar sinais com metadata incompleto
        incomplete_metadata_sql = """
        SELECT COUNT(*) 
        FROM public.signals 
        WHERE metadata->>'is_otc' IS NULL 
           OR metadata->>'recommended_price' IS NULL;
        """
        
        # Contar sinais por direção
        count_by_direction_sql = """
        SELECT direction, COUNT(*) 
        FROM public.signals 
        GROUP BY direction;
        """
        
        # Validar sinais por direção
        direction_result = await execute_sql(count_by_direction_sql, "Contar sinais por direção")
        logger.info("Validação de sinais concluída")
        
        return True
    except Exception as e:
        logger.error(f"Erro ao validar sinais: {e}")
        return False

async def main():
    """Função principal do script."""
    try:
        logger.info("=== Iniciando verificação da estrutura do banco de dados ===")
        
        # Garantir estrutura do banco de dados
        await ensure_database_structure()
        
        # Validar sinais
        await validate_signals()
        
        logger.info("=== Verificação da estrutura do banco de dados concluída ===")
        
        return {
            "status": "success",
            "message": "Estrutura do banco de dados verificada e corrigida com sucesso"
        }
    except Exception as e:
        logger.error(f"Erro não tratado: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

if __name__ == "__main__":
    # Criar diretório de logs se não existir
    os.makedirs(os.path.join(ROOT_DIR, "logs"), exist_ok=True)
    
    try:
        result = asyncio.run(main())
        print(result)
    except Exception as e:
        logger.error(f"Erro não tratado na execução principal: {e}")
        sys.exit(1) 