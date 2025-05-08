"""
Script de demonstração do Motor de Sinais ML.

Este script demonstra o uso dos diversos componentes do motor, incluindo:
- Coleta de dados de diferentes fontes
- Treinamento de modelos ML
- Geração de sinais

Para executar:
    $ python -m motor.demo
"""
import asyncio
import os
import json
from datetime import datetime, timedelta

import pandas as pd
import matplotlib.pyplot as plt
from loguru import logger

from src.models.ml_models import DirectionPredictionModel, ModelConfig, ModelType
from src.processors.ml_processor import (
    generate_ml_signal,
    load_price_data,
    train_model,
    batch_generate_signals
)
from src.collectors.yahoo_finance_collector import get_yahoo_finance_collector
from src.collectors.coingecko_collector import get_coingecko_collector


async def demo_data_collection():
    """Demonstra a coleta de dados de diferentes fontes."""
    logger.info("Demonstração de coleta de dados")
    
    # Yahoo Finance
    yahoo_collector = get_yahoo_finance_collector()
    
    # Coletar dados históricos de uma ação
    logger.info("Coletando dados do Yahoo Finance...")
    
    try:
        stock_data = await yahoo_collector.fetch_historical_data(
            symbol="AAPL",
            period="1y",
            interval="1d",
            save_to_db=False
        )
        
        if not stock_data.empty:
            logger.info(f"Dados coletados: {len(stock_data)} registros")
            print(f"Primeiros registros:\n{stock_data.head()}")
            
            # Plotar dados
            plt.figure(figsize=(12, 6))
            plt.plot(pd.to_datetime(stock_data['timestamp']), stock_data['close'])
            plt.title('AAPL - Preço de Fechamento (Último Ano)')
            plt.xlabel('Data')
            plt.ylabel('Preço ($)')
            plt.grid(True)
            plt.savefig('aapl_price.png')
            logger.info("Gráfico salvo em aapl_price.png")
        else:
            logger.warning("Nenhum dado retornado do Yahoo Finance")
    except Exception as e:
        logger.error(f"Erro ao coletar dados do Yahoo Finance: {e}")
    
    # CoinGecko
    coingecko_collector = get_coingecko_collector()
    
    # Coletar dados históricos de uma criptomoeda
    logger.info("Coletando dados do CoinGecko...")
    
    try:
        crypto_data = await coingecko_collector.fetch_historical_data(
            coin_id="bitcoin",
            vs_currency="usd",
            days="90",
            interval="daily",
            save_to_db=False
        )
        
        if not crypto_data.empty:
            logger.info(f"Dados coletados: {len(crypto_data)} registros")
            print(f"Primeiros registros:\n{crypto_data.head()}")
            
            # Plotar dados
            plt.figure(figsize=(12, 6))
            plt.plot(pd.to_datetime(crypto_data['timestamp']), crypto_data['close'])
            plt.title('Bitcoin - Preço de Fechamento (Últimos 90 dias)')
            plt.xlabel('Data')
            plt.ylabel('Preço ($)')
            plt.grid(True)
            plt.savefig('btc_price.png')
            logger.info("Gráfico salvo em btc_price.png")
        else:
            logger.warning("Nenhum dado retornado do CoinGecko")
    except Exception as e:
        logger.error(f"Erro ao coletar dados do CoinGecko: {e}")


async def demo_model_training():
    """Demonstra o treinamento de modelos ML."""
    logger.info("Demonstração de treinamento de modelos")
    
    # Definir ativo e timeframe
    asset_id = "AAPL"
    timeframe = "1d"
    
    try:
        # Verificar se já temos dados de preço
        price_data = load_price_data(asset_id, timeframe)
        
        if price_data.empty:
            logger.warning(f"Sem dados para {asset_id}, usando dados simulados")
        
        # Treinar modelo
        logger.info(f"Treinando modelo para {asset_id}...")
        performance = train_model(asset_id, timeframe, force_retrain=True)
        
        # Exibir métricas
        logger.info(f"Modelo treinado com sucesso!")
        logger.info(f"Accuracy: {performance.accuracy:.4f}")
        logger.info(f"Precision: {performance.precision:.4f}")
        logger.info(f"Recall: {performance.recall:.4f}")
        logger.info(f"F1 Score: {performance.f1:.4f}")
        
        # Verificar caminho do modelo
        model_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "models",
            f"model_{asset_id}_{timeframe}.pkl"
        )
        logger.info(f"Modelo salvo em: {model_path}")
        
        # Demonstrar carregamento do modelo
        model = DirectionPredictionModel.load(model_path)
        logger.info(f"Modelo carregado. Tipo: {model.config.model_type}")
    
    except Exception as e:
        logger.error(f"Erro ao treinar modelo: {e}")


async def demo_signal_generation():
    """Demonstra a geração de sinais."""
    logger.info("Demonstração de geração de sinais")
    
    # Definir ativos
    assets = [
        {"id": "AAPL", "symbol": "AAPL"},
        {"id": "MSFT", "symbol": "MSFT"},
        {"id": "BTCUSD", "symbol": "BTC-USD"},
        {"id": "EURUSD", "symbol": "EUR-USD"}
    ]
    
    # Gerar um sinal individual
    try:
        logger.info(f"Gerando sinal para {assets[0]['symbol']}...")
        signal = await generate_ml_signal(
            asset_id=assets[0]['id'],
            asset_symbol=assets[0]['symbol'],
            timeframe="1d",
            lookback_periods=100
        )
        
        # Exibir detalhes do sinal
        logger.info(f"Sinal gerado: {signal['direction']} com confiança {signal['confidence']:.2f}")
        logger.info(f"Preço alvo: {signal['price_target']}")
        logger.info(f"Stop loss: {signal['stop_loss']}")
        
        # Salvar em arquivo para referência
        with open('signal_example.json', 'w') as f:
            json.dump(signal, f, indent=2)
        logger.info("Sinal salvo em signal_example.json")
    
    except Exception as e:
        logger.error(f"Erro ao gerar sinal individual: {e}")
    
    # Gerar sinais em lote
    try:
        logger.info("Gerando sinais em lote...")
        asset_ids = [asset['id'] for asset in assets]
        
        batch_signals = await batch_generate_signals(
            asset_ids=asset_ids,
            timeframe="1d"
        )
        
        # Exibir resumo
        logger.info(f"Gerados {len(batch_signals)} sinais em lote:")
        for i, signal in enumerate(batch_signals):
            logger.info(f"{i+1}. {signal['asset_symbol']}: {signal['direction']} (confiança: {signal['confidence']:.2f})")
        
        # Salvar em arquivo para referência
        with open('batch_signals_example.json', 'w') as f:
            json.dump(batch_signals, f, indent=2)
        logger.info("Sinais em lote salvos em batch_signals_example.json")
    
    except Exception as e:
        logger.error(f"Erro ao gerar sinais em lote: {e}")


async def run_demo():
    """Executa todas as demonstrações."""
    try:
        logger.info("Iniciando demonstração do Motor de Sinais ML")
        
        # Demonstrar coleta de dados
        await demo_data_collection()
        
        # Demonstrar treinamento de modelos
        await demo_model_training()
        
        # Demonstrar geração de sinais
        await demo_signal_generation()
        
        logger.info("Demonstração concluída com sucesso!")
    
    except Exception as e:
        logger.error(f"Erro na execução da demonstração: {e}")


if __name__ == "__main__":
    asyncio.run(run_demo()) 