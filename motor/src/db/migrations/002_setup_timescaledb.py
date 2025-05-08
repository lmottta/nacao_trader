"""
Migração para configurar o TimescaleDB no banco de dados.

Esta migração:
1. Instala a extensão TimescaleDB
2. Converte a tabela price_history em uma hypertable
3. Configura compressão e políticas de retenção
4. Cria índices otimizados
"""
import asyncio
import datetime
import os
import sys
from typing import Dict, List, Any, Optional
from pathlib import Path

# Garantir que o módulo possa ser importado mesmo começando com número
# Isso é útil para quando o script é executado diretamente
__name__ = "timescale_setup_module" if __name__ == "__main__" else __name__

# Corrigir importação do BaseSettings que mudou no Pydantic v2
try:
    # Pydantic v2
    from pydantic_settings import BaseSettings
    from pydantic import model_validator
    PYDANTIC_V2 = True
except ImportError:
    try:
        # Tentar instalar pydantic-settings se necessário
        import subprocess
        import sys
        print("Instalando pydantic-settings...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pydantic-settings"], check=True)
        from pydantic_settings import BaseSettings
        from pydantic import model_validator
        PYDANTIC_V2 = True
    except Exception:
        # Fallback para Pydantic v1
        from pydantic import BaseSettings, validator
        PYDANTIC_V2 = False

# Setup logging
try:
    from loguru import logger
except ImportError:
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("timescaledb_migration")

# Supabase client
try:
    from supabase import create_client, Client
except ImportError:
    try:
        # Tentar instalar supabase-py se necessário
        import subprocess
        print("Instalando supabase-py...")
        subprocess.run([sys.executable, "-m", "pip", "install", "supabase"], check=True)
        from supabase import create_client, Client
    except Exception as e:
        logger.error(f"Erro ao instalar supabase: {e}")
        raise ImportError("Dependência supabase-py necessária para esta migração")

# Adicionar diretório raiz ao path
try:
    # Adicionar root do projeto ao path para facilitar importações
    motor_root = Path(__file__).parent.parent.parent.parent  # migrations -> db -> src -> motor
    sys.path.insert(0, str(motor_root))
except Exception as e:
    logger.warning(f"Não foi possível adicionar diretório raiz ao path: {e}")

# Configuração
if PYDANTIC_V2:
    # Pydantic v2 - Usar model_config para permitir campos extras
    class SupabaseConfig(BaseSettings):
        SUPABASE_URL: str = ""
        SUPABASE_SERVICE_KEY: str = ""
        SUPABASE_ANON_KEY: Optional[str] = None
        
        model_config = {
            "env_file": ".env",
            "env_file_encoding": "utf-8",
            "extra": "allow"  # Permitir campos extras para evitar erros de validação
        }
        
        # Carregando diretamente das variáveis de ambiente
        @model_validator(mode="before")
        @classmethod
        def load_from_env(cls, values):
            """Carrega valores do ambiente se não fornecidos."""
            if isinstance(values, dict):
                for field in cls.model_fields:
                    if field not in values and field in os.environ:
                        values[field] = os.environ[field]
            return values
else:
    # Pydantic v1 - Usar Config para permitir campos extras
    class SupabaseConfig(BaseSettings):
        SUPABASE_URL: str = ""
        SUPABASE_SERVICE_KEY: str = ""
        SUPABASE_ANON_KEY: Optional[str] = None
        
        class Config:
            env_file = ".env"
            env_file_encoding = "utf-8"
            extra = "allow"  # Permitir campos extras para evitar erros de validação
        
        @validator('*')
        def load_from_env(cls, v, field):
            """Carrega valores do ambiente se não fornecidos."""
            if not v and field.name in os.environ:
                return os.environ[field.name]
            return v

# Usar variáveis de ambiente diretamente se o arquivo de configuração apresentar problemas
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY")

# Tentar carregar configuração
try:
    config = SupabaseConfig()
except Exception as e:
    logger.warning(f"Erro ao carregar configuração do arquivo .env: {e}")
    logger.info("Usando variáveis de ambiente diretamente")
    
    # Definir configuração manual
    if SUPABASE_URL and (SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY):
        class ManualConfig:
            def __init__(self):
                self.SUPABASE_URL = SUPABASE_URL
                self.SUPABASE_SERVICE_KEY = SUPABASE_SERVICE_KEY or SUPABASE_ANON_KEY
                self.SUPABASE_ANON_KEY = SUPABASE_ANON_KEY
        
        config = ManualConfig()
    else:
        logger.error("Variáveis de ambiente para Supabase não encontradas")
        raise ValueError("Configuração Supabase ausente. Configure as variáveis de ambiente ou .env")

async def get_supabase_client() -> Client:
    """
    Obtém um cliente Supabase configurado.
    
    Returns:
        Client: Cliente Supabase
    """
    # Preferência para a chave de serviço, com fallback para chave anônima
    key = config.SUPABASE_SERVICE_KEY if hasattr(config, "SUPABASE_SERVICE_KEY") and config.SUPABASE_SERVICE_KEY else config.SUPABASE_ANON_KEY
    
    if not key:
        raise ValueError("Nenhuma chave Supabase disponível (SERVICE_KEY ou ANON_KEY)")
    
    try:
        return create_client(config.SUPABASE_URL, key)
    except Exception as e:
        logger.error(f"Erro ao criar cliente Supabase: {e}")
        raise

async def execute_sql(client: Client, query: str) -> List[Dict[str, Any]]:
    """
    Executa uma consulta SQL.
    
    Args:
        client: Cliente Supabase
        query: Consulta SQL a ser executada
    
    Returns:
        List[Dict[str, Any]]: Resultado da consulta
    """
    try:
        response = await client.rpc('execute_sql', {'query': query})
        return response
    except Exception as e:
        logger.error(f"Erro ao executar SQL: {e}")
        logger.error(f"Query: {query}")
        
        # Tentar abordagem alternativa se a função RPC não existir
        if "from pg_extension" in query.lower():
            # Para consultas sobre extensões, usar uma abordagem alternativa
            try:
                logger.info("Tentando abordagem alternativa para verificar extensões...")
                alt_query = """
                SELECT COALESCE(
                    (SELECT TRUE WHERE EXISTS (
                        SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'
                    )),
                    FALSE
                ) as exists;
                """
                response = await client.rpc('execute_sql', {'query': alt_query})
                return response
            except Exception:
                # Ignorar e continuar com o erro original
                pass
                
        # Se a abordagem alternativa falhar, relançar o erro original
        raise e

async def check_extension_exists(client: Client) -> bool:
    """
    Verifica se a extensão TimescaleDB já está instalada.
    
    Args:
        client: Cliente Supabase
    
    Returns:
        bool: True se a extensão já estiver instalada
    """
    query = """
    SELECT EXISTS (
        SELECT FROM pg_extension
        WHERE extname = 'timescaledb'
    );
    """
    
    try:
        result = await execute_sql(client, query)
        return result[0].get('exists', False) if result else False
    except Exception as e:
        logger.warning(f"Não foi possível verificar a existência da extensão TimescaleDB: {e}")
        # Assumir que a extensão não existe em caso de erro
        return False

async def install_timescaledb(client: Client) -> bool:
    """
    Instala a extensão TimescaleDB no banco de dados.
    
    Args:
        client: Cliente Supabase
    
    Returns:
        bool: True se a instalação foi bem-sucedida
    """
    # Verificar se a extensão já existe
    exists = await check_extension_exists(client)
    if exists:
        logger.info("Extensão TimescaleDB já está instalada")
        return True
        
    query = """
    CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
    """
    
    try:
        await execute_sql(client, query)
        logger.info("Extensão TimescaleDB instalada com sucesso")
        return True
    except Exception as e:
        logger.error(f"Erro ao instalar extensão TimescaleDB: {e}")
        
        # Verificar se é um erro de permissão
        if "permission denied" in str(e).lower():
            logger.warning("Permissão negada ao instalar extensão. Pode ser necessário contatar o suporte do Supabase.")
            
        return False

async def check_hypertable_exists(client: Client, table_name: str) -> bool:
    """
    Verifica se a tabela já é uma hypertable.
    
    Args:
        client: Cliente Supabase
        table_name: Nome da tabela a verificar
    
    Returns:
        bool: True se a tabela já for uma hypertable
    """
    query = f"""
    SELECT EXISTS (
        SELECT FROM timescaledb_information.hypertables
        WHERE hypertable_name = '{table_name}'
    );
    """
    
    try:
        result = await execute_sql(client, query)
        return result[0].get('exists', False) if result else False
    except Exception as e:
        logger.warning(f"Não foi possível verificar se {table_name} é uma hypertable: {e}")
        # Em caso de erro, assumir que não é uma hypertable
        return False

async def check_table_exists(client: Client, table_name: str) -> bool:
    """
    Verifica se a tabela existe no banco de dados.
    
    Args:
        client: Cliente Supabase
        table_name: Nome da tabela a verificar
    
    Returns:
        bool: True se a tabela existir
    """
    query = f"""
    SELECT EXISTS (
        SELECT FROM information_schema.tables 
        WHERE table_schema = 'public'
        AND table_name = '{table_name}'
    );
    """
    
    try:
        result = await execute_sql(client, query)
        return result[0].get('exists', False) if result else False
    except Exception as e:
        logger.warning(f"Não foi possível verificar se a tabela {table_name} existe: {e}")
        return False

async def convert_to_hypertable(client: Client, table_name: str, time_column: str) -> bool:
    """
    Converte uma tabela em uma hypertable do TimescaleDB.
    
    Args:
        client: Cliente Supabase
        table_name: Nome da tabela
        time_column: Nome da coluna de tempo
    
    Returns:
        bool: True se a conversão foi bem-sucedida
    """
    # Verificar se a tabela já é uma hypertable
    is_hypertable = await check_hypertable_exists(client, table_name)
    if is_hypertable:
        logger.info(f"Tabela {table_name} já é uma hypertable")
        return True
        
    # Verificar se a tabela existe
    table_exists = await check_table_exists(client, table_name)
    if not table_exists:
        logger.warning(f"Tabela {table_name} não existe no banco de dados")
        return False
    
    query = f"""
    SELECT create_hypertable('{table_name}', '{time_column}', if_not_exists => TRUE);
    """
    
    try:
        await execute_sql(client, query)
        logger.info(f"Tabela {table_name} convertida para hypertable com sucesso")
        return True
    except Exception as e:
        logger.error(f"Erro ao converter tabela {table_name} para hypertable: {e}")
        return False

async def setup_compression(client: Client, table_name: str) -> bool:
    """
    Configura compressão para uma hypertable.
    
    Args:
        client: Cliente Supabase
        table_name: Nome da tabela
    
    Returns:
        bool: True se a configuração de compressão foi bem-sucedida
    """
    # Primeiro, verificar se a tabela é uma hypertable
    is_hypertable = await check_hypertable_exists(client, table_name)
    if not is_hypertable:
        logger.warning(f"Tabela {table_name} não é uma hypertable. Impossível configurar compressão.")
        return False
    
    # Verificar se a compressão já está habilitada
    check_query = f"""
    SELECT compression_enabled 
    FROM timescaledb_information.hypertables
    WHERE hypertable_name = '{table_name}';
    """
    
    try:
        result = await execute_sql(client, check_query)
        
        if result and result[0].get('compression_enabled', False):
            logger.info(f"Compressão já está habilitada para a tabela {table_name}")
            return True
        
        # Configurar colunas para compressão
        compression_query = f"""
        ALTER TABLE {table_name} SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'symbol,timeframe',
            timescaledb.compress_orderby = 'timestamp DESC'
        );
        """
        
        await execute_sql(client, compression_query)
        logger.info(f"Compressão configurada para tabela {table_name}")
        
        # Criar política de compressão (comprimir dados após 7 dias)
        policy_query = f"""
        SELECT add_compression_policy('{table_name}', INTERVAL '7 days');
        """
        
        await execute_sql(client, policy_query)
        logger.info(f"Política de compressão criada para tabela {table_name}")
        
        return True
    except Exception as e:
        logger.error(f"Erro ao configurar compressão para tabela {table_name}: {e}")
        logger.info("Continuando com a migração mesmo sem compressão")
        return False

async def create_indexes(client: Client, table_name: str) -> bool:
    """
    Cria índices otimizados para a hypertable.
    
    Args:
        client: Cliente Supabase
        table_name: Nome da tabela
    
    Returns:
        bool: True se a criação de índices foi bem-sucedida
    """
    try:
        # Verificar índices existentes
        check_query = f"""
        SELECT indexname FROM pg_indexes 
        WHERE tablename = '{table_name}' 
        AND indexname LIKE 'idx_%';
        """
        
        result = await execute_sql(client, check_query)
        existing_indexes = [idx['indexname'] for idx in result] if result else []
        
        # Lista de índices a serem criados
        indexes = [
            {
                "name": "idx_price_history_symbol",
                "query": f"CREATE INDEX IF NOT EXISTS idx_price_history_symbol ON {table_name} (symbol);"
            },
            {
                "name": "idx_price_history_timeframe",
                "query": f"CREATE INDEX IF NOT EXISTS idx_price_history_timeframe ON {table_name} (timeframe);"
            },
            {
                "name": "idx_price_history_symbol_timeframe",
                "query": f"CREATE INDEX IF NOT EXISTS idx_price_history_symbol_timeframe ON {table_name} (symbol, timeframe);"
            }
        ]
        
        # Criar índices que não existem
        created = 0
        for idx in indexes:
            if idx["name"] not in existing_indexes:
                await execute_sql(client, idx["query"])
                logger.info(f"Índice {idx['name']} criado com sucesso")
                created += 1
            else:
                logger.info(f"Índice {idx['name']} já existe")
        
        if created > 0:
            logger.info(f"{created} índices criados para tabela {table_name}")
        else:
            logger.info(f"Todos os índices necessários já existem para tabela {table_name}")
            
        return True
    except Exception as e:
        logger.error(f"Erro ao criar índices para tabela {table_name}: {e}")
        return False

async def create_retention_policy(client: Client, table_name: str, retention_period: str = "90 days") -> bool:
    """
    Cria uma política de retenção para a hypertable.
    
    Args:
        client: Cliente Supabase
        table_name: Nome da tabela
        retention_period: Período de retenção (ex: "90 days")
    
    Returns:
        bool: True se a criação da política foi bem-sucedida
    """
    # Verificar políticas existentes
    check_query = f"""
    SELECT job_id FROM timescaledb_information.jobs
    WHERE proc_name = 'policy_retention' 
    AND hypertable_schema = 'public'
    AND hypertable_name = '{table_name}';
    """
    
    try:
        result = await execute_sql(client, check_query)
        
        if result and len(result) > 0:
            logger.info(f"Política de retenção já existe para tabela {table_name}")
            return True
        
        # Criar política de retenção
        policy_query = f"""
        SELECT add_retention_policy('{table_name}', INTERVAL '{retention_period}');
        """
        
        await execute_sql(client, policy_query)
        logger.info(f"Política de retenção criada para tabela {table_name} ({retention_period})")
        
        return True
    except Exception as e:
        logger.error(f"Erro ao criar política de retenção para tabela {table_name}: {e}")
        logger.info("Continuando com a migração mesmo sem política de retenção")
        return False

async def setup_timescaledb_for_table(client: Client, table_name: str, time_column: str) -> bool:
    """
    Configura TimescaleDB para uma tabela específica.
    
    Args:
        client: Cliente Supabase
        table_name: Nome da tabela
        time_column: Nome da coluna de tempo
    
    Returns:
        bool: True se a configuração foi bem-sucedida
    """
    logger.info(f"Configurando TimescaleDB para tabela {table_name}")
    
    # Verificar se a extensão está instalada
    extension_exists = await check_extension_exists(client)
    if not extension_exists:
        logger.warning("TimescaleDB não está instalado. Tentando instalar...")
        success = await install_timescaledb(client)
        if not success:
            logger.error("Falha ao instalar TimescaleDB. Abortando configuração da tabela.")
            return False
    
    # Converter para hypertable
    success = await convert_to_hypertable(client, table_name, time_column)
    if not success:
        logger.error(f"Falha ao converter {table_name} para hypertable. Abortando configuração.")
        return False
    
    # Configurar compressão (opcional - continua mesmo se falhar)
    await setup_compression(client, table_name)
    
    # Criar índices
    await create_indexes(client, table_name)
    
    # Criar política de retenção (opcional - continua mesmo se falhar)
    await create_retention_policy(client, table_name)
    
    logger.info(f"Configuração TimescaleDB para tabela {table_name} concluída com sucesso")
    return True

async def run_migration():
    """
    Executa a migração TimescaleDB.
    
    Esta função é chamada externamente pelo script de configuração.
    """
    logger.info("Iniciando migração TimescaleDB")
    
    try:
        # Obter cliente Supabase
        client = await get_supabase_client()
        
        # Instalar extensão TimescaleDB
        success = await install_timescaledb(client)
        if not success:
            logger.warning("Falha ao instalar extensão TimescaleDB. Algumas funcionalidades podem estar indisponíveis.")
        
        # Configurar tabela price_history
        await setup_timescaledb_for_table(client, "price_history", "timestamp")
        
        logger.info("Migração TimescaleDB concluída com sucesso")
    except Exception as e:
        logger.error(f"Erro durante migração TimescaleDB: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise

# Se o script for executado diretamente
if __name__ == "__main__":
    asyncio.run(run_migration()) 