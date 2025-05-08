import os
import sys
import asyncio
from supabase import create_client, Client

# Configurações do Supabase
SUPABASE_URL = "https://prcnldxsrpkhusanwffr.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InByY25sZHhzcnBraHVzYW53ZmZyIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NjE2MDg4MSwiZXhwIjoyMDYxNzM2ODgxfQ.qpto7gfuaZ0zGyxpEenfDlVC7Y3GtLWYkxdQa7wi_BA"

def get_supabase_client():
    """Obtém o cliente Supabase."""
    try:
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        return client
    except Exception as e:
        print(f"Erro ao criar cliente Supabase: {e}")
        sys.exit(1)

def check_timescaledb_exists(client):
    """Verifica se a extensão TimescaleDB já está instalada."""
    print("Verificando se TimescaleDB está instalado...")
    try:
        # Esta é uma função personalizada que deve existir no projeto
        response = client.rpc('check_extension_exists', {'extension_name': 'timescaledb'}).execute()
        if response.data == True:
            print("TimescaleDB já está instalado!")
        else:
            print("TimescaleDB não está instalado.")
        return response.data
    except Exception as e:
        print(f"Erro ao verificar TimescaleDB: {e}")
        print("Assumindo que TimescaleDB não está instalado.")
        return False

def install_timescaledb(client):
    """Instala a extensão TimescaleDB."""
    print("Tentando instalar TimescaleDB...")
    try:
        # Esta é uma função personalizada que deve existir no projeto
        response = client.rpc('install_extension', {'extension_name': 'timescaledb'}).execute()
        if response.data == True:
            print("TimescaleDB instalado com sucesso!")
        else:
            print("Falha ao instalar TimescaleDB.")
        return response.data
    except Exception as e:
        print(f"Erro ao instalar TimescaleDB: {e}")
        return False

def check_price_history_exists(client):
    """Verifica se a tabela price_history existe."""
    print("Verificando se a tabela price_history existe...")
    try:
        # Consulta via SQL
        response = client.table('price_history').select('id').limit(1).execute()
        exists = True  # Se não falhar, a tabela existe
        print("Tabela price_history existe!")
        return exists
    except Exception as e:
        print(f"Tabela price_history não existe ou erro: {e}")
        return False

def create_price_history_table(client):
    """Cria a tabela price_history."""
    print("Criando tabela price_history...")
    
    # Verificar primeiro se já existe
    if check_price_history_exists(client):
        print("Tabela price_history já existe. Pulando criação.")
        return True
    
    try:
        # Esta é uma função personalizada que deve existir no projeto
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
        
        response = client.rpc('run_sql', {'sql_query': query}).execute()
        print("Tabela price_history criada com sucesso!")
        return True
    except Exception as e:
        print(f"Erro ao criar tabela price_history: {e}")
        return False

def convert_to_hypertable(client):
    """Converte price_history para hypertable."""
    print("Convertendo price_history para hypertable...")
    
    try:
        query = """
        SELECT create_hypertable('price_history', 'timestamp', 
                                 if_not_exists => TRUE,
                                 create_default_indexes => FALSE);
        """
        
        response = client.rpc('run_sql', {'sql_query': query}).execute()
        print("price_history convertida para hypertable com sucesso!")
        return True
    except Exception as e:
        print(f"Erro ao converter para hypertable: {e}")
        return False

def setup_compression(client):
    """Configura compressão para dados históricos."""
    print("Configurando compressão de dados...")
    
    try:
        query = """
        -- Habilitar compressão
        ALTER TABLE price_history SET (
          timescaledb.compress,
          timescaledb.compress_segmentby = 'symbol,timeframe',
          timescaledb.compress_orderby = 'timestamp DESC'
        );
        
        -- Criar política de compressão
        SELECT add_compression_policy('price_history', INTERVAL '7 days');
        """
        
        response = client.rpc('run_sql', {'sql_query': query}).execute()
        print("Compressão configurada com sucesso!")
        return True
    except Exception as e:
        print(f"Erro ao configurar compressão: {e}")
        # Não é crítico, pode continuar
        return False

def create_optimized_indexes(client):
    """Cria índices otimizados para consultas."""
    print("Criando índices otimizados...")
    
    try:
        query = """
        -- Índice de co-localização
        CREATE INDEX IF NOT EXISTS idx_price_history_symbol_timeframe_timestamp 
        ON price_history(symbol, timeframe, timestamp DESC);
        
        -- Índice para intervalo de datas
        CREATE INDEX IF NOT EXISTS idx_price_history_timestamp_range 
        ON price_history USING BRIN(timestamp);
        """
        
        response = client.rpc('run_sql', {'sql_query': query}).execute()
        print("Índices otimizados criados com sucesso!")
        return True
    except Exception as e:
        print(f"Erro ao criar índices otimizados: {e}")
        # Não é crítico, pode continuar
        return False

def create_functions(client):
    """Cria funções SQL úteis no Supabase."""
    print("Criando funções SQL no Supabase...")
    
    try:
        # Função para verificar se uma extensão existe
        query_check_extension = """
        CREATE OR REPLACE FUNCTION check_extension_exists(extension_name TEXT)
        RETURNS BOOLEAN
        LANGUAGE plpgsql
        SECURITY DEFINER
        AS $$
        DECLARE
            exists_result BOOLEAN;
        BEGIN
            SELECT EXISTS (
                SELECT FROM pg_extension
                WHERE extname = extension_name
            ) INTO exists_result;
            
            RETURN exists_result;
        END;
        $$;
        """
        
        # Função para instalar uma extensão
        query_install_extension = """
        CREATE OR REPLACE FUNCTION install_extension(extension_name TEXT)
        RETURNS BOOLEAN
        LANGUAGE plpgsql
        SECURITY DEFINER
        AS $$
        DECLARE
            command TEXT;
        BEGIN
            command := 'CREATE EXTENSION IF NOT EXISTS ' || extension_name || ' CASCADE;';
            EXECUTE command;
            RETURN TRUE;
        EXCEPTION
            WHEN OTHERS THEN
                RAISE NOTICE 'Erro ao instalar extensão %: %', extension_name, SQLERRM;
                RETURN FALSE;
        END;
        $$;
        """
        
        # Função para executar SQL genérico
        query_run_sql = """
        CREATE OR REPLACE FUNCTION run_sql(sql_query TEXT)
        RETURNS VOID
        LANGUAGE plpgsql
        SECURITY DEFINER
        AS $$
        BEGIN
            EXECUTE sql_query;
        END;
        $$;
        """
        
        # Criar as funções
        client.rpc('run_sql', {'sql_query': query_check_extension}).execute()
        print("Função check_extension_exists criada com sucesso!")
        
        client.rpc('run_sql', {'sql_query': query_install_extension}).execute()
        print("Função install_extension criada com sucesso!")
        
        client.rpc('run_sql', {'sql_query': query_run_sql}).execute()
        print("Função run_sql criada com sucesso!")
        
        return True
    except Exception as e:
        print(f"Erro ao criar funções SQL: {e}")
        # Tentar criar individualmente
        try:
            # Criar função genérica run_sql primeiro
            client.rpc('run_sql', {'sql_query': query_run_sql}).execute()
            print("Função run_sql criada com sucesso!")
            return True
        except Exception as e2:
            print(f"Erro ao criar função run_sql: {e2}")
            return False

def run_setup():
    """Função principal de configuração."""
    print("--- Configuração de TimescaleDB para Nação Trader ---")
    
    # Obter cliente Supabase
    client = get_supabase_client()
    
    # Criar funções úteis primeiro
    functions_created = create_functions(client)
    if not functions_created:
        print("AVISO: Falha ao criar funções SQL. Continuando mesmo assim...")
    
    # Instalar TimescaleDB
    if not check_timescaledb_exists(client):
        installed = install_timescaledb(client)
        if not installed:
            print("ERRO: Falha ao instalar TimescaleDB. Tentando continuar...")
    
    # Criar tabela price_history
    table_created = create_price_history_table(client)
    if not table_created:
        print("ERRO: Falha ao criar tabela price_history. Tentando continuar...")
    
    # Converter para hypertable
    hypertable_success = convert_to_hypertable(client)
    if not hypertable_success:
        print("ERRO: Falha ao converter para hypertable. Tentando continuar...")
    
    # Configurar compressão
    compression_success = setup_compression(client)
    if not compression_success:
        print("AVISO: Falha ao configurar compressão. Continuando...")
    
    # Criar índices otimizados
    indexes_success = create_optimized_indexes(client)
    if not indexes_success:
        print("AVISO: Falha ao criar índices otimizados. Continuando...")
    
    print("--- Configuração concluída! ---")

if __name__ == "__main__":
    run_setup() 