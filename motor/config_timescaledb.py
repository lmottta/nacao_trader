import os
import sys
import asyncio
import httpx
import json

SUPABASE_URL = "https://prcnldxsrpkhusanwffr.supabase.co"
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InByY25sZHhzcnBraHVzYW53ZmZyIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NjE2MDg4MSwiZXhwIjoyMDYxNzM2ODgxfQ.qpto7gfuaZ0zGyxpEenfDlVC7Y3GtLWYkxdQa7wi_BA"

print(f"Usando Supabase URL: {SUPABASE_URL}")

async def execute_sql(query):
    """Executa uma consulta SQL via API REST do Supabase."""
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}", 
        "Content-Type": "application/json"
    }
    
    # Usar API SQL direta (disponível em todos os projetos Supabase)
    url = f"{SUPABASE_URL}/rest/v1/rpc/execute_sql"
    data = {"query": query}
    
    print(f"Executando SQL: {query[:100]}...")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=data, headers=headers)
            response.raise_for_status()
            result = response.json()
            return result
    except Exception as e:
        print(f"Erro ao executar SQL: {str(e)}")
        return None

async def check_timescaledb_exists():
    """Verifica se a extensão TimescaleDB já está instalada."""
    query = "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb');"
    
    try:
        result = await execute_sql(query)
        if result and len(result) > 0:
            exists = result[0].get('exists', False)
            if exists:
                print("TimescaleDB já está instalado!")
            else:
                print("TimescaleDB não está instalado.")
            return exists
    except Exception as e:
        print(f"Erro ao verificar TimescaleDB: {str(e)}")
    return False

async def install_timescaledb():
    """Instala a extensão TimescaleDB."""
    print("Instalando TimescaleDB...")
    
    # Verificar se já existe
    exists = await check_timescaledb_exists()
    if exists:
        print("TimescaleDB já está instalado. Pulando instalação.")
        return True
        
    # Instalar a extensão
    query = "CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;"
    
    try:
        await execute_sql(query)
        print("Extensão TimescaleDB instalada com sucesso!")
        
        # Verificar se foi instalada
        return await check_timescaledb_exists()
    except Exception as e:
        print(f"Erro ao instalar TimescaleDB: {str(e)}")
        return False

async def check_price_history_exists():
    """Verifica se a tabela price_history existe."""
    query = """
    SELECT EXISTS (
      SELECT FROM information_schema.tables 
      WHERE table_schema = 'public' 
      AND table_name = 'price_history'
    );
    """
    
    try:
        result = await execute_sql(query)
        if result and len(result) > 0:
            exists = result[0].get('exists', False)
            if exists:
                print("Tabela price_history existe!")
            else:
                print("Tabela price_history não existe.")
            return exists
    except Exception as e:
        print(f"Erro ao verificar tabela price_history: {str(e)}")
    return False

async def create_price_history():
    """Cria a tabela price_history se não existir."""
    print("Verificando/criando tabela price_history...")
    
    # Verificar se já existe
    exists = await check_price_history_exists()
    if exists:
        print("Tabela price_history já existe. Pulando criação.")
        return True
        
    # Criar a tabela
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
    
    -- Índices básicos
    CREATE INDEX IF NOT EXISTS idx_price_history_symbol ON price_history(symbol);
    CREATE INDEX IF NOT EXISTS idx_price_history_timestamp ON price_history(timestamp DESC);
    CREATE UNIQUE INDEX IF NOT EXISTS idx_price_history_unique ON price_history(symbol, timestamp, timeframe);
    """
    
    try:
        await execute_sql(query)
        print("Tabela price_history criada com sucesso!")
        return True
    except Exception as e:
        print(f"Erro ao criar tabela price_history: {str(e)}")
        return False

async def check_hypertable_exists():
    """Verifica se price_history já é uma hypertable."""
    query = """
    SELECT EXISTS (
      SELECT FROM timescaledb_information.hypertables
      WHERE hypertable_name = 'price_history'
    );
    """
    
    try:
        result = await execute_sql(query)
        if result and len(result) > 0:
            exists = result[0].get('exists', False)
            if exists:
                print("price_history já é uma hypertable!")
            else:
                print("price_history não é uma hypertable.")
            return exists
    except Exception as e:
        print(f"Erro ao verificar hypertable: {str(e)}")
    return False

async def convert_to_hypertable():
    """Converte price_history para hypertable."""
    print("Convertendo price_history para hypertable...")
    
    # Verificar se já é uma hypertable
    is_hypertable = await check_hypertable_exists()
    if is_hypertable:
        print("price_history já é uma hypertable. Pulando conversão.")
        return True
        
    # Converter para hypertable
    query = """
    SELECT create_hypertable('price_history', 'timestamp', 
                             if_not_exists => TRUE,
                             create_default_indexes => FALSE);
    """
    
    try:
        await execute_sql(query)
        print("price_history convertida para hypertable com sucesso!")
        return True
    except Exception as e:
        print(f"Erro ao converter para hypertable: {str(e)}")
        return False

async def setup_compression():
    """Configura compressão para dados históricos."""
    print("Configurando compressão de dados...")
    
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
        print("Compressão configurada com sucesso!")
        return True
    except Exception as e:
        print(f"Erro ao configurar compressão: {str(e)}")
        # Não é crítico, pode continuar
        return False

async def create_optimized_indexes():
    """Cria índices otimizados para consultas."""
    print("Criando índices otimizados...")
    
    query = """
    -- Índice de co-localização
    CREATE INDEX IF NOT EXISTS idx_price_history_symbol_timeframe_timestamp 
    ON price_history(symbol, timeframe, timestamp DESC);
    
    -- Índice para intervalo de datas
    CREATE INDEX IF NOT EXISTS idx_price_history_timestamp_range 
    ON price_history USING BRIN(timestamp);
    """
    
    try:
        await execute_sql(query)
        print("Índices otimizados criados com sucesso!")
        return True
    except Exception as e:
        print(f"Erro ao criar índices otimizados: {str(e)}")
        # Não é crítico, pode continuar
        return False

async def main():
    """Função principal de configuração."""
    print("--- Configuração de TimescaleDB para Nação Trader ---")
    
    # Passo 1: Instalar TimescaleDB
    installed = await install_timescaledb()
    if not installed:
        print("ERRO: Falha ao instalar TimescaleDB. Abortando.")
        return
    
    # Passo 2: Criar tabela price_history
    table_created = await create_price_history()
    if not table_created:
        print("ERRO: Falha ao criar tabela price_history. Abortando.")
        return
    
    # Passo 3: Converter para hypertable
    hypertable_success = await convert_to_hypertable()
    if not hypertable_success:
        print("ERRO: Falha ao converter para hypertable. Tentando continuar...")
    
    # Passo 4: Configurar compressão
    await setup_compression()
    
    # Passo 5: Criar índices otimizados
    await create_optimized_indexes()
    
    print("--- Configuração TimescaleDB concluída com sucesso! ---")

if __name__ == "__main__":
    asyncio.run(main()) 