"""
Migration para criar a tabela de resultados de operações.

Esta migração cria a tabela operation_results para rastrear os resultados das operações sugeridas
e compará-los com os resultados reais do mercado.
"""
import os
import asyncio
from loguru import logger

from src.utils.supabase_client import get_supabase_client


async def run_migration():
    """Executa a migração, criando a tabela de resultados de operações."""
    logger.info("Executando migração: Criação da tabela de resultados de operações")
    
    # Obter cliente do Supabase
    client = await get_supabase_client()
    
    # SQL para criar a tabela
    sql = """
    -- Tabela de resultados de operações
    CREATE TABLE IF NOT EXISTS operation_results (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        user_id TEXT NOT NULL,
        asset_id TEXT NOT NULL,
        asset_symbol TEXT NOT NULL,
        asset_name TEXT,
        direction TEXT NOT NULL CHECK (direction IN ('CALL', 'PUT')),
        signal_id UUID,
        recommended_price DECIMAL(15, 5),
        entry_time TIMESTAMPTZ NOT NULL DEFAULT now(),
        target_price DECIMAL(15, 5),
        stop_loss DECIMAL(15, 5),
        confidence INTEGER NOT NULL CHECK (confidence BETWEEN 0 AND 100),
        result TEXT CHECK (result IN ('win', 'loss', 'pending')),
        actual_price DECIMAL(15, 5),
        price_difference DECIMAL(15, 5),
        profit_loss DECIMAL(15, 5),
        notes TEXT,
        created_at TIMESTAMPTZ DEFAULT now(),
        updated_at TIMESTAMPTZ DEFAULT now(),
        
        CONSTRAINT fk_user FOREIGN KEY(user_id) REFERENCES auth.users(id) ON DELETE CASCADE,
        CONSTRAINT fk_asset FOREIGN KEY(asset_id) REFERENCES assets(id) ON DELETE CASCADE,
        CONSTRAINT fk_signal FOREIGN KEY(signal_id) REFERENCES signals(id) ON DELETE SET NULL
    );
    
    -- Função de trigger para atualizar o timestamp 'updated_at'
    CREATE OR REPLACE FUNCTION update_timestamp()
    RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = now();
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    
    -- Trigger para atualizar 'updated_at' ao modificar um registro
    DROP TRIGGER IF EXISTS set_updated_at ON operation_results;
    CREATE TRIGGER set_updated_at
    BEFORE UPDATE ON operation_results
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();
    
    -- Índices para otimização
    CREATE INDEX IF NOT EXISTS operation_results_user_id_idx ON operation_results (user_id);
    CREATE INDEX IF NOT EXISTS operation_results_asset_id_idx ON operation_results (asset_id);
    CREATE INDEX IF NOT EXISTS operation_results_asset_symbol_idx ON operation_results (asset_symbol);
    CREATE INDEX IF NOT EXISTS operation_results_direction_idx ON operation_results (direction);
    CREATE INDEX IF NOT EXISTS operation_results_result_idx ON operation_results (result);
    CREATE INDEX IF NOT EXISTS operation_results_entry_time_idx ON operation_results (entry_time);
    CREATE INDEX IF NOT EXISTS operation_results_confidence_idx ON operation_results (confidence);
    
    -- Aplicar políticas de segurança para row level security
    ALTER TABLE operation_results ENABLE ROW LEVEL SECURITY;
    
    -- Políticas para permitir leitura, modificação e exclusão apenas para o próprio usuário
    DROP POLICY IF EXISTS "Permitir leitura para o próprio usuário" ON operation_results;
    CREATE POLICY "Permitir leitura para o próprio usuário"
      ON operation_results FOR SELECT
      USING (auth.uid() = user_id);
    
    DROP POLICY IF EXISTS "Permitir modificação para o próprio usuário" ON operation_results;
    CREATE POLICY "Permitir modificação para o próprio usuário"
      ON operation_results FOR UPDATE
      USING (auth.uid() = user_id);
    
    DROP POLICY IF EXISTS "Permitir exclusão para o próprio usuário" ON operation_results;
    CREATE POLICY "Permitir exclusão para o próprio usuário"
      ON operation_results FOR DELETE
      USING (auth.uid() = user_id);
      
    -- Permitir inserção para o papel de serviço e para o próprio usuário
    DROP POLICY IF EXISTS "Permitir inserção para serviço e usuário" ON operation_results;
    CREATE POLICY "Permitir inserção para serviço e usuário"
      ON operation_results FOR INSERT
      WITH CHECK (auth.uid() = user_id OR auth.role() = 'service_role');
    """
    
    try:
        # Executar o SQL usando o cliente do Supabase
        response = await client.rpc('pgclassify', {'query': sql})
        
        # Verificar se a migração foi bem-sucedida
        if hasattr(response, 'error') and response.error:
            raise Exception(f"Erro na execução da migração: {response.error}")
        
        logger.info("Migração concluída com sucesso: Tabela de resultados de operações criada")
        return True
    except Exception as e:
        logger.error(f"Erro ao executar migração: {str(e)}")
        return False


if __name__ == "__main__":
    # Executar a migração diretamente quando o script é chamado
    asyncio.run(run_migration()) 