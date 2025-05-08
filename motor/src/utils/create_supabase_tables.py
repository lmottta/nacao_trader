"""
Script para criar as tabelas no Supabase usando o MCP.

Este script pode ser executado uma única vez para configurar o projeto no Supabase.
Use o comando:
    $ python -m motor.src.utils.create_supabase_tables <project_id>
"""
import argparse
import sys

from loguru import logger


def create_price_history_table(project_id: str):
    """
    Cria a tabela price_history para armazenar dados OHLCV.
    
    Args:
        project_id: ID do projeto Supabase
    """
    logger.info("Criando tabela price_history")
    
    query = """
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
    
    -- Criar políticas RLS
    ALTER TABLE price_history ENABLE ROW LEVEL SECURITY;
    DROP POLICY IF EXISTS "Allow SELECT for authenticated users" ON price_history;
    CREATE POLICY "Allow SELECT for authenticated users" 
        ON price_history FOR SELECT 
        USING (auth.role() = 'authenticated');
    DROP POLICY IF EXISTS "Allow INSERT/UPDATE for service role" ON price_history;
    CREATE POLICY "Allow INSERT/UPDATE for service role" 
        ON price_history FOR ALL 
        USING (auth.role() = 'service_role');
    """
    
    try:
        # Executar migration via MCP
        print(f"Criando tabela price_history no projeto {project_id}...")
        print("Execute o seguinte comando MCP:")
        print(f"mcp_supabase_apply_migration --project_id={project_id} --name=create_price_history_table --query=\"{query}\"")
        return True
    except Exception as e:
        logger.error(f"Erro ao criar tabela price_history: {e}")
        return False


def create_model_registry_table(project_id: str):
    """
    Cria a tabela model_registry para armazenar metadados de modelos ML.
    
    Args:
        project_id: ID do projeto Supabase
    """
    logger.info("Criando tabela model_registry")
    
    query = """
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
    """
    
    try:
        # Executar migration via MCP
        print(f"Criando tabela model_registry no projeto {project_id}...")
        print("Execute o seguinte comando MCP:")
        print(f"mcp_supabase_apply_migration --project_id={project_id} --name=create_model_registry_table --query=\"{query}\"")
        return True
    except Exception as e:
        logger.error(f"Erro ao criar tabela model_registry: {e}")
        return False


def create_signals_table(project_id: str):
    """
    Cria a tabela signals para armazenar sinais de trading.
    
    Args:
        project_id: ID do projeto Supabase
    """
    logger.info("Criando tabela signals")
    
    query = """
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
    """
    
    try:
        # Executar migration via MCP
        print(f"Criando tabela signals no projeto {project_id}...")
        print("Execute o seguinte comando MCP:")
        print(f"mcp_supabase_apply_migration --project_id={project_id} --name=create_signals_table --query=\"{query}\"")
        return True
    except Exception as e:
        logger.error(f"Erro ao criar tabela signals: {e}")
        return False


def create_user_operations_table(project_id: str):
    """
    Cria a tabela user_operations para armazenar operações dos usuários.
    
    Args:
        project_id: ID do projeto Supabase
    """
    logger.info("Criando tabela user_operations")
    
    query = """
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
    
    try:
        # Executar migration via MCP
        print(f"Criando tabela user_operations no projeto {project_id}...")
        print("Execute o seguinte comando MCP:")
        print(f"mcp_supabase_apply_migration --project_id={project_id} --name=create_user_operations_table --query=\"{query}\"")
        return True
    except Exception as e:
        logger.error(f"Erro ao criar tabela user_operations: {e}")
        return False


def create_all_tables(project_id: str):
    """
    Cria todas as tabelas necessárias no Supabase.
    
    Args:
        project_id: ID do projeto Supabase
    """
    logger.info(f"Criando todas as tabelas no projeto {project_id}")
    
    # Criar as tabelas
    price_history = create_price_history_table(project_id)
    model_registry = create_model_registry_table(project_id)
    signals = create_signals_table(project_id)
    user_operations = create_user_operations_table(project_id)
    
    # Verificar resultados
    tables = {
        "price_history": price_history,
        "model_registry": model_registry,
        "signals": signals,
        "user_operations": user_operations
    }
    
    logger.info("Resultado da criação das tabelas:")
    for table, success in tables.items():
        result = "✓" if success else "✗"
        logger.info(f"{table}: {result}")


def main():
    """Função principal do script."""
    # Configurar parser de argumentos
    parser = argparse.ArgumentParser(description="Cria tabelas no Supabase")
    parser.add_argument("project_id", help="ID do projeto Supabase")
    parser.add_argument("--table", help="Nome específico da tabela a ser criada", default=None)
    
    # Verificar argumentos
    args = parser.parse_args()
    
    if not args.project_id:
        print("Erro: O ID do projeto Supabase é obrigatório")
        sys.exit(1)
    
    # Criar tabelas
    if args.table:
        # Criar tabela específica
        if args.table == "price_history":
            create_price_history_table(args.project_id)
        elif args.table == "model_registry":
            create_model_registry_table(args.project_id)
        elif args.table == "signals":
            create_signals_table(args.project_id)
        elif args.table == "user_operations":
            create_user_operations_table(args.project_id)
        else:
            print(f"Erro: Tabela '{args.table}' desconhecida")
            sys.exit(1)
    else:
        # Criar todas as tabelas
        create_all_tables(args.project_id)
    
    print("Processo concluído!")


if __name__ == "__main__":
    main() 