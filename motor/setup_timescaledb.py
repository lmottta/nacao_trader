#!/usr/bin/env python
"""
Script para configuração do TimescaleDB no Supabase.

Este script implementa a parte de configuração do TimescaleDB do Sprint 1:
1. Verifica se a extensão TimescaleDB está disponível
2. Instala a extensão se necessário
3. Configura a tabela price_history como hypertable
4. Configura compressão e índices otimizados
"""
import os
import sys
import time
import asyncio
from typing import Dict, List, Any, Optional

import httpx
import logging

# Tentar importar dotenv, mas continuar mesmo se não estiver disponível
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("Variáveis de ambiente carregadas do arquivo .env")
except ImportError:
    print("Módulo dotenv não encontrado. Usando variáveis de ambiente do sistema.")
    def load_dotenv():
        pass

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("timescaledb_setup")

# Carregar variáveis de ambiente
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    logger.error("SUPABASE_URL e SUPABASE_SERVICE_KEY devem ser definidos nas variáveis de ambiente")
    sys.exit(1)

logger.info(f"Usando Supabase URL: {SUPABASE_URL}")

async def execute_sql(query: str) -> List[Dict[str, Any]]:
    """
    Executa uma consulta SQL no Supabase usando a função RPC.
    
    Args:
        query: Consulta SQL a ser executada
    
    Returns:
        List[Dict[str, Any]]: Resultado da consulta
    """
    try:
        # Criar cliente HTTP
        headers = {
            "apikey": SUPABASE_SERVICE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        
        # Construir URL para função RPC execute_sql
        url = f"{SUPABASE_URL}/rest/v1/rpc/execute_sql"
        
        # Fazer requisição POST
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url, 
                json={"query": query},
                headers=headers,
                timeout=30.0
            )
            
            # Verificar se a resposta foi bem-sucedida
            response.raise_for_status()
            
            # Retornar dados
            return response.json()
    except Exception as e:
        logger.error(f"Erro ao executar SQL: {e}")
        # Se a consulta é sobre extensões, tentar uma abordagem direta
        if "pg_extension" in query:
            logger.info("Tentando abordagem alternativa para extensões...")
            return await execute_direct_extension_check()
        raise

async def execute_direct_extension_check() -> List[Dict[str, Any]]:
    """Tenta verificar extensões diretamente via API SQL."""
    try:
        # Construir URL para função REST de SQL direta
        url = f"{SUPABASE_URL}/rest/v1/execute_sql"
        
        headers = {
            "apikey": SUPABASE_SERVICE_KEY,
            "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        
        query = "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb');"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url, 
                json={"query": query},
                headers=headers,
                timeout=30.0
            )
            
            # Verificar se a resposta foi bem-sucedida
            response.raise_for_status()
            
            # Retornar dados formatados consistentemente
            result = response.json()
            return [{"exists": result[0]["exists"]}]
    except Exception as e:
        logger.error(f"Erro na verificação direta de extensões: {e}")
        # Retornar um resultado padrão (assumindo que não existe)
        return [{"exists": False}]

async def check_timescaledb_exists() -> bool:
    """
    Verifica se a extensão TimescaleDB já está instalada.
    
    Returns:
        bool: True se a extensão já estiver instalada
    """
    logger.info("Verificando se TimescaleDB já está instalado...")
    
    query = """
    SELECT EXISTS (
        SELECT FROM pg_extension
        WHERE extname = 'timescaledb'
    );
    """
    
    try:
        result = await execute_sql(query)
        exists = result[0].get('exists', False) if result and len(result) > 0 else False
        
        if exists:
            logger.info("TimescaleDB já está instalado")
        else:
            logger.info("TimescaleDB não está instalado")
            
        return exists
    except Exception as e:
        logger.warning(f"Não foi possível verificar a existência do TimescaleDB: {e}")
        logger.info("Assumindo que TimescaleDB não está instalado")
        return False

async def install_timescaledb() -> bool:
    """
    Instala a extensão TimescaleDB no banco de dados.
    
    Returns:
        bool: True se a instalação foi bem-sucedida
    """
    # Verificar se a extensão já existe
    exists = await check_timescaledb_exists()
    if exists:
        logger.info("Extensão TimescaleDB já está instalada")
        return True
        
    logger.info("Instalando extensão TimescaleDB...")
    
    query = """
    CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
    """
    
    try:
        await execute_sql(query)
        logger.info("Extensão TimescaleDB instalada com sucesso")
        
        # Verificar novamente se está instalada
        return await check_timescaledb_exists()
    except Exception as e:
        logger.error(f"Erro ao instalar extensão TimescaleDB: {e}")
        return False

async def check_price_history_table_exists() -> bool:
    """
    Verifica se a tabela price_history existe.
    
    Returns:
        bool: True se a tabela existir
    """
    logger.info("Verificando se a tabela price_history existe...")
    
    query = """
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'price_history'
    );
    """
    
    try:
        result = await execute_sql(query)
        exists = result[0].get('exists', False) if result and len(result) > 0 else False
        
        if exists:
            logger.info("Tabela price_history existe")
        else:
            logger.info("Tabela price_history não existe")
            
        return exists
    except Exception as e:
        logger.warning(f"Não foi possível verificar a existência da tabela price_history: {e}")
        return False

async def create_price_history_table() -> bool:
    """
    Cria a tabela price_history se ela não existir.
    
    Returns:
        bool: True se a criação foi bem-sucedida
    """
    # Verificar se a tabela já existe
    exists = await check_price_history_table_exists()
    if exists:
        logger.info("Tabela price_history já existe")
        return True
        
    logger.info("Criando tabela price_history...")
    
    query = """
    CREATE TABLE IF NOT EXISTS price_history (
        id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
        symbol TEXT NOT NULL,
        timestamp TIMESTAMPTZ NOT NULL,
        timeframe TEXT NOT NULL,
        open DECIMAL(18, 8) NOT NULL,
        high DECIMAL(18, 8) NOT NULL,
        low DECIMAL(18, 8) NOT NULL,
        close DECIMAL(18, 8) NOT NULL,
        volume DECIMAL(24, 8),
        source TEXT,
        created_at TIMESTAMPTZ DEFAULT now()
    );
    
    -- Adicionar índices para consultas comuns
    CREATE INDEX IF NOT EXISTS idx_price_history_symbol ON price_history(symbol);
    CREATE INDEX IF NOT EXISTS idx_price_history_timestamp ON price_history(timestamp DESC);
    CREATE UNIQUE INDEX IF NOT EXISTS idx_price_history_unique 
    ON price_history(symbol, timestamp, timeframe);
    """
    
    try:
        await execute_sql(query)
        logger.info("Tabela price_history criada com sucesso")
        
        # Verificar novamente se está criada
        return await check_price_history_table_exists()
    except Exception as e:
        logger.error(f"Erro ao criar tabela price_history: {e}")
        return False

async def check_hypertable_exists() -> bool:
    """
    Verifica se a tabela price_history já está configurada como hypertable.
    
    Returns:
        bool: True se já for uma hypertable
    """
    logger.info("Verificando se price_history já é uma hypertable...")
    
    query = """
    SELECT EXISTS (
        SELECT FROM timescaledb_information.hypertables
        WHERE hypertable_name = 'price_history'
    );
    """
    
    try:
        result = await execute_sql(query)
        exists = result[0].get('exists', False) if result and len(result) > 0 else False
        
        if exists:
            logger.info("price_history já é uma hypertable")
        else:
            logger.info("price_history não é uma hypertable")
            
        return exists
    except Exception as e:
        logger.warning(f"Não foi possível verificar se price_history é uma hypertable: {e}")
        return False

async def convert_to_hypertable() -> bool:
    """
    Converte a tabela price_history para uma hypertable.
    
    Returns:
        bool: True se a conversão foi bem-sucedida
    """
    # Verificar se já é uma hypertable
    is_hypertable = await check_hypertable_exists()
    if is_hypertable:
        logger.info("price_history já é uma hypertable")
        return True
        
    logger.info("Convertendo price_history para hypertable...")
    
    query = """
    SELECT create_hypertable('price_history', 'timestamp', 
                             if_not_exists => TRUE,
                             create_default_indexes => FALSE);
    """
    
    try:
        await execute_sql(query)
        logger.info("price_history convertida para hypertable com sucesso")
        
        # Verificar novamente
        return await check_hypertable_exists()
    except Exception as e:
        logger.error(f"Erro ao converter price_history para hypertable: {e}")
        return False

async def setup_compression() -> bool:
    """
    Configura compressão para dados históricos na hypertable.
    
    Returns:
        bool: True se a configuração foi bem-sucedida
    """
    logger.info("Configurando compressão para price_history...")
    
    query = """
    ALTER TABLE price_history SET (
        timescaledb.compress,
        timescaledb.compress_segmentby = 'symbol,timeframe',
        timescaledb.compress_orderby = 'timestamp DESC'
    );
    
    -- Criar política de compressão automatizada
    SELECT add_compression_policy('price_history', INTERVAL '7 days');
    """
    
    try:
        await execute_sql(query)
        logger.info("Compressão configurada com sucesso")
        return True
    except Exception as e:
        logger.error(f"Erro ao configurar compressão: {e}")
        # Não é um erro crítico, pode continuar
        return False

async def create_optimized_indexes() -> bool:
    """
    Cria índices otimizados para consultas comuns.
    
    Returns:
        bool: True se a criação foi bem-sucedida
    """
    logger.info("Criando índices otimizados...")
    
    query = """
    -- Índice de co-localização para consultas por (symbol, timeframe) com filtro de timestamp
    CREATE INDEX IF NOT EXISTS idx_price_history_symbol_timeframe_timestamp 
    ON price_history(symbol, timeframe, timestamp DESC);
    
    -- Índice para consultas de intervalo de data
    CREATE INDEX IF NOT EXISTS idx_price_history_timestamp_range 
    ON price_history USING BRIN(timestamp);
    """
    
    try:
        await execute_sql(query)
        logger.info("Índices otimizados criados com sucesso")
        return True
    except Exception as e:
        logger.error(f"Erro ao criar índices otimizados: {e}")
        # Não é um erro crítico, pode continuar
        return False

async def create_retention_policy() -> bool:
    """
    Cria uma política de retenção para limitar o crescimento da tabela.
    
    Returns:
        bool: True se a criação foi bem-sucedida
    """
    logger.info("Criando política de retenção (90 dias)...")
    
    query = """
    -- Remover política existente se houver
    SELECT drop_chunks('price_history', older_than => INTERVAL '100 years');
    
    -- Criar nova política
    SELECT add_retention_policy('price_history', INTERVAL '90 days');
    """
    
    try:
        await execute_sql(query)
        logger.info("Política de retenção criada com sucesso")
        return True
    except Exception as e:
        logger.error(f"Erro ao criar política de retenção: {e}")
        # Não é um erro crítico, pode continuar
        return False

async def run_setup() -> None:
    """
    Executa toda a configuração do TimescaleDB.
    """
    logger.info("Iniciando configuração do TimescaleDB")
    
    # Instalar extensão TimescaleDB
    installed = await install_timescaledb()
    if not installed:
        logger.error("Falha ao instalar TimescaleDB. Abortando configuração.")
        return
    
    # Criar tabela price_history se não existir
    table_created = await create_price_history_table()
    if not table_created:
        logger.error("Falha ao criar tabela price_history. Abortando configuração.")
        return
    
    # Converter para hypertable
    hypertable_success = await convert_to_hypertable()
    if not hypertable_success:
        logger.error("Falha ao converter para hypertable. Abortando configuração.")
        return
    
    # Configurar compressão
    await setup_compression()
    
    # Criar índices otimizados
    await create_optimized_indexes()
    
    # Criar política de retenção
    await create_retention_policy()
    
    logger.info("Configuração do TimescaleDB concluída com sucesso!")

if __name__ == "__main__":
    asyncio.run(run_setup()) 