"""
Funções auxiliares para manipulação de dados.

Este módulo fornece funções utilitárias para trabalhar com dados,
incluindo backup, salvamento e carregamento de arquivos.
"""
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd
from loguru import logger


def create_backup_file(source_path: Union[str, Path], backup_dir: Optional[Union[str, Path]] = None) -> Path:
    """
    Cria uma cópia de backup de um arquivo.
    
    Args:
        source_path: Caminho do arquivo a ser copiado
        backup_dir: Diretório para o backup (opcional)
        
    Returns:
        Path: Caminho do arquivo de backup
    """
    source_path = Path(source_path)
    
    if not source_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {source_path}")
        
    # Definir diretório de backup
    if backup_dir is None:
        backup_dir = Path("data/backup")
        
    backup_dir = Path(backup_dir)
    os.makedirs(backup_dir, exist_ok=True)
    
    # Criar nome do arquivo de backup com timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{source_path.stem}_{timestamp}{source_path.suffix}"
    backup_path = backup_dir / backup_name
    
    # Copiar arquivo
    shutil.copy2(source_path, backup_path)
    logger.info(f"Backup criado: {backup_path}")
    
    return backup_path


def save_json(data: Union[Dict, List], file_path: Union[str, Path], indent: int = 2) -> bool:
    """
    Salva dados em um arquivo JSON.
    
    Args:
        data: Dados a serem salvos (dicionário ou lista)
        file_path: Caminho do arquivo
        indent: Número de espaços para indentação
        
    Returns:
        bool: True se o salvamento foi bem-sucedido
    """
    file_path = Path(file_path)
    
    # Criar diretório se não existir
    os.makedirs(file_path.parent, exist_ok=True)
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        
        logger.debug(f"Dados salvos em {file_path}")
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar dados em {file_path}: {e}")
        return False


def load_json(file_path: Union[str, Path]) -> Optional[Union[Dict, List]]:
    """
    Carrega dados de um arquivo JSON.
    
    Args:
        file_path: Caminho do arquivo
        
    Returns:
        Dados carregados ou None em caso de erro
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        logger.warning(f"Arquivo não encontrado: {file_path}")
        return None
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        logger.debug(f"Dados carregados de {file_path}")
        return data
    except Exception as e:
        logger.error(f"Erro ao carregar dados de {file_path}: {e}")
        return None


def save_dataframe(df: pd.DataFrame, file_path: Union[str, Path], format: str = "csv") -> bool:
    """
    Salva um DataFrame em um arquivo.
    
    Args:
        df: DataFrame a ser salvo
        file_path: Caminho do arquivo
        format: Formato de saída (csv, parquet, pickle, excel)
        
    Returns:
        bool: True se o salvamento foi bem-sucedido
    """
    file_path = Path(file_path)
    
    # Criar diretório se não existir
    os.makedirs(file_path.parent, exist_ok=True)
    
    try:
        if format.lower() == "csv":
            df.to_csv(file_path, index=False)
        elif format.lower() == "parquet":
            df.to_parquet(file_path, index=False)
        elif format.lower() == "pickle":
            df.to_pickle(file_path)
        elif format.lower() == "excel":
            df.to_excel(file_path, index=False)
        else:
            raise ValueError(f"Formato não suportado: {format}")
            
        logger.debug(f"DataFrame salvo em {file_path}")
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar DataFrame em {file_path}: {e}")
        return False


def load_dataframe(file_path: Union[str, Path], format: Optional[str] = None) -> Optional[pd.DataFrame]:
    """
    Carrega um DataFrame de um arquivo.
    
    Args:
        file_path: Caminho do arquivo
        format: Formato do arquivo (se None, será determinado pela extensão)
        
    Returns:
        DataFrame carregado ou None em caso de erro
    """
    file_path = Path(file_path)
    
    if not file_path.exists():
        logger.warning(f"Arquivo não encontrado: {file_path}")
        return None
    
    # Determinar formato pela extensão se não especificado
    if format is None:
        suffix = file_path.suffix.lower()
        if suffix == ".csv":
            format = "csv"
        elif suffix == ".parquet":
            format = "parquet"
        elif suffix in [".pkl", ".pickle"]:
            format = "pickle"
        elif suffix in [".xlsx", ".xls"]:
            format = "excel"
        else:
            raise ValueError(f"Não foi possível determinar o formato do arquivo: {file_path}")
    
    try:
        if format.lower() == "csv":
            df = pd.read_csv(file_path)
        elif format.lower() == "parquet":
            df = pd.read_parquet(file_path)
        elif format.lower() == "pickle":
            df = pd.read_pickle(file_path)
        elif format.lower() == "excel":
            df = pd.read_excel(file_path)
        else:
            raise ValueError(f"Formato não suportado: {format}")
            
        logger.debug(f"DataFrame carregado de {file_path}")
        return df
    except Exception as e:
        logger.error(f"Erro ao carregar DataFrame de {file_path}: {e}")
        return None 