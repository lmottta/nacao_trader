"""
Migration para criar a tabela de notificações.

Esta migração cria a tabela de notificações para armazenar alertas e mensagens para os usuários.
"""
import os
import asyncio
from loguru import logger

from src.utils.supabase_client import get_supabase_client


async def run_migration():
    """Executa a migração, criando a tabela de notificações."""
    logger.info("Executando migração: Criação da tabela de notificações")
    
    # Obter cliente do Supabase
    client = await get_supabase_client()
    
    # SQL para criar a tabela
    sql = """
    -- Tabela de notificações
    CREATE TABLE IF NOT EXISTS notifications (
        id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
        user_id TEXT NOT NULL,
        message TEXT NOT NULL,
        type TEXT NOT NULL,
        asset_id TEXT,
        asset_symbol TEXT,
        read BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMPTZ DEFAULT now(),
        
        CONSTRAINT fk_user FOREIGN KEY(user_id) REFERENCES auth.users(id) ON DELETE CASCADE
    );
    
    -- Índices para otimização
    CREATE INDEX IF NOT EXISTS notifications_user_id_idx ON notifications (user_id);
    CREATE INDEX IF NOT EXISTS notifications_asset_id_idx ON notifications (asset_id);
    CREATE INDEX IF NOT EXISTS notifications_read_idx ON notifications (read);
    CREATE INDEX IF NOT EXISTS notifications_created_at_idx ON notifications (created_at);
    
    -- Aplicar políticas de segurança para row level security
    ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
    
    -- Políticas para permitir leitura, modificação e exclusão apenas para o próprio usuário
    DROP POLICY IF EXISTS "Permitir leitura para o próprio usuário" ON notifications;
    CREATE POLICY "Permitir leitura para o próprio usuário"
      ON notifications FOR SELECT
      USING (auth.uid() = user_id);
    
    DROP POLICY IF EXISTS "Permitir modificação para o próprio usuário" ON notifications;
    CREATE POLICY "Permitir modificação para o próprio usuário"
      ON notifications FOR UPDATE
      USING (auth.uid() = user_id);
    
    DROP POLICY IF EXISTS "Permitir exclusão para o próprio usuário" ON notifications;
    CREATE POLICY "Permitir exclusão para o próprio usuário"
      ON notifications FOR DELETE
      USING (auth.uid() = user_id);
      
    -- Permitir inserção para o papel de serviço e para o próprio usuário
    DROP POLICY IF EXISTS "Permitir inserção para serviço e usuário" ON notifications;
    CREATE POLICY "Permitir inserção para serviço e usuário"
      ON notifications FOR INSERT
      WITH CHECK (auth.uid() = user_id OR auth.role() = 'service_role');
    """
    
    try:
        # Executar o SQL usando o cliente do Supabase
        response = await client.rpc('pgclassify', {'query': sql})
        
        # Verificar se a migração foi bem-sucedida
        if hasattr(response, 'error') and response.error:
            raise Exception(f"Erro na execução da migração: {response.error}")
        
        logger.info("Migração concluída com sucesso: Tabela de notificações criada")
        return True
    except Exception as e:
        logger.error(f"Erro ao executar migração: {str(e)}")
        return False


if __name__ == "__main__":
    # Executar a migração diretamente quando o script é chamado
    asyncio.run(run_migration()) 