"""
Script principal para execução dos coletores de dados.

Este script coordena a execução dos vários coletores de dados
para diferentes fontes (Finnhub, Yahoo Finance).
"""
import asyncio
import os
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

import pandas as pd
from loguru import logger

from src.collectors.finnhub_collector import get_finnhub_collector
from src.collectors.yahoo_finance_collector import get_yahoo_finance_collector
from src.utils.config import settings


async def collect_stocks():
    """Coleta dados de ações."""
    try:
        logger.info("Iniciando coleta de dados de ações")
        
        # Obter coletor do Yahoo Finance
        yahoo_collector = get_yahoo_finance_collector()
        
        # Lista de ações populares para coleta (pode ser expandida)
        stock_symbols = [
            # Tecnologia
            "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "AMD", "INTC",
            # Financeiras
            "JPM", "BAC", "GS", "MS", "WFC", "V", "MA",
            # Consumo
            "PG", "KO", "PEP", "MCD", "SBUX", "NKE", "WMT", "TGT",
            # Saúde
            "JNJ", "PFE", "MRNA", "ABT", "UNH",
            # Índices
            "^GSPC", "^DJI", "^IXIC", "^FTSE",
        ]
        
        # Coletar dados históricos
        results = await yahoo_collector.batch_fetch_historical_data(
            symbols=stock_symbols,
            period="5y",  # Últimos 5 anos
            interval="1d"  # Dados diários
        )
        
        # Atualizar informações dos ativos
        await yahoo_collector.update_assets_info(stock_symbols)
        
        logger.info(f"Coleta de dados de ações concluída. {len(results)} ações processadas.")
    except Exception as e:
        logger.error(f"Erro na coleta de dados de ações: {e}")


async def collect_forex():
    """Coleta dados de forex."""
    try:
        logger.info("Iniciando coleta de dados de forex")
        
        # Obter coletor do Yahoo Finance
        yahoo_collector = get_yahoo_finance_collector()
        
        # Lista de pares forex populares para coleta
        forex_symbols = [
            "EURUSD=X", "GBPUSD=X", "USDJPY=X", "USDCHF=X", "AUDUSD=X", 
            "USDCAD=X", "NZDUSD=X", "EURGBP=X", "EURJPY=X", "GBPJPY=X"
        ]
        
        # Coletar dados históricos
        results = await yahoo_collector.batch_fetch_historical_data(
            symbols=forex_symbols,
            period="2y",  # Últimos 2 anos
            interval="1d"  # Dados diários
        )
        
        # Atualizar informações dos ativos
        await yahoo_collector.update_assets_info(forex_symbols)
        
        logger.info(f"Coleta de dados de forex concluída. {len(results)} pares processados.")
    except Exception as e:
        logger.error(f"Erro na coleta de dados de forex: {e}")


async def collect_finnhub_data():
    """Coleta dados da API Finnhub."""
    try:
        logger.info("Iniciando coleta de dados do Finnhub")
        
        # Obter coletor Finnhub
        finnhub_collector = get_finnhub_collector()
        
        # Coletar e armazenar ativos
        await finnhub_collector.fetch_and_store_assets()
        
        # Atualizar preços
        await finnhub_collector.update_asset_prices()
        
        logger.info("Coleta de dados do Finnhub concluída.")
    except Exception as e:
        logger.error(f"Erro na coleta de dados do Finnhub: {e}")


async def run_all_collectors():
    """Executa todos os coletores em sequência."""
    try:
        logger.info("Iniciando execução de todos os coletores")
        
        # Executar coletores
        await collect_stocks()
        await collect_forex()
        
        # Finnhub se tiver chave API configurada
        if hasattr(settings, "FINNHUB_API_KEY") and settings.FINNHUB_API_KEY:
            await collect_finnhub_data()
        
        logger.info("Todos os coletores executados com sucesso")
    except Exception as e:
        logger.error(f"Erro na execução dos coletores: {e}")


async def scheduled_collection():
    """Executa a coleta de dados em intervalos programados."""
    try:
        while True:
            logger.info("Iniciando coleta de dados programada")
            
            # Executar todos os coletores
            await run_all_collectors()
            
            # Intervalo definido nas configurações (em segundos)
            collection_interval = getattr(settings, "DATA_COLLECTION_INTERVAL", 3600)
            
            logger.info(f"Coleta concluída. Próxima execução em {collection_interval} segundos")
            await asyncio.sleep(collection_interval)
    except Exception as e:
        logger.error(f"Erro na coleta programada: {e}")
        # Tentar reiniciar após uma falha
        await asyncio.sleep(300)  # 5 minutos
        await scheduled_collection()


async def main():
    """Função principal."""
    # Configurar logger
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level=settings.LOG_LEVEL,
    )
    logger.add(
        "logs/collectors.log",
        rotation="10 MB",
        retention="1 week",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        level=settings.LOG_LEVEL,
    )
    
    # Criar diretório de logs se não existir
    os.makedirs("logs", exist_ok=True)
    
    # Verificar argumentos de linha de comando
    if len(sys.argv) > 1:
        if sys.argv[1] == "once":
            # Executar uma vez
            await scheduled_collection()
        elif sys.argv[1] == "continuous":
            # Executar continuamente
            interval = int(sys.argv[2]) if len(sys.argv) > 2 else None
            await run_continuous_collection(interval)
        else:
            logger.error(f"Argumento inválido: {sys.argv[1]}")
            logger.info("Uso: python -m src.collectors.run_collectors [once|continuous] [interval_seconds]")
    else:
        # Por padrão, executar uma vez
        await scheduled_collection()


if __name__ == "__main__":
    asyncio.run(main()) 