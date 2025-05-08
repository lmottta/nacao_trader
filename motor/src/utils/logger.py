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

# Limpar loggers existentes
logger.remove()

# Variáveis de contexto global
HOSTNAME = socket.gethostname()
VERSION = "1.0.0"  # Deve ser extraído de um arquivo de versão ou variável de ambiente

# Carregar configuração de ambiente (dev, test, prod)
ENVIRONMENT = os.getenv("ENV", "development")

# Configurar nível de log baseado no ambiente
LOG_LEVELS = {
    "development": "DEBUG",
    "test": "INFO",
    "production": "WARNING"
}
DEFAULT_LOG_LEVEL = LOG_LEVELS.get(ENVIRONMENT, "INFO")

# Formato JSON para logs
class JsonFormatter:
    """Formata mensagens de log como JSON."""
    
    def __call__(self, record: Dict[str, Any]) -> str:
        """
        Formata um registro de log como JSON.
        
        Args:
            record: O registro de log a ser formatado
            
        Returns:
            str: Registro formatado como JSON
        """
        log_data = {
            "timestamp": record["time"].strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": record["level"].name,
            "message": record["message"],
            "logger": record["name"],
            "file": record["file"].name,
            "line": record["line"],
            "function": record["function"],
            "environment": ENVIRONMENT,
            "hostname": HOSTNAME,
            "version": VERSION
        }
        
        # Adicionar exceção se presente
        if record["exception"]:
            log_data["exception"] = {
                "type": record["exception"].type.__name__,
                "value": str(record["exception"].value),
                "traceback": traceback.format_tb(record["exception"].traceback)
            }
        
        # Adicionar contexto extra
        if record["extra"]:
            log_data.update(record["extra"])
        
        return json.dumps(log_data)

# Configurar saída para console com formatação legível para humanos
logger.add(
    sys.stdout,
    level=os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL),
    format=("<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"),
    colorize=True
)

# Configurar arquivo de log com formatação JSON
logger.add(
    LOG_DIR / f"{ENVIRONMENT}_{{time:YYYY-MM-DD}}.log",
    level=os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL),
    format="{message}",
    rotation=os.getenv("LOG_ROTATION", "10 MB"),
    retention=os.getenv("LOG_RETENTION", "1 week"),
    compression="zip",
    enqueue=True,
    filter=lambda record: record["level"].no >= logger.level(DEFAULT_LOG_LEVEL).no,
    serialize=JsonFormatter()
)

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