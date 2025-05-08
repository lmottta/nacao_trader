"""
Script para criar as tabelas necessárias no Supabase.

Este script deve ser executado apenas uma vez durante a instalação
do motor. As operações são idempotentes (podem ser executadas
múltiplas vezes sem efeitos colaterais).
"""
import asyncio
from typing import List

from loguru import logger

from src.utils.supabase_client import get_supabase_client


async def run_migration():
    """Executa a migração, criando as tabelas necessárias."""
    client = get_supabase_client()
    
    # Definir as migrações com queries SQL
    migrations = [
        # Assets (ativos financeiros)
        """
        CREATE TABLE IF NOT EXISTS assets (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            symbol TEXT NOT NULL,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            data_source TEXT NOT NULL,
            last_updated TIMESTAMPTZ DEFAULT now(),
            metadata JSONB,
            created_at TIMESTAMPTZ DEFAULT now(),
            UNIQUE(symbol, type)
        );
        
        CREATE INDEX IF NOT EXISTS assets_symbol_idx ON assets (symbol);
        CREATE INDEX IF NOT EXISTS assets_type_idx ON assets (type);
        
        ALTER TABLE assets ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS "Allow SELECT for authenticated users" ON assets;
        CREATE POLICY "Allow SELECT for authenticated users" 
            ON assets FOR SELECT 
            USING (auth.role() = 'authenticated');
        DROP POLICY IF EXISTS "Allow INSERT/UPDATE for service role" ON assets;
        CREATE POLICY "Allow INSERT/UPDATE for service role" 
            ON assets FOR ALL 
            USING (auth.role() = 'service_role');
        """,
        
        # Signals (sinais de trading)
        """
        CREATE TABLE IF NOT EXISTS signals (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            asset_id TEXT NOT NULL,
            asset_symbol TEXT NOT NULL,
            direction TEXT NOT NULL,
            confidence NUMERIC(10, 8) NOT NULL,
            price_target NUMERIC(18, 8),
            stop_loss NUMERIC(18, 8),
            generated_at TIMESTAMPTZ NOT NULL,
            valid_until TIMESTAMPTZ,
            status TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            source TEXT NOT NULL,
            indicators JSONB,
            model_performance JSONB,
            notes TEXT,
            created_at TIMESTAMPTZ DEFAULT now(),
            created_by TEXT DEFAULT 'system'
        );
        
        CREATE INDEX IF NOT EXISTS signals_asset_id_idx ON signals (asset_id);
        CREATE INDEX IF NOT EXISTS signals_asset_symbol_idx ON signals (asset_symbol);
        CREATE INDEX IF NOT EXISTS signals_generated_at_idx ON signals (generated_at);
        CREATE INDEX IF NOT EXISTS signals_direction_idx ON signals (direction);
        
        ALTER TABLE signals ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS "Allow SELECT for authenticated users" ON signals;
        CREATE POLICY "Allow SELECT for authenticated users" 
            ON signals FOR SELECT 
            USING (auth.role() = 'authenticated');
        DROP POLICY IF EXISTS "Allow INSERT/UPDATE for service role" ON signals;
        CREATE POLICY "Allow INSERT/UPDATE for service role" 
            ON signals FOR ALL 
            USING (auth.role() = 'service_role');
        """,
        
        # Price History (histórico de preços)
        """
        CREATE TABLE IF NOT EXISTS price_history (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            symbol TEXT NOT NULL,
            timestamp TIMESTAMPTZ NOT NULL,
            timeframe TEXT NOT NULL,
            open NUMERIC(18, 8) NOT NULL,
            high NUMERIC(18, 8) NOT NULL,
            low NUMERIC(18, 8) NOT NULL,
            close NUMERIC(18, 8) NOT NULL,
            volume NUMERIC(38, 8) DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT now(),
            UNIQUE(symbol, timestamp, timeframe)
        );
        
        CREATE INDEX IF NOT EXISTS price_history_symbol_idx ON price_history (symbol);
        CREATE INDEX IF NOT EXISTS price_history_timestamp_idx ON price_history (timestamp);
        CREATE INDEX IF NOT EXISTS price_history_timeframe_idx ON price_history (timeframe);
        
        -- Habilitar TimescaleDB se disponível
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM pg_extension
                WHERE extname = 'timescaledb'
            ) THEN
                PERFORM create_hypertable('price_history', 'timestamp', if_not_exists => TRUE);
            END IF;
        END
        $$;
        
        ALTER TABLE price_history ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS "Allow SELECT for authenticated users" ON price_history;
        CREATE POLICY "Allow SELECT for authenticated users" 
            ON price_history FOR SELECT 
            USING (auth.role() = 'authenticated');
        DROP POLICY IF EXISTS "Allow INSERT/UPDATE for service role" ON price_history;
        CREATE POLICY "Allow INSERT/UPDATE for service role" 
            ON price_history FOR ALL 
            USING (auth.role() = 'service_role');
        """,
        
        # Model Registry (registro de modelos ML)
        """
        CREATE TABLE IF NOT EXISTS model_registry (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            model_name TEXT NOT NULL,
            asset_id TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            model_type TEXT NOT NULL,
            model_version TEXT NOT NULL,
            accuracy NUMERIC(10, 8),
            precision NUMERIC(10, 8),
            recall NUMERIC(10, 8),
            f1_score NUMERIC(10, 8),
            training_date TIMESTAMPTZ NOT NULL,
            model_params JSONB,
            model_features JSONB,
            metrics JSONB,
            storage_path TEXT,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now(),
            created_by TEXT DEFAULT 'system',
            status TEXT DEFAULT 'active'
        );
        
        CREATE INDEX IF NOT EXISTS model_registry_asset_id_idx ON model_registry (asset_id);
        CREATE INDEX IF NOT EXISTS model_registry_timeframe_idx ON model_registry (timeframe);
        
        ALTER TABLE model_registry ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS "Allow SELECT for authenticated users" ON model_registry;
        CREATE POLICY "Allow SELECT for authenticated users" 
            ON model_registry FOR SELECT 
            USING (auth.role() = 'authenticated');
        DROP POLICY IF EXISTS "Allow INSERT/UPDATE for service role" ON model_registry;
        CREATE POLICY "Allow INSERT/UPDATE for service role" 
            ON model_registry FOR ALL 
            USING (auth.role() = 'service_role');
        """,
        
        # User Operations (operações de usuários)
        """
        CREATE TABLE IF NOT EXISTS user_operations (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            user_id UUID NOT NULL,
            asset_id TEXT NOT NULL,
            asset_symbol TEXT NOT NULL,
            operation_type TEXT NOT NULL,
            direction TEXT NOT NULL,
            entry_price NUMERIC(18, 8),
            exit_price NUMERIC(18, 8),
            success BOOLEAN,
            profit_loss NUMERIC(18, 8),
            entry_date TIMESTAMPTZ,
            exit_date TIMESTAMPTZ,
            notes TEXT,
            signal_id UUID,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        );
        
        CREATE INDEX IF NOT EXISTS user_operations_user_id_idx ON user_operations (user_id);
        CREATE INDEX IF NOT EXISTS user_operations_asset_symbol_idx ON user_operations (asset_symbol);
        
        ALTER TABLE user_operations ENABLE ROW LEVEL SECURITY;
        DROP POLICY IF EXISTS "Allow access to own operations" ON user_operations;
        CREATE POLICY "Allow access to own operations" 
            ON user_operations FOR ALL 
            USING (auth.uid() = user_id OR auth.role() = 'service_role');
        """
    ]
    
    # Executar cada migração
    for i, migration in enumerate(migrations):
        try:
            logger.info(f"Executando migração {i+1}/{len(migrations)}")
            
            # Executar SQL
            await client.table("migrations").execute_sql(migration)
            
            logger.info(f"Migração {i+1} executada com sucesso")
        except Exception as e:
            logger.error(f"Erro ao executar migração {i+1}: {e}")
            # Continuar mesmo com erro
    
    logger.info("Migrações concluídas!")


if __name__ == "__main__":
    # Executar de forma assíncrona
    asyncio.run(run_migration()) 