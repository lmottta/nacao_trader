"""
Processador de sinais baseado em Machine Learning.

Este módulo contém as funções de processamento e geração de sinais usando
os modelos ML implementados em src/models/ml_models.py.
"""
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any

import pandas as pd
import numpy as np
from loguru import logger

from src.models.signal import (
    IndicatorValues,
    Signal,
    SignalDirection,
    SignalSource,
    SignalStatus,
    SignalTimeframe,
    ModelPerformance as SignalModelPerformance
)
from src.models.asset import Asset
from src.models.ml_models import (
    DirectionPredictionModel,
    ModelConfig,
    ModelType,
    ModelPerformanceMetrics
)
from src.utils.config import settings
from src.utils.supabase_client import SupabaseHelper


# Constantes para diretórios de modelos
MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "models")
PRICE_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")

# Certifique-se de que os diretórios existam
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(PRICE_DATA_DIR, exist_ok=True)


def get_model_path(asset_id: str, timeframe: str = "1d") -> str:
    """
    Retorna o caminho para o arquivo do modelo ML.
    
    Args:
        asset_id: ID do ativo
        timeframe: Timeframe do modelo
        
    Returns:
        Caminho completo para o arquivo do modelo
    """
    return os.path.join(MODELS_DIR, f"model_{asset_id}_{timeframe}.pkl")


def load_or_create_model(asset_id: str, timeframe: str = "1d") -> DirectionPredictionModel:
    """
    Carrega um modelo existente ou cria um novo se não existir.
    
    Args:
        asset_id: ID do ativo
        timeframe: Timeframe do modelo
        
    Returns:
        Modelo carregado ou criado
    """
    model_path = get_model_path(asset_id, timeframe)
    
    # Verificar se o modelo existe
    if os.path.exists(model_path):
        try:
            # Tentar carregar o modelo existente
            return DirectionPredictionModel.load(model_path)
        except Exception as e:
            logger.error(f"Erro ao carregar modelo: {e}")
            # Se falhar, criar um novo
            logger.info("Criando um novo modelo.")
    
    # Criar um novo modelo com configuração padrão
    config = DirectionPredictionModel.get_default_config()
    return DirectionPredictionModel(config)


def load_price_data(asset_symbol: str, timeframe: str = "1d", lookback_periods: int = 200) -> pd.DataFrame:
    """
    Carrega dados históricos de preços do Supabase.
    
    Args:
        asset_symbol: Símbolo do ativo (ex: AAPL, EURUSD)
        timeframe: Timeframe dos dados (ex: 1d, 1h, 5m)
        lookback_periods: Quantidade de registros a buscar
        
    Returns:
        DataFrame com dados OHLCV, ordenado por timestamp ASC.
        Retorna DataFrame vazio se ocorrer erro ou não houver dados.
    """
    logger.info(f"Buscando dados históricos para {asset_symbol} ({timeframe}) do Supabase...")
    try:
        helper = SupabaseHelper()
        # Usar o método get_price_history do helper
        price_data_list = helper.get_price_history(
            symbol=asset_symbol,
            timeframe=timeframe,
            limit=lookback_periods
            # start_date e end_date podem ser adicionados se necessário
        )

        if not price_data_list:
            logger.warning(f"Nenhum dado histórico encontrado para {asset_symbol} ({timeframe}).")
            return pd.DataFrame() # Retorna DataFrame vazio

        # Converter lista de dicionários para DataFrame
        df = pd.DataFrame(price_data_list)
        
        # Converter timestamp para datetime e definir como índice (opcional, mas útil para análise)
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        df = df.dropna(subset=['timestamp']) # Remover linhas com timestamp inválido
        df = df.sort_values('timestamp', ascending=True)
        # df = df.set_index('timestamp') # Descomentar se o índice for necessário
        
        # Garantir que colunas numéricas sejam numéricas
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Remover linhas com NaNs introduzidos pela conversão (ou tratar de outra forma)
        # df = df.dropna(subset=numeric_cols) 

        logger.info(f"Dados de preço carregados de Supabase para {asset_symbol}: {len(df)} registros")
        return df

    except Exception as e:
        logger.error(f"Erro ao carregar dados de preço do Supabase para {asset_symbol}: {e}", exc_info=True)
        return pd.DataFrame() # Retorna DataFrame vazio em caso de erro


def get_timeframe_duration(timeframe: str) -> timedelta:
    """
    Mapeia um timeframe para uma duração em timedelta.
    
    Args:
        timeframe: Timeframe (1m, 5m, 15m, 30m, 1h, 4h, 1d, 1w, 1M)
        
    Returns:
        Duração correspondente
    """
    timeframe_map = {
        "1m": timedelta(minutes=1),
        "5m": timedelta(minutes=5),
        "15m": timedelta(minutes=15),
        "30m": timedelta(minutes=30),
        "1h": timedelta(hours=1),
        "4h": timedelta(hours=4),
        "1d": timedelta(days=1),
        "1w": timedelta(weeks=1),
        "1M": timedelta(days=30),  # Aproximação
    }
    
    return timeframe_map.get(timeframe, timedelta(days=1))


def train_model(asset_id: str, asset_symbol: str, timeframe: str = "1d", force_retrain: bool = False) -> ModelPerformanceMetrics:
    """
    Treina ou atualiza um modelo ML para um ativo específico.
    
    Args:
        asset_id: ID do ativo
        asset_symbol: Símbolo do ativo
        timeframe: Timeframe para treinamento
        force_retrain: Se True, força o retreinamento mesmo se já houver um modelo
        
    Returns:
        Métricas de performance do modelo
    """
    model_path = get_model_path(asset_id, timeframe)
    model_exists = os.path.exists(model_path)
    
    if model_exists and not force_retrain:
        logger.info(f"Modelo já existe para {asset_symbol} ({timeframe}) e retreinamento não forçado.")
        # Carregar e retornar métricas salvas?
        # Por enquanto, apenas não treinamos
        # TODO: Carregar métricas salvas junto com o modelo ou de um registro
        return {"message": "Modelo já treinado."} # Retornar algo mais útil

    # Carregar dados de preço do Supabase
    # Aumentar lookback para ter dados suficientes para treino/teste
    price_df = load_price_data(asset_symbol=asset_symbol, timeframe=timeframe, lookback_periods=1000) 
    
    if price_df.empty or len(price_df) < 50: # Mínimo de dados para treinar
        logger.warning(f"Dados insuficientes para treinar modelo para {asset_symbol} ({timeframe}): {len(price_df)} linhas")
        return {"error": "Dados insuficientes para treinamento"}
        
    # Carregar ou criar modelo
    model = load_or_create_model(asset_id, timeframe)
    
    # Treinar o modelo
    logger.info(f"Iniciando treinamento do modelo para {asset_symbol} ({timeframe})...")
    performance_metrics = model.train(price_df)
    logger.info(f"Treinamento concluído para {asset_symbol}. Métricas: {performance_metrics}")
    
    # Salvar o modelo treinado
    model.save(model_path)
    logger.info(f"Modelo salvo em: {model_path}")
    
    # TODO: Salvar métricas no model_registry do Supabase
    # helper = SupabaseHelper()
    # await helper.upsert_model_registry({...})
    
    return performance_metrics


def generate_ml_signal(
    asset_id: str,
    asset_symbol: str,
    timeframe: str = "1d",
    lookback_periods: int = 200,
    force_retrain: bool = False,
) -> Dict[str, Any]:
    """
    Gera um sinal de ML para um ativo e timeframe.
    """
    logger.info(f"Gerando sinal ML para {asset_symbol} ({timeframe})")
    
    # Carregar ou treinar o modelo
    model_path = get_model_path(asset_id, timeframe)
    if not os.path.exists(model_path) or force_retrain:
        logger.info(f"Modelo não encontrado ou retreinamento forçado para {asset_symbol}. Treinando...")
        train_model(asset_id=asset_id, asset_symbol=asset_symbol, timeframe=timeframe, force_retrain=True)
        # Verificar se o modelo foi criado após o treinamento
        if not os.path.exists(model_path):
             logger.error(f"Falha ao treinar/criar modelo para {asset_symbol}.")
             return {"error": "Falha ao treinar modelo"}
             
    # Carregar modelo
    model = load_or_create_model(asset_id, timeframe)
    
    # Carregar dados de preço recentes do Supabase
    price_df = load_price_data(
        asset_symbol=asset_symbol, 
        timeframe=timeframe, 
        lookback_periods=lookback_periods # Usar lookback para features
    )
    
    if price_df.empty or len(price_df) < model.config.min_data_points:
        logger.warning(f"Dados recentes insuficientes para gerar sinal para {asset_symbol}: {len(price_df)} linhas")
        return {"error": f"Dados insuficientes ({len(price_df)})"}
    
    # Fazer a predição
    logger.info(f"Realizando predição para {asset_symbol}...")
    prediction_result = model.predict(price_df)
    
    if not prediction_result or 'direction' not in prediction_result:
        logger.warning(f"Predição falhou ou não retornou direção para {asset_symbol}.")
        return {"error": "Falha na predição"}
    
    # Construir o objeto Signal
    direction = SignalDirection.CALL if prediction_result['direction'] == 1 else SignalDirection.PUT
    confidence = prediction_result.get('confidence', 0.0) * 100 # Converter para %
    indicators_data = prediction_result.get('indicators', {})
    
    # Calcular validade (ex: próximo período do timeframe)
    timeframe_delta = get_timeframe_duration(timeframe)
    now = datetime.now().astimezone() # Usar timezone
    valid_until = (now + timeframe_delta).isoformat()
    generated_at = now.isoformat()

    # Obter a última data dos dados usados para gerar o sinal
    last_data_timestamp = price_df['timestamp'].iloc[-1].isoformat()
    
    # Gerar notas
    notes = generate_signal_notes(
        direction=direction,
        indicators=indicators_data, # Passar os indicadores usados
        asset_symbol=asset_symbol,
        raw_indicators= prediction_result.get('raw_indicators') # Passar indicadores crus se disponíveis
    )
    
    signal_output = {
        "asset_id": asset_id,
        "asset_symbol": asset_symbol,
        "timeframe": timeframe,
        "direction": direction.value,
        "confidence": confidence, 
        "accuracy": confidence, # Usar confidence como accuracy por enquanto
        "generated_at": generated_at,
        "valid_until": valid_until,
        "source": SignalSource.ML_MODEL.value,
        "status": SignalStatus.ACTIVE.value,
        "indicators": indicators_data, # Salvar indicadores usados
        "model_performance": model.performance_metrics, # Salvar métricas do modelo
        "notes": notes,
        # "price_target": ..., # TODO: Calcular se necessário
        # "stop_loss": ..., # TODO: Calcular se necessário
        "metadata": { # Campo genérico para info extra
             "model_type": model.config.model_type.value,
             "last_data_timestamp": last_data_timestamp,
             "lookback_used": len(price_df)
        }
    }
    
    logger.info(f"Sinal ML gerado com sucesso para {asset_symbol}: {direction.value} com {confidence:.2f}% conf.")
    
    return signal_output


def generate_signal_notes(
    direction: SignalDirection,
    indicators: IndicatorValues,
    asset_symbol: str,
    raw_indicators: Dict[str, Any] = None,
) -> str:
    """
    Gera notas explicativas para o sinal baseado nos indicadores.
    
    Args:
        direction: Direção do sinal
        indicators: Indicadores técnicos formatados
        asset_symbol: Símbolo do ativo
        raw_indicators: Indicadores brutos com valores adicionais
        
    Returns:
        String com notas explicativas
    """
    # Gerar motivos com base nos indicadores
    reasons = []
    
    # RSI
    if raw_indicators and "rsi" in raw_indicators:
        rsi = raw_indicators["rsi"]
        if direction == SignalDirection.CALL and rsi < 40:
            reasons.append(f"RSI em região de sobrevenda ({rsi:.1f})")
        elif direction == SignalDirection.PUT and rsi > 60:
            reasons.append(f"RSI em região de sobrecompra ({rsi:.1f})")
    
    # MACD
    if raw_indicators and "macd" in raw_indicators:
        macd = raw_indicators["macd"]
        if direction == SignalDirection.CALL and macd["interpretation"] == "bullish":
            reasons.append("MACD mostrando momentum positivo")
        elif direction == SignalDirection.PUT and macd["interpretation"] == "bearish":
            reasons.append("MACD mostrando momentum negativo")
    
    # SMA
    if raw_indicators and "sma" in raw_indicators:
        sma = raw_indicators["sma"]
        if direction == SignalDirection.CALL and sma["interpretation"] == "bullish":
            reasons.append("Médias móveis indicando tendência de alta")
        elif direction == SignalDirection.PUT and sma["interpretation"] == "bearish":
            reasons.append("Médias móveis indicando tendência de baixa")
    
    # Bollinger
    if raw_indicators and "bollinger" in raw_indicators:
        bb = raw_indicators["bollinger"]
        if direction == SignalDirection.CALL and bb["interpretation"] in ["oversold", "lower_band"]:
            reasons.append(f"Preço próximo à banda inferior de Bollinger ({bb['pct']:.2f})")
        elif direction == SignalDirection.PUT and bb["interpretation"] in ["overbought", "upper_band"]:
            reasons.append(f"Preço próximo à banda superior de Bollinger ({bb['pct']:.2f})")
    
    # Volume
    if raw_indicators and "volume" in raw_indicators:
        vol = raw_indicators["volume"]
        if vol["interpretation"] == "high":
            reasons.append(f"Volume acima da média ({vol['sma_ratio']:.2f}x)")
    
    # Se não temos razões específicas, adicionar uma genérica
    if not reasons:
        if direction == SignalDirection.CALL:
            reasons.append("Indicadores técnicos sugerem potencial de alta")
        elif direction == SignalDirection.PUT:
            reasons.append("Indicadores técnicos sugerem potencial de baixa")
        else:
            reasons.append("Indicadores mistos sugerem cautela")
    
    # Montar o texto final
    if direction == SignalDirection.CALL:
        note = f"Sinal de COMPRA para {asset_symbol}. "
        note += " ".join(reasons)
        note += " Considere entrada com stop abaixo do suporte recente."
    elif direction == SignalDirection.PUT:
        note = f"Sinal de VENDA para {asset_symbol}. "
        note += " ".join(reasons)
        note += " Considere entrada com stop acima da resistência recente."
    else:
        note = f"Momento de NEUTRALIDADE para {asset_symbol}. "
        note += "Indicadores mistos sugerem esperar por um sinal mais claro antes de tomar posição."
    
    return note


def batch_generate_signals(
    asset_ids: List[str],
    timeframe: str = "1d",
    force_retrain: bool = False,
) -> List[Dict[str, Any]]:
    """
    Gera sinais para vários ativos em lote.
    
    Args:
        asset_ids: Lista de IDs de ativos
        timeframe: Timeframe para análise
        force_retrain: Se True, força o retreinamento dos modelos
        
    Returns:
        Lista de sinais gerados
    """
    signals = []
    
    for asset_id in asset_ids:
        try:
            signal = generate_ml_signal(
                asset_id=asset_id,
                timeframe=timeframe,
                force_retrain=force_retrain
            )
            signals.append(signal)
            logger.info(f"Sinal gerado para {asset_id}: {signal['direction']} (confiança: {signal['confidence']:.2f})")
        except Exception as e:
            logger.error(f"Erro ao gerar sinal para {asset_id}: {e}")
    
    return signals 