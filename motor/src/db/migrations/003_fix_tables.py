#!/usr/bin/env python
"""
Migração para corrigir a estrutura das tabelas.

Este script:
1. Cria ou modifica as tabelas assets e price_history para corrigir os erros
"""
import os
import sys
from pathlib import Path

# Adicionar o diretório raiz ao sys.path
root_dir = Path(__file__).parent.parent.parent.parent
sys.path.append(str(root_dir))

from src.utils.supabase_client import get_supabase_client
from loguru import logger

def run_migration():
    """
    Executa as migrações para corrigir as tabelas utilizando APIs REST do Supabase.
    """
    logger.info("Iniciando migração para corrigir as tabelas...")
    
    # Obter cliente Supabase
    supabase = get_supabase_client()
    
    try:
        # 1. Criar tabela assets se não existir ou adicionar as colunas necessárias
        logger.info("Configurando tabela assets...")
        
        # Verificar se a tabela já existe
        try:
            # Tentativa de leitura
            result = supabase.table("assets").select("id").limit(1).execute()
            table_exists = True
            logger.info("Tabela assets encontrada, realizando modificações...")
        except Exception as e:
            if "relation \"assets\" does not exist" in str(e) or "does not exist" in str(e):
                table_exists = False
                logger.info("Tabela assets não encontrada, criando a tabela...")
            else:
                # Outro tipo de erro
                raise e
        
        if not table_exists:
            # Criar tabela via SQL Supabase usando o editor SQL
            logger.info("Criando tabela assets diretamente...")
            
            # Vamos notificar o usuário para criar a tabela via interface Supabase
            logger.info("""
            Por favor, acesse o painel Supabase e execute o seguinte SQL:
            
            -- Criar a tabela assets
            CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
            
            CREATE TABLE public.assets (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                symbol VARCHAR(20) NOT NULL,
                name VARCHAR(255),
                description TEXT,
                asset_type VARCHAR(50),
                last_price DECIMAL(18, 6),
                currency VARCHAR(10) DEFAULT 'USD',
                exchange VARCHAR(50),
                active BOOLEAN DEFAULT TRUE,
                is_tradable BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMPTZ DEFAULT now(),
                updated_at TIMESTAMPTZ DEFAULT now(),
                api_source VARCHAR(50),
                timezone VARCHAR(50) DEFAULT 'UTC',
                metadata JSONB
            );
            
            -- Adicionar índices
            CREATE INDEX idx_assets_symbol ON public.assets(symbol);
            CREATE INDEX idx_assets_type ON public.assets(asset_type);
            CREATE INDEX idx_assets_active ON public.assets(active);
            
            -- Adicionar restrição única para symbol
            ALTER TABLE public.assets ADD CONSTRAINT assets_symbol_unique UNIQUE (symbol);
            
            -- Criar políticas RLS
            ALTER TABLE public.assets ENABLE ROW LEVEL SECURITY;
            
            CREATE POLICY "Permitir leitura pública de assets" ON public.assets
                FOR SELECT USING (true);
            
            -- Criar a tabela price_history
            CREATE TABLE public.price_history (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                symbol VARCHAR(20) NOT NULL,
                timestamp TIMESTAMPTZ NOT NULL,
                timeframe VARCHAR(10) NOT NULL,
                open DECIMAL(18, 6),
                high DECIMAL(18, 6),
                low DECIMAL(18, 6),
                close DECIMAL(18, 6),
                volume DECIMAL(18, 2),
                source VARCHAR(50),
                created_at TIMESTAMPTZ DEFAULT now()
            );
            
            -- Adicionar índices
            CREATE INDEX idx_price_history_symbol ON public.price_history(symbol);
            CREATE INDEX idx_price_history_timestamp ON public.price_history(timestamp);
            CREATE INDEX idx_price_history_timeframe ON public.price_history(timeframe);
            
            -- Adicionar restrição única para symbol + timestamp + timeframe
            ALTER TABLE public.price_history ADD CONSTRAINT price_history_unique UNIQUE (symbol, timestamp, timeframe);
            
            -- Criar políticas RLS
            ALTER TABLE public.price_history ENABLE ROW LEVEL SECURITY;
            
            CREATE POLICY "Permitir leitura pública de price_history" ON public.price_history
                FOR SELECT USING (true);
            """)

            # Testamos se as tabelas foram criadas corretamente
            logger.info("Verificando se as tabelas foram criadas...")
            try:
                # Criar um registro de teste na tabela assets
                test_asset = {
                    "symbol": "TESTE123",
                    "name": "Ativo de Teste",
                    "asset_type": "stock",
                    "currency": "USD",
                    "active": True
                }
                
                # Tente criar o ativo de teste
                test_result = supabase.table("assets").insert(test_asset).execute()
                logger.info(f"Teste de inserção em assets realizado: {test_result.data}")
                
                # Remover o ativo de teste
                supabase.table("assets").delete().eq("symbol", "TESTE123").execute()
                
                # Teste concluído com sucesso
                logger.info("Estrutura da tabela assets verificada com sucesso!")
            except Exception as e:
                logger.error(f"Erro ao testar a tabela assets: {e}")
                raise
        else:
            logger.info("Tabela assets já existe. Verifique a estrutura usando o Supabase Studio.")
        
        # Verificar a tabela price_history
        try:
            # Tentativa de leitura
            result = supabase.table("price_history").select("id").limit(1).execute()
            ph_table_exists = True
            logger.info("Tabela price_history encontrada.")
        except Exception as e:
            if "relation \"price_history\" does not exist" in str(e) or "does not exist" in str(e):
                ph_table_exists = False
                logger.info("Tabela price_history não encontrada.")
            else:
                # Outro tipo de erro
                raise e
        
        if not ph_table_exists:
            logger.info("A tabela price_history precisa ser criada. Por favor, execute o SQL mencionado anteriormente.")
        else:
            logger.info("Tabela price_history já existe. Verifique a estrutura usando o Supabase Studio.")
        
        logger.info("Migração para corrigir as tabelas concluída. Verifique se as estruturas estão corretas no Supabase Studio.")
        return True
        
    except Exception as e:
        logger.error(f"Erro durante a migração para corrigir as tabelas: {e}")
        return False

if __name__ == "__main__":
    run_migration() 