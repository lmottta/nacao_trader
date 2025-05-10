"""
Utilitário para normalização de formatos de indicadores técnicos.
Garante que os indicadores técnicos tenham um formato consistente antes
de serem salvos no banco de dados ou enviados para o frontend.
"""

from typing import Dict, Any, Optional, Union, List
import logging

logger = logging.getLogger(__name__)

def normalize_rsi(rsi_value: Any) -> Optional[float]:
    """
    Normaliza o valor do RSI para um float entre 0-100 ou None se inválido.
    
    Args:
        rsi_value: Valor do RSI que pode estar em diferentes formatos
        
    Returns:
        float: Valor do RSI normalizado ou None se inválido
    """
    if rsi_value is None:
        return None
    
    try:
        if isinstance(rsi_value, str):
            rsi_value = float(rsi_value)
        
        # Verificar se está em escala 0-1 e converter para 0-100
        if 0 <= rsi_value <= 1:
            rsi_value = rsi_value * 100
            
        # Garantir que está dentro dos limites
        rsi_value = max(0, min(100, rsi_value))
        
        return float(rsi_value)
    except (ValueError, TypeError) as e:
        logger.warning(f"Erro ao normalizar RSI: {e}. Valor original: {rsi_value}")
        return None

def normalize_macd(macd_data: Any) -> Dict[str, Any]:
    """
    Normaliza o objeto MACD para um formato padrão.
    
    Args:
        macd_data: Objeto MACD em qualquer formato
        
    Returns:
        dict: Objeto MACD normalizado
    """
    # Estrutura padrão para MACD
    normalized = {
        "value": None,  # Linha MACD
        "signal": None, # Linha de Sinal
        "histogram": None, # Histograma (diferença)
        "trend": None,  # 'bullish' ou 'bearish'
        "crossover": None # 'bullish', 'bearish' ou 'none'
    }
    
    # Se for None ou não for um dicionário, retornar estrutura padrão vazia
    if not macd_data or not isinstance(macd_data, dict):
        return normalized
    
    try:
        # Extrair valor principal (pode estar como 'value' ou 'MACD')
        if "value" in macd_data and macd_data["value"] is not None:
            try:
                normalized["value"] = float(macd_data["value"])
            except (ValueError, TypeError):
                normalized["value"] = None
        elif "MACD" in macd_data and macd_data["MACD"] is not None:
            try:
                normalized["value"] = float(macd_data["MACD"])
            except (ValueError, TypeError):
                normalized["value"] = None
        
        # Extrair sinal
        if "signal" in macd_data and macd_data["signal"] is not None:
            try:
                normalized["signal"] = float(macd_data["signal"])
            except (ValueError, TypeError):
                normalized["signal"] = None
        
        # Extrair histograma
        if "histogram" in macd_data and macd_data["histogram"] is not None:
            try:
                normalized["histogram"] = float(macd_data["histogram"])
            except (ValueError, TypeError):
                normalized["histogram"] = None
        elif normalized["value"] is not None and normalized["signal"] is not None:
            # Calcular histograma se não fornecido
            normalized["histogram"] = normalized["value"] - normalized["signal"]
        
        # Preservar trend e crossover se existirem
        if "trend" in macd_data:
            normalized["trend"] = str(macd_data["trend"])
        elif normalized["histogram"] is not None:
            # Determinar tendência com base no histograma
            normalized["trend"] = "bullish" if normalized["histogram"] > 0 else "bearish"
        
        if "crossover" in macd_data:
            normalized["crossover"] = str(macd_data["crossover"])
        
        return normalized
    except Exception as e:
        logger.warning(f"Erro ao normalizar MACD: {e}. Dados originais: {macd_data}")
        return normalized

def normalize_bollinger(bollinger_data: Any) -> Dict[str, Any]:
    """
    Normaliza o objeto Bollinger Bands para um formato padrão.
    
    Args:
        bollinger_data: Objeto Bollinger em qualquer formato (pode ser 'bollinger' ou 'bbands')
        
    Returns:
        dict: Objeto Bollinger normalizado
    """
    # Estrutura padrão para Bollinger Bands
    normalized = {
        "upper": None,  # Banda superior
        "middle": None, # Banda média (SMA)
        "lower": None,  # Banda inferior
        "width": None,  # Largura relativa
        "percentB": None # Posição relativa do preço entre bandas
    }
    
    # Se for None ou não for um dicionário, retornar estrutura padrão vazia
    if not bollinger_data or not isinstance(bollinger_data, dict):
        return normalized
    
    try:
        # Extrair valores das bandas
        for band in ["upper", "middle", "lower"]:
            if band in bollinger_data and bollinger_data[band] is not None:
                try:
                    normalized[band] = float(bollinger_data[band])
                except (ValueError, TypeError):
                    normalized[band] = None
        
        # Preservar width e percentB
        if "width" in bollinger_data and bollinger_data["width"] is not None:
            try:
                normalized["width"] = float(bollinger_data["width"])
            except (ValueError, TypeError):
                normalized["width"] = None
        elif normalized["upper"] is not None and normalized["middle"] is not None and normalized["middle"] != 0:
            # Calcular width se não fornecida
            normalized["width"] = (normalized["upper"] - normalized["lower"]) / normalized["middle"]
        
        if "percentB" in bollinger_data and bollinger_data["percentB"] is not None:
            try:
                normalized["percentB"] = float(bollinger_data["percentB"])
            except (ValueError, TypeError):
                normalized["percentB"] = None
        
        return normalized
    except Exception as e:
        logger.warning(f"Erro ao normalizar Bollinger Bands: {e}. Dados originais: {bollinger_data}")
        return normalized

def normalize_indicators(indicators: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normaliza um conjunto completo de indicadores técnicos.
    
    Args:
        indicators: Dicionário com diversos indicadores
        
    Returns:
        dict: Indicadores normalizados
    """
    if not indicators or not isinstance(indicators, dict):
        return {}
    
    normalized = {}
    
    # Copiar indicadores não tratados especificamente
    for key, value in indicators.items():
        normalized[key] = value
    
    # Normalizar RSI
    if "rsi" in indicators:
        normalized["rsi"] = normalize_rsi(indicators["rsi"])
    
    # Normalizar MACD
    if "macd" in indicators:
        normalized["macd"] = normalize_macd(indicators["macd"])
    
    # Normalizar Bollinger (pode aparecer como bollinger ou bbands)
    if "bollinger" in indicators:
        normalized["bollinger"] = normalize_bollinger(indicators["bollinger"])
    elif "bbands" in indicators:
        normalized["bollinger"] = normalize_bollinger(indicators["bbands"])
        # Remover a versão antiga se estiver presente
        if "bbands" in normalized:
            del normalized["bbands"]
    
    return normalized 