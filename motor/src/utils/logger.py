"""
Sistema de logging estruturado para o Motor de Sinais ML.

Este módulo fornece funções para configurar e obter loggers
com suporte a logs estruturados em formato JSON, rotação
de arquivos e contextualização enriquecida.
"""
import json
import os
import socket
import sys
import traceback
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union
import asyncio

from loguru import logger

# Diretório para logs
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Carregar configuração de ambiente (dev, test, prod)
ENVIRONMENT = os.getenv("ENV", "development")

# Configurar nível de log baseado no ambiente
LOG_LEVELS = {
    "development": "DEBUG",
    "test": "INFO",
    "production": "WARNING"
}
DEFAULT_LOG_LEVEL = LOG_LEVELS.get(ENVIRONMENT, "INFO")

def setup_logger(
    log_name: str,
    log_file: Union[str, Path],
    level: str = DEFAULT_LOG_LEVEL,
    rotation: str = "10 MB",
    retention: str = "7 days",
) -> "Logger":
    """Configura e retorna um logger Loguru com um handler de arquivo e um formatador JSON."""
    # Garante que o diretório do arquivo de log exista
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Acessa o logger global do Loguru para remover configurações existentes
    from loguru import logger
    logger.remove()

    # Adiciona o handler de arquivo com serialização JSON nativa do Loguru
    logger.add(
        log_path,
        level=level.upper(),
        rotation=rotation,
        retention=retention,
        enqueue=True,      # Torna a escrita de logs assíncrona e segura
        serialize=True,    # Ativa a serialização JSON nativa
        catch=True,        # Captura exceções dentro do logger
    )

    # Adiciona metadados globais ao contexto do logger
    # Esses dados estarão disponíveis em todos os logs através de `record['extra']`
    bound_logger = logger.bind(
        hostname=HOSTNAME,
        version=VERSION,
        environment=ENVIRONMENT
    )

    bound_logger.info(f"Logger '{log_name}' configurado. Nível: {level}. Arquivo: {log_file}")

    return bound_logger

# Variáveis de contexto global
HOSTNAME = socket.gethostname()
VERSION = "1.0.0"  # Deve ser extraído de um arquivo de versão ou variável de ambiente



def get_logger(name: str) -> logger.__class__:
    """
    Obtém um logger configurado com o nome especificado.
    
    Args:
        name: Nome do logger
    
    Returns:
        Logger configurado
    """
    return logger.bind(name=name)

def log_execution_time(func: Callable) -> Callable:
    """
    Decorador para registrar o tempo de execução de uma função.
    
    Args:
        func: Função a ser decorada
    
    Returns:
        Função decorada
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Obter logger
        log = get_logger(func.__module__)
        
        # Registrar início
        start_time = datetime.now()
        log.debug(f"Iniciando {func.__name__}")
        
        try:
            # Executar função
            result = func(*args, **kwargs)
            
            # Registrar conclusão
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            log.debug(
                f"Concluído {func.__name__}",
                execution_time=execution_time,
                execution_time_ms=int(execution_time * 1000)
            )
            
            return result
        except Exception as e:
            # Registrar erro
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            log.error(
                f"Erro em {func.__name__}: {str(e)}",
                execution_time=execution_time,
                execution_time_ms=int(execution_time * 1000),
                error=str(e),
                error_type=type(e).__name__
            )
            
            # Relançar exceção
            raise
    
    return wrapper

def with_context(**context_kwargs):
    """
    Decorador para adicionar contexto adicional ao logger para uma função.
    
    Args:
        **context_kwargs: Parâmetros de contexto nomeados (aceita endpoint e outros)
    
    Returns:
        Decorador que aplica o contexto
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            log = get_logger(func.__module__).bind(**context_kwargs)
            log.debug(f"Executando {func.__name__} com contexto")
            return await func(*args, **kwargs)
            
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            log = get_logger(func.__module__).bind(**context_kwargs)
            log.debug(f"Executando {func.__name__} com contexto")
            return func(*args, **kwargs)
            
        # Determinar se a função é assíncrona ou síncrona
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
            
    return decorator

# Exemplo de uso:
# log = get_logger(__name__)
# log.info("Mensagem informativa")
# log.warning("Aviso", extra_data="valor")
# 
# user_log = logger.bind(user_id="123", session="abc")
# user_log.info("Ação do usuário")
# 
# @log_execution_time
# def funcao_demorada():
#     # código
#     pass