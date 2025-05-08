"""
Cliente para conexão com o banco de dados Supabase.

Fornece funções para conectar ao Supabase e executar operações de banco de dados.
"""
import os
from typing import Dict, List, Any, Optional, Union
import asyncio
import json
from pathlib import Path

try:
    from supabase import create_client, Client
except ImportError:
    import subprocess
    import sys
    print("Instalando supabase-py...")
    subprocess.run([sys.executable, "-m", "pip", "install", "supabase"], check=True)
    from supabase import create_client, Client

try:
    import httpx
except ImportError:
    import subprocess
    import sys
    print("Instalando httpx...")
    subprocess.run([sys.executable, "-m", "pip", "install", "httpx"], check=True)
    import httpx

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger("supabase")
    logging.basicConfig(level=logging.INFO)

# Importar configurações (com fallback para variáveis de ambiente)
try:
    from src.utils.config import settings
except ImportError:
    # Criar configurações básicas a partir das variáveis de ambiente
    class SettingsFallback:
        def __init__(self):
            self.SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
            self.SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
            self.SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
    
    settings = SettingsFallback()

# Cache de cliente para reutilização
_CLIENT_CACHE = None

async def get_supabase_client() -> Client:
    """
    Obtém um cliente Supabase configurado.
    
    Reutiliza o cliente se já existir.
    
    Returns:
        Client: Cliente Supabase configurado
    
    Raises:
        ValueError: Se as credenciais Supabase não estiverem configuradas
    """
    global _CLIENT_CACHE
    
    # Verificar se já temos um cliente cacheado
    if _CLIENT_CACHE:
        return _CLIENT_CACHE
    
    # Verificar se temos as configurações necessárias
    url = settings.SUPABASE_URL if hasattr(settings, "SUPABASE_URL") else os.environ.get("SUPABASE_URL")
    key = None
    
    # Preferência para a chave de serviço, com fallback para chave anônima
    if hasattr(settings, "SUPABASE_SERVICE_KEY") and settings.SUPABASE_SERVICE_KEY:
        key = settings.SUPABASE_SERVICE_KEY
    elif os.environ.get("SUPABASE_SERVICE_KEY"):
        key = os.environ.get("SUPABASE_SERVICE_KEY")
    elif hasattr(settings, "SUPABASE_ANON_KEY") and settings.SUPABASE_ANON_KEY:
        key = settings.SUPABASE_ANON_KEY
    elif os.environ.get("SUPABASE_ANON_KEY"):
        key = os.environ.get("SUPABASE_ANON_KEY")
    
    if not url or not key:
        raise ValueError(
            "Configuração Supabase ausente. "
            "Configure SUPABASE_URL e SUPABASE_SERVICE_KEY ou SUPABASE_ANON_KEY "
            "nas variáveis de ambiente ou .env"
        )
    
    # Criar cliente Supabase
    try:
        # Mostrar URL sem expor a chave
        masked_url = f"{url[:20]}...{url[-10:]}" if len(url) > 30 else url
        logger.debug(f"Conectando ao Supabase: {masked_url}")
        
        timeout = httpx.Timeout(30.0, connect=30.0)  # Timeout mais longo para operações lentas
        client = create_client(url, key, options={"timeout": timeout})
        
        # Testar conexão
        try:
            await client.auth.get_user()
            logger.debug("Autenticação com Supabase bem-sucedida")
        except Exception as e:
            # Se falhar com erro de autenticação, ainda podemos tentar usar o cliente
            # para operações que não requerem autenticação
            logger.warning(f"Aviso na autenticação Supabase: {e}")
        
        # Armazenar em cache
        _CLIENT_CACHE = client
        
        logger.debug("Conexão com Supabase estabelecida")
        return client
    
    except Exception as e:
        logger.error(f"Erro ao conectar ao Supabase: {e}")
        raise

async def execute_sql(query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Executa uma consulta SQL no Supabase.
    
    Args:
        query: Consulta SQL a ser executada
        params: Parâmetros para a consulta (opcional)
    
    Returns:
        List[Dict[str, Any]]: Resultado da consulta
    
    Raises:
        Exception: Se ocorrer erro na execução da consulta
    """
    client = await get_supabase_client()
    
    try:
        if params:
            # Executar consulta com parâmetros
            payload = {
                'query': query,
                'params': params
            }
            response = await client.rpc('execute_sql_with_params', payload)
        else:
            # Executar consulta simples
            response = await client.rpc('execute_sql', {'query': query})
        
        return response
    except Exception as e:
        logger.error(f"Erro ao executar SQL: {e}")
        logger.debug(f"Query: {query}")
        if params:
            logger.debug(f"Params: {json.dumps(params)}")
        
        # Verificar se a função RPC existe
        try:
            # Tentar abordagem alternativa usando funções padrão do Postgrest
            if "select" in query.lower():
                # Se for uma consulta SELECT sem parâmetros, podemos tentar diretamente
                # Simplificar a consulta e tentar com from_
                table_match = query.lower().split("from")[1].strip().split()[0].strip().rstrip(';')
                if table_match:
                    logger.info(f"Tentando consulta alternativa na tabela {table_match}")
                    result = await client.table(table_match).select("*").execute()
                    return result.data
            
            raise e  # Se não conseguimos, propagar o erro original
        except Exception:
            # Se a abordagem alternativa falhar, relançar o erro original
            raise e

async def test_connection() -> bool:
    """
    Testa a conexão com o banco de dados.
    
    Returns:
        bool: True se a conexão foi bem-sucedida
    """
    try:
        client = await get_supabase_client()
        # Executar consulta simples para testar
        result = await execute_sql("SELECT NOW() as time")
        
        if result and len(result) > 0:
            logger.info(f"Conexão com banco de dados testada com sucesso: {result[0].get('time')}")
            return True
        return False
    except Exception as e:
        logger.error(f"Erro ao testar conexão com banco de dados: {e}")
        return False

# Executar teste de conexão se executado diretamente
if __name__ == "__main__":
    import asyncio
    asyncio.run(test_connection()) 