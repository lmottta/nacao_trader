#!/usr/bin/env python
"""
Script para criar a tabela de dados em tempo real no Supabase.

Este script configura a tabela 'realtime_market_data' no Supabase para
armazenar e gerenciar dados de mercado em tempo real obtidos via API do Yahoo Finance.
"""
import asyncio
import os
import sys
from pathlib import Path

# Adicionar diretório raiz ao PYTHONPATH para importação relativa
ROOT_DIR = Path(__file__).parent
sys.path.append(str(ROOT_DIR))

try:
    from src.utils.supabase_client import get_supabase_client, refresh_supabase_connection
    from src.utils.config import settings
    from src.utils.logger import setup_logger
except ImportError as e:
    print(f"Erro ao importar módulos: {e}")
    print("Verifique se está executando o script do diretório correto.")
    sys.exit(1)

# Configurar logger
logger = setup_logger("create_realtime_table.log")

async def create_realtime_table():
    """
    Cria e configura a tabela 'realtime_market_data' no Supabase
    para armazenamento de dados de mercado em tempo real.
    """
    try:
        logger.info("Iniciando criação da tabela realtime_market_data")
        
        # Obter cliente Supabase
        supabase = get_supabase_client()
        
        # SQL para criar a tabela realtime_market_data se não existir
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS realtime_market_data (
            id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
            symbol TEXT NOT NULL,
            timestamp TIMESTAMPTZ NOT NULL,
            price NUMERIC,
            open NUMERIC,
            high NUMERIC,
            low NUMERIC,
            volume NUMERIC,
            market_cap NUMERIC,
            pe_ratio NUMERIC,
            change_percent NUMERIC,
            source TEXT DEFAULT 'yahoo_finance',
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        );
        
        -- Criar índices para consultas eficientes
        CREATE INDEX IF NOT EXISTS idx_realtime_market_data_symbol ON realtime_market_data (symbol);
        CREATE INDEX IF NOT EXISTS idx_realtime_market_data_timestamp ON realtime_market_data (timestamp);
        CREATE INDEX IF NOT EXISTS idx_realtime_market_data_source ON realtime_market_data (source);
        
        -- Adicionar restrição unique para evitar duplicidade
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'realtime_market_data_symbol_timestamp_key'
            ) THEN
                ALTER TABLE realtime_market_data ADD CONSTRAINT realtime_market_data_symbol_timestamp_key 
                UNIQUE (symbol, timestamp);
            END IF;
        END
        $$;
        
        -- Configurar trigger para updated_at
        CREATE OR REPLACE FUNCTION update_timestamp_column()
        RETURNS TRIGGER AS $$
        BEGIN
           NEW.updated_at = NOW();
           RETURN NEW;
        END;
        $$ language 'plpgsql';
        
        DROP TRIGGER IF EXISTS update_realtime_market_data_timestamp ON realtime_market_data;
        CREATE TRIGGER update_realtime_market_data_timestamp
        BEFORE UPDATE ON realtime_market_data
        FOR EACH ROW EXECUTE PROCEDURE update_timestamp_column();
        
        -- Configurar políticas RLS
        ALTER TABLE realtime_market_data ENABLE ROW LEVEL SECURITY;
        
        -- Políticas para permitir o acesso adequado
        DROP POLICY IF EXISTS "Dados públicos para leitura" ON realtime_market_data;
        CREATE POLICY "Dados públicos para leitura" 
            ON realtime_market_data FOR SELECT 
            USING (true);
        
        DROP POLICY IF EXISTS "Apenas serviço pode inserir ou atualizar" ON realtime_market_data;
        CREATE POLICY "Apenas serviço pode inserir ou atualizar" 
            ON realtime_market_data FOR INSERT 
            TO service_role 
            USING (true);
            
        DROP POLICY IF EXISTS "Apenas serviço pode atualizar" ON realtime_market_data;
        CREATE POLICY "Apenas serviço pode atualizar" 
            ON realtime_market_data FOR UPDATE 
            TO service_role 
            USING (true);
        """
        
        # Executar SQL como usuário autenticado (service_role)
        refresh_supabase_connection()
        result = supabase.rpc('exec_sql', {'sql': create_table_sql}).execute()
        
        logger.info("Tabela realtime_market_data criada/atualizada com sucesso")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao criar tabela realtime_market_data: {e}")
        return False

async def create_assets_columns():
    """
    Adiciona ou atualiza a tabela assets para suportar dados em tempo real.
    """
    try:
        logger.info("Atualizando tabela assets para suportar dados em tempo real")
        
        # Obter cliente Supabase
        supabase = get_supabase_client()
        
        # SQL para atualizar a tabela assets
        alter_assets_sql = """
        -- Adicionar colunas para preço em tempo real e última atualização
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name = 'assets' AND column_name = 'last_price') THEN
                ALTER TABLE assets ADD COLUMN last_price NUMERIC;
            END IF;
            
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name = 'assets' AND column_name = 'last_update') THEN
                ALTER TABLE assets ADD COLUMN last_update TIMESTAMPTZ;
            END IF;
            
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name = 'assets' AND column_name = 'daily_change') THEN
                ALTER TABLE assets ADD COLUMN daily_change NUMERIC;
            END IF;
            
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name = 'assets' AND column_name = 'daily_change_percent') THEN
                ALTER TABLE assets ADD COLUMN daily_change_percent NUMERIC;
            END IF;
            
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name = 'assets' AND column_name = 'active') THEN
                ALTER TABLE assets ADD COLUMN active BOOLEAN DEFAULT TRUE;
            END IF;
            
            -- Verificar e adicionar coluna de descrição
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name = 'assets' AND column_name = 'description') THEN
                ALTER TABLE assets ADD COLUMN description TEXT;
            END IF;
        END
        $$;
        """
        
        # Executar SQL como usuário autenticado (service_role)
        refresh_supabase_connection()
        result = supabase.rpc('exec_sql', {'sql': alter_assets_sql}).execute()
        
        logger.info("Tabela assets atualizada com sucesso")
        return True
        
    except Exception as e:
        logger.error(f"Erro ao atualizar tabela assets: {e}")
        return False

async def main():
    """
    Função principal para executar as tarefas de configuração.
    """
    print("=" * 80)
    print("Configurando tabela de dados em tempo real - Nação Trader")
    print("=" * 80)
    
    try:
        # Criar/atualizar tabela realtime_market_data
        success_realtime = await create_realtime_table()
        
        # Atualizar tabela assets
        success_assets = await create_assets_columns()
        
        if success_realtime and success_assets:
            print("✅ Configuração concluída com sucesso!")
            return 0
        else:
            print("❌ Houve erros durante a configuração. Verifique os logs.")
            return 1
            
    except Exception as e:
        print(f"❌ Erro durante a configuração: {e}")
        logger.error(f"Erro durante a configuração: {e}")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nProcesso interrompido pelo usuário.")
        sys.exit(0)
    except Exception as e:
        print(f"\nERRO FATAL: {e}")
        sys.exit(1) 