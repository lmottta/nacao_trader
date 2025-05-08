"""
Gerador de sinais de trading baseado em análise técnica e ML.
"""
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd
from loguru import logger

from src.models.signal import (
    IndicatorValues,
    Signal,
    SignalDirection,
    SignalSource,
    SignalStatus,
    SignalTimeframe,
)
from src.utils.config import settings


def generate_signal(
    asset_id: str,
    timeframe: str = "1d",
    lookback_periods: int = 100,
) -> Dict[str, Any]:
    """
    Gera um sinal de trading para um ativo específico.
    
    Esta é uma implementação inicial que simula a geração de sinais.
    Posteriormente, será substituída por uma implementação real
    utilizando modelos de ML e análise técnica.
    
    Args:
        asset_id: ID do ativo
        timeframe: Timeframe para análise (1m, 5m, 15m, 1h, 4h, 1d, 1w)
        lookback_periods: Número de períodos para análise retroativa
        
    Returns:
        Dicionário contendo o sinal gerado
    """
    try:
        # Simulação: em uma implementação real, buscaríamos os dados do ativo
        # Para simulação, geramos dados aleatórios que parecem razoáveis
        asset_symbol = f"ASSET_{asset_id}"  # Em uma implementação real, buscaríamos do banco
        
        # Gerar direção aleatória com maior tendência para CALL (otimismo do mercado)
        direction_weights = [0.55, 0.40, 0.05]  # CALL, PUT, NEUTRAL
        direction = random.choices(
            [SignalDirection.CALL, SignalDirection.PUT, SignalDirection.NEUTRAL],
            weights=direction_weights,
            k=1
        )[0]
        
        # Gerar confiança com base na direção
        if direction == SignalDirection.CALL:
            confidence = random.uniform(0.65, 0.95)
        elif direction == SignalDirection.PUT:
            confidence = random.uniform(0.60, 0.90)
        else:
            confidence = random.uniform(0.40, 0.60)
        
        # Arredondar confiança para 2 casas decimais
        confidence = round(confidence, 2)
        
        # Definir preço atual simulado
        current_price = round(random.uniform(50, 500), 2)
        
        # Calcular price_target e stop_loss com base na direção e volatilidade simulada
        volatility = random.uniform(0.02, 0.08)  # 2-8% de volatilidade
        
        if direction == SignalDirection.CALL:
            price_target = round(current_price * (1 + volatility * 2), 2)
            stop_loss = round(current_price * (1 - volatility), 2)
        elif direction == SignalDirection.PUT:
            price_target = round(current_price * (1 - volatility * 2), 2)
            stop_loss = round(current_price * (1 + volatility), 2)
        else:
            price_target = None
            stop_loss = None
        
        # Gerar indicadores técnicos simulados
        rsi_value = 30.0 if direction == SignalDirection.CALL else 70.0 if direction == SignalDirection.PUT else 50.0
        rsi_value += random.uniform(-10, 10)  # Adicionar ruído
        rsi_value = min(max(rsi_value, 0), 100)  # Garantir que está entre 0-100
        
        macd_interpretation = "bullish" if direction == SignalDirection.CALL else "bearish" if direction == SignalDirection.PUT else "neutral"
        
        sma_50 = current_price * (0.95 if direction == SignalDirection.CALL else 1.05 if direction == SignalDirection.PUT else 1.0)
        sma_200 = current_price * (0.90 if direction == SignalDirection.CALL else 1.10 if direction == SignalDirection.PUT else 1.0)
        
        indicators = IndicatorValues(
            rsi=round(rsi_value, 1),
            macd={
                "value": round(random.uniform(-2, 2), 2),
                "signal": round(random.uniform(-1, 1), 2),
                "histogram": round(random.uniform(-1, 1), 2),
                "interpretation": macd_interpretation,
            },
            sma={
                "sma_50": round(sma_50, 2),
                "sma_200": round(sma_200, 2),
                "interpretation": macd_interpretation,
            },
            patterns=[
                random.choice(["doji", "hammer", "engulfing"]) 
                for _ in range(random.randint(0, 2))
            ],
        )
        
        # Determine signal source based on confidence
        if confidence > 0.85:
            source = SignalSource.ENSEMBLE
        elif confidence > 0.75:
            source = SignalSource.ML_ADVANCED
        elif confidence > 0.65:
            source = SignalSource.ML_BASIC
        else:
            source = SignalSource.TECHNICAL
        
        # Create signal object
        signal = Signal(
            id=None,  # will be assigned by database
            asset_id=asset_id,
            asset_symbol=asset_symbol,
            direction=direction,
            confidence=confidence,
            price_target=price_target,
            stop_loss=stop_loss,
            generated_at=datetime.now(),
            valid_until=None,  # will be calculated by validator
            status=SignalStatus.ACTIVE,
            timeframe=timeframe,
            source=source,
            indicators=indicators,
            notes=generate_signal_notes(direction, indicators, asset_symbol),
            created_by="system",
        )
        
        # Convert to dict (auto-calculates valid_until via validator)
        return signal.dict()
        
    except Exception as e:
        logger.error(f"Erro ao gerar sinal: {e}")
        # Return a minimal valid signal in case of error
        return {
            "asset_id": asset_id,
            "asset_symbol": f"ASSET_{asset_id}",
            "direction": "NEUTRAL",
            "confidence": 0.5,
            "generated_at": datetime.now().isoformat(),
            "valid_until": (datetime.now() + timedelta(days=1)).isoformat(),
            "status": "active",
            "timeframe": timeframe,
            "source": "technical",
        }


def generate_signal_notes(
    direction: SignalDirection,
    indicators: IndicatorValues,
    asset_symbol: str,
) -> str:
    """
    Gera notas explicativas para o sinal.
    
    Args:
        direction: Direção do sinal
        indicators: Indicadores técnicos
        asset_symbol: Símbolo do ativo
        
    Returns:
        String com notas explicativas
    """
    if direction == SignalDirection.CALL:
        return f"Sinal de COMPRA para {asset_symbol}. RSI em região de sobrevenda ({indicators.rsi}), " \
               f"MACD mostrando momentum positivo e tendência de alta confirmada pelo cruzamento das médias móveis."
    elif direction == SignalDirection.PUT:
        return f"Sinal de VENDA para {asset_symbol}. RSI em região de sobrecompra ({indicators.rsi}), " \
               f"MACD mostrando momentum negativo e tendência de baixa confirmada pelo cruzamento das médias móveis."
    else:
        return f"Momento de neutralidade para {asset_symbol}. Indicadores mistos sugerem esperar por um sinal mais claro " \
               f"antes de tomar posição."


def backtest_signal_strategy(
    asset_id: str,
    strategy_type: str = "rsi_macd",
    timeframe: str = "1d",
    lookback_periods: int = 365,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Função para backtesting de estratégias de trading.
    Esta é uma implementação de exemplo que seria expandida com dados reais.
    
    Args:
        asset_id: ID do ativo
        strategy_type: Tipo de estratégia
        timeframe: Timeframe para análise
        lookback_periods: Número de períodos para análise
        start_date: Data de início do backtest
        end_date: Data de fim do backtest
        
    Returns:
        Resultados do backtest
    """
    # Implementação simulada
    signals_count = random.randint(10, 50)
    win_rate = random.uniform(0.51, 0.75)
    wins = int(signals_count * win_rate)
    losses = signals_count - wins
    
    avg_profit = random.uniform(1.5, 3.0)
    avg_loss = random.uniform(0.8, 1.0)
    
    profit_factor = (wins * avg_profit) / (losses * avg_loss) if losses > 0 else float('inf')
    sharpe_ratio = random.uniform(0.8, 2.5)
    max_drawdown = random.uniform(5, 30)
    
    return {
        "asset_id": asset_id,
        "strategy": strategy_type,
        "timeframe": timeframe,
        "period": f"{lookback_periods} periods",
        "signals_generated": signals_count,
        "win_rate": round(win_rate * 100, 2),
        "total_signals": signals_count,
        "winning_signals": wins,
        "losing_signals": losses,
        "avg_profit_per_win": round(avg_profit, 2),
        "avg_loss_per_loss": round(avg_loss, 2),
        "profit_factor": round(profit_factor, 2),
        "sharpe_ratio": round(sharpe_ratio, 2),
        "max_drawdown": round(max_drawdown, 2),
        "expected_return": round((win_rate * avg_profit) - ((1 - win_rate) * avg_loss), 2),
    } 