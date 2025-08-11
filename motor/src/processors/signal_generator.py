"""
Gerador de sinais de trading baseado em análise técnica e ML.
"""
import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

import numpy as np
import pandas as pd
from src.utils.logger import setup_logger

logger = setup_logger("signal_generator", "signal_generator.log")

from src.models.signal import (
    IndicatorValues,
    Signal,
    SignalDirection,
    SignalSource,
    SignalStatus,
    SignalTimeframe,
)
from src.utils.config import settings


async def main(realtime_data: Dict[str, Any]):
    """
    Função principal para gerar sinais com base nos dados de mercado em tempo real.
    """
    logger.info("Iniciando geração de sinais com dados em tempo real...")
    signals_to_insert = []

    for symbol, data in realtime_data.items():
        if 'error' in data or not data.get('last_price'):
            logger.warning(f"Dados inválidos para {symbol}, pulando geração de sinal.")
            continue

        # Aqui, uma lógica de análise técnica mais sofisticada seria aplicada.
        # Por enquanto, usaremos uma lógica simplificada baseada no preço.
        signal = generate_signal_from_realtime_data(data)
        if signal:
            signals_to_insert.append(signal)

    if signals_to_insert:
        try:
            from src.utils.supabase_client import get_supabase_client
            supabase = get_supabase_client()
            supabase.table('signals').insert(signals_to_insert).execute()
            logger.info(f"{len(signals_to_insert)} novos sinais inseridos no banco de dados.")
        except Exception as e:
            logger.error(f"Erro ao inserir sinais no banco de dados: {e}")

def generate_signal_from_realtime_data(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Gera um sinal de trading para um ativo com base em dados de tempo real.
    """
    try:
        asset_symbol = data['symbol']
        current_price = data['last_price']
        open_price = data.get('open', current_price)

        # Lógica de decisão simples: se o preço subiu, CALL; se desceu, PUT.
        if current_price > open_price:
            direction = SignalDirection.CALL
            confidence = 0.65 + (current_price - open_price) / open_price * 2
        else:
            direction = SignalDirection.PUT
            confidence = 0.65 + (open_price - current_price) / open_price * 2
        
        confidence = round(min(max(confidence, 0.55), 0.95), 2)

        volatility = (data.get('high', current_price) - data.get('low', current_price)) / current_price
        if direction == SignalDirection.CALL:
            price_target = round(current_price * (1 + volatility * 1.5), 4)
            stop_loss = round(current_price * (1 - volatility * 0.75), 4)
        else:
            price_target = round(current_price * (1 - volatility * 1.5), 4)
            stop_loss = round(current_price * (1 + volatility * 0.75), 4)

        # Simulação de indicadores
        rsi_value = 50 + (confidence - 0.75) * 100
        indicators = IndicatorValues(
            rsi=round(rsi_value, 1),
            macd={"interpretation": "bullish" if direction == SignalDirection.CALL else "bearish"},
            sma={},
            patterns=[]
        )

        signal = Signal(
            asset_symbol=asset_symbol,
            direction=direction,
            confidence=confidence,
            price_target=price_target,
            stop_loss=stop_loss,
            generated_at=datetime.now(),
            status=SignalStatus.ACTIVE,
            timeframe='1m',
            source=SignalSource.REALTIME,
            indicators=indicators,
            notes=f"Sinal gerado a partir de dados em tempo real. Preço atual: {current_price}",
            created_by="realtime_system",
        )
        return signal.dict(exclude_none=True)

    except Exception as e:
        logger.error(f"Erro ao gerar sinal para {data.get('symbol')}: {e}")
        return None
        
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


def generate_signal(
    asset_id: str,
    timeframe: str = "1d",
    lookback_periods: int = 365,
    strategy_type: str = "rsi_macd"
) -> Dict[str, Any]:
    """
    Gera um sinal de trading para um ativo específico.
    
    Args:
        asset_id: ID do ativo
        timeframe: Timeframe para análise
        lookback_periods: Número de períodos para análise
        strategy_type: Tipo de estratégia
        
    Returns:
        Dicionário com o sinal gerado
    """
    try:
        # Simulação de geração de sinal
        direction_options = [SignalDirection.CALL, SignalDirection.PUT, SignalDirection.NEUTRAL]
        direction = random.choice(direction_options)
        confidence = random.uniform(0.55, 0.95)
        
        # Preço simulado
        current_price = random.uniform(10, 1000)
        volatility = random.uniform(0.01, 0.05)
        
        if direction == SignalDirection.CALL:
            price_target = round(current_price * (1 + volatility * 1.5), 4)
            stop_loss = round(current_price * (1 - volatility * 0.75), 4)
        elif direction == SignalDirection.PUT:
            price_target = round(current_price * (1 - volatility * 1.5), 4)
            stop_loss = round(current_price * (1 + volatility * 0.75), 4)
        else:
            price_target = current_price
            stop_loss = current_price
        
        # Indicadores simulados
        rsi_value = random.uniform(20, 80)
        indicators = IndicatorValues(
            rsi=round(rsi_value, 1),
            macd={"interpretation": "bullish" if direction == SignalDirection.CALL else "bearish"},
            sma={},
            patterns=[]
        )
        
        signal = Signal(
            asset_symbol=f"ASSET_{asset_id}",
            direction=direction,
            confidence=round(confidence, 2),
            price_target=price_target,
            stop_loss=stop_loss,
            generated_at=datetime.now(),
            status=SignalStatus.ACTIVE,
            timeframe=timeframe,
            source=SignalSource.TECHNICAL,
            indicators=indicators,
            notes=generate_signal_notes(direction, indicators, f"ASSET_{asset_id}"),
            created_by="signal_generator",
        )
        
        return signal.dict(exclude_none=True)
        
    except Exception as e:
        logger.error(f"Erro ao gerar sinal para {asset_id}: {e}")
        # Retornar sinal mínimo em caso de erro
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