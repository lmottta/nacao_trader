"""
Módulo de análise técnica avançada para o Motor de Sinais ML.

Fornece:
1. Cálculo de indicadores técnicos avançados
2. Identificação de padrões de candlestick
3. Análise de suporte e resistência
4. Detecção de divergências
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Union, Any
from talib import abstract as ta  # Usando TALib para indicadores
import talib as talib

from src.utils.logger import get_logger, log_execution_time


# Inicializar logger
log = get_logger("technical_analysis")


def prepare_dataframe(data: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Converte lista de dicionários de dados OHLCV em DataFrame pandas formatado para TALib.
    
    Args:
        data: Lista de dicionários com dados de preço (timestamp, open, high, low, close, volume)
        
    Returns:
        pd.DataFrame: DataFrame formatado para uso com TALib
    """
    df = pd.DataFrame(data)
    
    # Converter timestamp para datetime se necessário
    if 'timestamp' in df.columns and not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
        df['timestamp'] = pd.to_datetime(df['timestamp'])
    
    # Configurar timestamp como índice
    if 'timestamp' in df.columns:
        df.set_index('timestamp', inplace=True)
    
    # Garantir que colunas OHLCV estão presentes e são numéricas
    required_columns = ['open', 'high', 'low', 'close', 'volume']
    for col in required_columns:
        if col not in df.columns:
            log.warning(f"Coluna {col} não encontrada nos dados")
            # Adicionar coluna com zeros
            df[col] = 0
        else:
            # Converter para float
            df[col] = df[col].astype(float)
    
    return df


@log_execution_time
def calculate_all_indicators(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calcula múltiplos indicadores técnicos para os dados fornecidos.
    
    Args:
        df: DataFrame com dados OHLCV
        
    Returns:
        Dict: Dicionário com todos os indicadores calculados
    """
    if len(df) < 30:
        log.warning(f"Dados insuficientes para cálculo de indicadores: {len(df)} períodos")
        return {}
    
    result = {}
    
    try:
        # Extrair arrays para uso com TALib
        open_prices = df['open'].values
        high_prices = df['high'].values
        low_prices = df['low'].values
        close_prices = df['close'].values
        volumes = df['volume'].values
        
        # === Indicadores de Tendência ===
        # Médias Móveis
        result['sma'] = {
            'sma9': ta.SMA(df, timeperiod=9),
            'sma20': ta.SMA(df, timeperiod=20),
            'sma50': ta.SMA(df, timeperiod=50),
            'sma200': ta.SMA(df, timeperiod=200)
        }
        
        # EMA - Exponential Moving Average
        result['ema'] = {
            'ema9': ta.EMA(df, timeperiod=9),
            'ema20': ta.EMA(df, timeperiod=20),
            'ema50': ta.EMA(df, timeperiod=50)
        }
        
        # MACD
        macd, macd_signal, macd_hist = talib.MACD(
            close_prices,
            fastperiod=12,
            slowperiod=26,
            signalperiod=9
        )
        result['macd'] = {
            'macd': macd,
            'signal': macd_signal,
            'histogram': macd_hist
        }
        
        # ADX - Average Directional Index (Tendência)
        result['adx'] = ta.ADX(df, timeperiod=14)
        
        # === Indicadores de Momentum ===
        # RSI - Relative Strength Index
        result['rsi'] = ta.RSI(df, timeperiod=14)
        
        # Stochastic Oscillator
        slowk, slowd = talib.STOCH(
            high_prices,
            low_prices,
            close_prices,
            fastk_period=5,
            slowk_period=3,
            slowk_matype=0,
            slowd_period=3,
            slowd_matype=0
        )
        result['stochastic'] = {
            'k': slowk,
            'd': slowd
        }
        
        # CCI - Commodity Channel Index
        result['cci'] = ta.CCI(df, timeperiod=14)
        
        # === Indicadores de Volatilidade ===
        # Bollinger Bands
        upper, middle, lower = talib.BBANDS(
            close_prices,
            timeperiod=20,
            nbdevup=2,
            nbdevdn=2,
            matype=0
        )
        result['bbands'] = {
            'upper': upper,
            'middle': middle,
            'lower': lower,
            'width': (upper - lower) / middle
        }
        
        # ATR - Average True Range
        result['atr'] = ta.ATR(df, timeperiod=14)
        
        # === Indicadores de Volume ===
        # OBV - On Balance Volume
        result['obv'] = ta.OBV(df)
        
        # VWAP - Volume Weighted Average Price (usando SMA ponderada por volume como aproximação)
        df_vwap = df.copy()
        df_vwap['vwap'] = (df_vwap['close'] * df_vwap['volume']).cumsum() / df_vwap['volume'].cumsum()
        result['vwap'] = df_vwap['vwap'].values
        
        # ADI - Accumulation/Distribution Index
        result['ad'] = ta.AD(df)
        
        # === Indicadores personalizados adicionais ===
        # Heikin-Ashi (velas japonesas modificadas para melhor visualização de tendência)
        df_ha = df.copy()
        df_ha['ha_close'] = (df_ha['open'] + df_ha['high'] + df_ha['low'] + df_ha['close']) / 4
        df_ha['ha_open'] = df_ha['open'].copy()
        
        for i in range(1, len(df_ha)):
            df_ha.iloc[i, df_ha.columns.get_loc('ha_open')] = (
                df_ha.iloc[i-1, df_ha.columns.get_loc('ha_open')] + 
                df_ha.iloc[i-1, df_ha.columns.get_loc('ha_close')]
            ) / 2
        
        df_ha['ha_high'] = df_ha[['high', 'ha_open', 'ha_close']].max(axis=1)
        df_ha['ha_low'] = df_ha[['low', 'ha_open', 'ha_close']].min(axis=1)
        
        result['heikin_ashi'] = {
            'open': df_ha['ha_open'].values,
            'high': df_ha['ha_high'].values,
            'low': df_ha['ha_low'].values,
            'close': df_ha['ha_close'].values
        }
        
        log.debug(f"Calculados {len(result)} indicadores técnicos")
        return result
    
    except Exception as e:
        log.error(f"Erro ao calcular indicadores: {e}")
        return {}


def detect_candlestick_patterns(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Identifica padrões de candlestick nos dados.
    
    Args:
        df: DataFrame com dados OHLCV
        
    Returns:
        Dict: Dicionário com padrões de candlestick detectados
    """
    if len(df) < 10:
        log.warning(f"Dados insuficientes para detecção de padrões: {len(df)} períodos")
        return {}
    
    patterns = {}
    
    try:
        # Verificar funções de reconhecimento de padrões do TALib
        pattern_functions = {
            'doji': talib.CDLDOJI,
            'hammer': talib.CDLHAMMER,
            'hanging_man': talib.CDLHANGINGMAN,
            'engulfing': talib.CDLENGULFING,
            'morning_star': talib.CDLMORNINGSTAR,
            'evening_star': talib.CDLEVENINGSTAR,
            'three_white_soldiers': talib.CDL3WHITESOLDIERS,
            'three_black_crows': talib.CDL3BLACKCROWS
        }
        
        for pattern_name, pattern_func in pattern_functions.items():
            patterns[pattern_name] = pattern_func(
                df['open'].values,
                df['high'].values,
                df['low'].values,
                df['close'].values
            )
        
        log.debug(f"Detectados {len(patterns)} padrões de candlestick")
        return patterns
    
    except Exception as e:
        log.error(f"Erro ao detectar padrões de candlestick: {e}")
        return {}


def detect_support_resistance(df: pd.DataFrame, lookback: int = 20, threshold: float = 0.03) -> Dict[str, List[float]]:
    """
    Detecta níveis de suporte e resistência nos dados.
    
    Args:
        df: DataFrame com dados OHLCV
        lookback: Períodos para olhar para trás
        threshold: Limiar para considerar ponto como suporte/resistência
        
    Returns:
        Dict: Dicionário com níveis de suporte e resistência
    """
    if len(df) < lookback * 2:
        log.warning(f"Dados insuficientes para suporte/resistência: {len(df)} períodos")
        return {'support': [], 'resistance': []}
    
    try:
        # Identificar pivôs usando máximos e mínimos locais
        highs = df['high'].values
        lows = df['low'].values
        
        resistance_levels = []
        support_levels = []
        
        # Detectar resistências (picos)
        for i in range(lookback, len(highs) - lookback):
            if all(highs[i] > highs[i-j] for j in range(1, lookback)) and \
               all(highs[i] > highs[i+j] for j in range(1, lookback)):
                resistance_levels.append(highs[i])
        
        # Detectar suportes (vales)
        for i in range(lookback, len(lows) - lookback):
            if all(lows[i] < lows[i-j] for j in range(1, lookback)) and \
               all(lows[i] < lows[i+j] for j in range(1, lookback)):
                support_levels.append(lows[i])
        
        # Agrupar níveis próximos
        def group_levels(levels, threshold_pct):
            if not levels:
                return []
            
            levels = sorted(levels)
            grouped = []
            current_group = [levels[0]]
            
            for level in levels[1:]:
                if level > current_group[-1] * (1 + threshold_pct):
                    # Novo grupo
                    grouped.append(sum(current_group) / len(current_group))
                    current_group = [level]
                else:
                    # Adicionar ao grupo atual
                    current_group.append(level)
            
            # Adicionar o último grupo
            if current_group:
                grouped.append(sum(current_group) / len(current_group))
            
            return grouped
        
        # Agrupar níveis próximos
        grouped_resistance = group_levels(resistance_levels, threshold)
        grouped_support = group_levels(support_levels, threshold)
        
        log.debug(f"Detectados {len(grouped_support)} níveis de suporte e {len(grouped_resistance)} níveis de resistência")
        
        return {
            'support': grouped_support,
            'resistance': grouped_resistance
        }
    
    except Exception as e:
        log.error(f"Erro ao detectar suporte/resistência: {e}")
        return {'support': [], 'resistance': []}


def detect_divergence(df: pd.DataFrame, indicator: np.ndarray, lookback: int = 20) -> Dict[str, Any]:
    """
    Detecta divergências entre preço e indicador.
    
    Args:
        df: DataFrame com dados OHLCV
        indicator: Array numpy com valores do indicador
        lookback: Períodos para olhar para trás
        
    Returns:
        Dict: Dicionário com divergências detectadas
    """
    if len(df) < lookback * 2 or len(indicator) < lookback * 2:
        log.warning(f"Dados insuficientes para detecção de divergência: {len(df)} períodos")
        return {'bullish': False, 'bearish': False}
    
    try:
        prices = df['close'].values[-lookback:]
        ind_values = indicator[-lookback:]
        
        # Detectar divergência positiva (preço com mínimos mais baixos, indicador com mínimos mais altos)
        price_making_lower_lows = np.min(prices[:lookback//2]) > np.min(prices[lookback//2:])
        indicator_making_higher_lows = np.min(ind_values[:lookback//2]) < np.min(ind_values[lookback//2:])
        bullish_divergence = price_making_lower_lows and indicator_making_higher_lows
        
        # Detectar divergência negativa (preço com máximos mais altos, indicador com máximos mais baixos)
        price_making_higher_highs = np.max(prices[:lookback//2]) < np.max(prices[lookback//2:])
        indicator_making_lower_highs = np.max(ind_values[:lookback//2]) > np.max(ind_values[lookback//2:])
        bearish_divergence = price_making_higher_highs and indicator_making_lower_highs
        
        log.debug(f"Divergência: bullish={bullish_divergence}, bearish={bearish_divergence}")
        
        return {
            'bullish': bullish_divergence,
            'bearish': bearish_divergence
        }
    
    except Exception as e:
        log.error(f"Erro ao detectar divergência: {e}")
        return {'bullish': False, 'bearish': False}


@log_execution_time
def analyze_market_structure(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Analisa a estrutura de mercado, identificando rompimentos, tendências, etc.
    
    Args:
        df: DataFrame com dados OHLCV
        
    Returns:
        Dict: Dicionário com análise da estrutura de mercado
    """
    if len(df) < 50:
        log.warning(f"Dados insuficientes para análise de estrutura: {len(df)} períodos")
        return {}
    
    try:
        # Extrair preços
        close_prices = df['close'].values
        
        # Calcular médias móveis para determinar tendência
        sma20 = talib.SMA(close_prices, timeperiod=20)
        sma50 = talib.SMA(close_prices, timeperiod=50)
        
        # Determinar tendência atual
        current_sma20 = sma20[-1]
        current_sma50 = sma50[-1]
        prev_sma20 = sma20[-2]
        prev_sma50 = sma50[-2]
        
        # Validar se há médias para comparar
        if np.isnan(current_sma20) or np.isnan(current_sma50) or \
           np.isnan(prev_sma20) or np.isnan(prev_sma50):
            trend = "neutral"
            trend_strength = 0
        else:
            # Lógica de tendência com cruzamentos de médias
            if current_sma20 > current_sma50:
                trend = "bullish"
                crossing_up = prev_sma20 <= prev_sma50 and current_sma20 > current_sma50
                trend_strength = 2 if crossing_up else 1
            elif current_sma20 < current_sma50:
                trend = "bearish"
                crossing_down = prev_sma20 >= prev_sma50 and current_sma20 < current_sma50
                trend_strength = 2 if crossing_down else 1
            else:
                trend = "neutral"
                trend_strength = 0
        
        # Verificar se o preço rompeu médias importantes
        current_price = close_prices[-1]
        previous_price = close_prices[-2]
        
        # Identificar rompimentos
        breakout = None
        if previous_price < current_sma20 and current_price > current_sma20:
            breakout = "sma20_up"
        elif previous_price > current_sma20 and current_price < current_sma20:
            breakout = "sma20_down"
        elif previous_price < current_sma50 and current_price > current_sma50:
            breakout = "sma50_up"
        elif previous_price > current_sma50 and current_price < current_sma50:
            breakout = "sma50_down"
        
        # Detectar estrutura de suporte e resistência
        sr_levels = detect_support_resistance(df)
        
        # Verificar proximidade a suportes/resistências
        close_to_support = any(abs(current_price - level) / current_price < 0.02 for level in sr_levels['support'])
        close_to_resistance = any(abs(current_price - level) / current_price < 0.02 for level in sr_levels['resistance'])
        
        # Calcular ADX para força da tendência
        adx = talib.ADX(
            df['high'].values,
            df['low'].values,
            df['close'].values,
            timeperiod=14
        )
        current_adx = adx[-1] if not np.isnan(adx[-1]) else 0
        
        # Construir resultado
        result = {
            'trend': trend,
            'trend_strength': trend_strength,
            'adx': current_adx,
            'trend_strength_desc': 'strong' if current_adx > 25 else 'weak',
            'breakout': breakout,
            'close_to_support': close_to_support,
            'close_to_resistance': close_to_resistance,
            'support_levels': sr_levels['support'],
            'resistance_levels': sr_levels['resistance']
        }
        
        log.debug(f"Análise de estrutura de mercado: tendência {trend}, força {current_adx}")
        return result
    
    except Exception as e:
        log.error(f"Erro ao analisar estrutura de mercado: {e}")
        return {}


@log_execution_time
def perform_technical_analysis(price_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Executa análise técnica completa em dados de preço.
    
    Args:
        price_data: Lista de dicionários com dados OHLCV
        
    Returns:
        Dict: Análise técnica completa
    """
    log.info(f"Iniciando análise técnica em {len(price_data)} registros")
    
    # Preparar DataFrame
    df = prepare_dataframe(price_data)
    
    if len(df) < 30:
        log.warning(f"Dados insuficientes para análise técnica: {len(df)} registros")
        return {"error": "Dados insuficientes para análise técnica"}
    
    try:
        # Executar análises
        indicators = calculate_all_indicators(df)
        patterns = detect_candlestick_patterns(df)
        market_structure = analyze_market_structure(df)
        
        # Gerar alerta baseado em RSI
        rsi_value = indicators['rsi'][-1] if 'rsi' in indicators and len(indicators['rsi']) > 0 else None
        rsi_alert = None
        if rsi_value is not None:
            if rsi_value < 30:
                rsi_alert = "oversold"
            elif rsi_value > 70:
                rsi_alert = "overbought"
        
        # Verificar divergências
        divergences = {}
        if 'rsi' in indicators:
            divergences['rsi'] = detect_divergence(df, indicators['rsi'])
        if 'macd' in indicators and 'histogram' in indicators['macd']:
            divergences['macd'] = detect_divergence(df, indicators['macd']['histogram'])
        
        # Consolidar resultados
        result = {
            'timestamp': df.index[-1].isoformat() if isinstance(df.index[-1], pd.Timestamp) else str(df.index[-1]),
            'indicators': {
                'current': {
                    'rsi': float(indicators['rsi'][-1]) if 'rsi' in indicators and len(indicators['rsi']) > 0 else None,
                    'macd': {
                        'value': float(indicators['macd']['macd'][-1]) if 'macd' in indicators else None,
                        'signal': float(indicators['macd']['signal'][-1]) if 'macd' in indicators else None,
                        'histogram': float(indicators['macd']['histogram'][-1]) if 'macd' in indicators else None,
                    },
                    'bbands': {
                        'upper': float(indicators['bbands']['upper'][-1]) if 'bbands' in indicators else None,
                        'middle': float(indicators['bbands']['middle'][-1]) if 'bbands' in indicators else None,
                        'lower': float(indicators['bbands']['lower'][-1]) if 'bbands' in indicators else None,
                    },
                    'adx': float(indicators['adx'][-1]) if 'adx' in indicators and len(indicators['adx']) > 0 else None,
                    'cci': float(indicators['cci'][-1]) if 'cci' in indicators and len(indicators['cci']) > 0 else None,
                    'stochastic': {
                        'k': float(indicators['stochastic']['k'][-1]) if 'stochastic' in indicators else None,
                        'd': float(indicators['stochastic']['d'][-1]) if 'stochastic' in indicators else None,
                    }
                }
            },
            'patterns': {
                name: int(pattern[-1]) for name, pattern in patterns.items() if len(pattern) > 0
            },
            'market_structure': market_structure,
            'divergences': divergences,
            'alerts': {
                'rsi': rsi_alert
            }
        }
        
        # Gerar recomendação geral
        buy_signals = 0
        sell_signals = 0
        total_signals = 0
        
        # Sinais de RSI
        if rsi_alert == "oversold":
            buy_signals += 1
        elif rsi_alert == "overbought":
            sell_signals += 1
        total_signals += 1
        
        # Sinais de MACD
        if 'macd' in indicators and len(indicators['macd']['histogram']) > 1:
            macd_hist = indicators['macd']['histogram']
            if macd_hist[-2] < 0 and macd_hist[-1] > 0:  # Cruzamento para cima
                buy_signals += 1
            elif macd_hist[-2] > 0 and macd_hist[-1] < 0:  # Cruzamento para baixo
                sell_signals += 1
            total_signals += 1
        
        # Sinais de tendência
        if 'trend' in market_structure:
            if market_structure['trend'] == 'bullish':
                buy_signals += 1
            elif market_structure['trend'] == 'bearish':
                sell_signals += 1
            total_signals += 1
        
        # Sinais de padrões de candlestick
        for name, value in result['patterns'].items():
            if value > 0:  # Padrão bullish
                buy_signals += 1
            elif value < 0:  # Padrão bearish
                sell_signals += 1
            total_signals += 1
        
        # Gerar recomendação
        if total_signals > 0:
            buy_strength = buy_signals / total_signals
            sell_strength = sell_signals / total_signals
            
            if buy_strength > sell_strength and buy_strength > 0.6:
                recommendation = 'strong_buy'
            elif buy_strength > sell_strength:
                recommendation = 'buy'
            elif sell_strength > buy_strength and sell_strength > 0.6:
                recommendation = 'strong_sell'
            elif sell_strength > buy_strength:
                recommendation = 'sell'
            else:
                recommendation = 'neutral'
        else:
            recommendation = 'neutral'
        
        result['recommendation'] = {
            'action': recommendation,
            'buy_signals': buy_signals,
            'sell_signals': sell_signals,
            'total_signals': total_signals
        }
        
        log.info(f"Análise técnica concluída com recomendação: {recommendation}")
        return result
    
    except Exception as e:
        log.error(f"Erro ao realizar análise técnica: {e}")
        return {"error": f"Erro durante análise técnica: {str(e)}"} 