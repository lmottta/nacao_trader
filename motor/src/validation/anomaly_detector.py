from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone, timedelta
from enum import Enum
from dataclasses import dataclass, field
import asyncio
import logging
import statistics
import math
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class AnomalyType(Enum):
    """Tipos de anomalias detectáveis."""
    STATISTICAL_OUTLIER = "statistical_outlier"    # Outlier estatístico
    VOLATILITY_SPIKE = "volatility_spike"          # Pico de volatilidade
    VOLUME_ANOMALY = "volume_anomaly"              # Anomalia de volume
    PRICE_GAP = "price_gap"                        # Gap de preço
    CORRELATION_BREAK = "correlation_break"        # Quebra de correlação
    TEMPORAL_INCONSISTENCY = "temporal_inconsistency"  # Inconsistência temporal

class AnomalySeverity(Enum):
    """Severidade das anomalias."""
    LOW = "low"                    # Baixa severidade
    MEDIUM = "medium"              # Média severidade
    HIGH = "high"                  # Alta severidade
    CRITICAL = "critical"          # Severidade crítica

@dataclass
class AnomalyResult:
    """Resultado de detecção de anomalia."""
    type: AnomalyType                        # Tipo da anomalia
    severity: AnomalySeverity                # Severidade
    confidence: float                        # Confiança na detecção (0-1)
    description: str                         # Descrição da anomalia
    affected_field: str = None               # Campo afetado
    current_value: Any = None                # Valor atual
    expected_range: tuple = None             # Faixa esperada (min, max)
    statistical_score: float = None          # Score estatístico
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    context: Dict[str, Any] = field(default_factory=dict)  # Contexto adicional
    recommendations: List[str] = field(default_factory=list)  # Recomendações
    
    def add_recommendation(self, recommendation: str):
        """Adiciona uma recomendação."""
        if recommendation not in self.recommendations:
            self.recommendations.append(recommendation)
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        return {
            'type': self.type.value,
            'severity': self.severity.value,
            'confidence': self.confidence,
            'description': self.description,
            'affected_field': self.affected_field,
            'current_value': self.current_value,
            'expected_range': self.expected_range,
            'statistical_score': self.statistical_score,
            'timestamp': self.timestamp.isoformat(),
            'context': self.context,
            'recommendations': self.recommendations
        }

@dataclass
class AnomalyDetectionConfig:
    """Configuração para detecção de anomalias."""
    # Configurações gerais
    confidence_threshold: float = 0.7        # Threshold mínimo de confiança
    max_anomalies_per_check: int = 10        # Máximo de anomalias por verificação
    
    # Configurações estatísticas
    z_score_threshold: float = 3.0           # Threshold para Z-score
    mad_threshold: float = 3.0               # Threshold para MAD (Median Absolute Deviation)
    min_historical_points: int = 30          # Mínimo de pontos históricos
    
    # Configurações de volatilidade
    volatility_threshold: float = 2.0        # Threshold para picos de volatilidade
    volatility_window: int = 20              # Janela para cálculo de volatilidade
    
    # Configurações de volume
    volume_spike_threshold: float = 3.0      # Threshold para picos de volume
    volume_drop_threshold: float = 0.3       # Threshold para quedas de volume
    
    # Configurações temporais
    max_time_gap_minutes: int = 60           # Gap máximo entre dados (minutos)
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        return {
            'confidence_threshold': self.confidence_threshold,
            'max_anomalies_per_check': self.max_anomalies_per_check,
            'z_score_threshold': self.z_score_threshold,
            'mad_threshold': self.mad_threshold,
            'min_historical_points': self.min_historical_points,
            'volatility_threshold': self.volatility_threshold,
            'volatility_window': self.volatility_window,
            'volume_spike_threshold': self.volume_spike_threshold,
            'volume_drop_threshold': self.volume_drop_threshold,
            'max_time_gap_minutes': self.max_time_gap_minutes
        }

class AnomalyDetector(ABC):
    """Classe base para detectores de anomalia."""
    
    def __init__(self, name: str):
        self.name = name
        self.enabled = True
    
    @abstractmethod
    async def detect(self, current_data: Any, historical_data: List[Any], 
                    config: AnomalyDetectionConfig) -> List[AnomalyResult]:
        """Detecta anomalias nos dados."""
        pass
    
    def is_applicable(self, data_type: str) -> bool:
        """Verifica se o detector se aplica ao tipo de dados."""
        return True
    
    def _extract_numeric_value(self, data: Any, field: str) -> Optional[float]:
        """Extrai valor numérico dos dados."""
        if isinstance(data, (int, float)):
            return float(data)
        
        if isinstance(data, dict) and field in data:
            value = data[field]
            if isinstance(value, (int, float)):
                return float(value)
            
            if isinstance(value, str):
                try:
                    return float(value.replace(',', '').replace('%', ''))
                except ValueError:
                    return None
        
        return None
    
    def _calculate_z_score(self, value: float, historical_values: List[float]) -> float:
        """Calcula Z-score."""
        if len(historical_values) < 2:
            return 0.0
        
        mean = statistics.mean(historical_values)
        stdev = statistics.stdev(historical_values)
        
        if stdev == 0:
            return 0.0
        
        return abs(value - mean) / stdev
    
    def _calculate_mad_score(self, value: float, historical_values: List[float]) -> float:
        """Calcula MAD score (Median Absolute Deviation)."""
        if len(historical_values) < 2:
            return 0.0
        
        median = statistics.median(historical_values)
        deviations = [abs(x - median) for x in historical_values]
        mad = statistics.median(deviations)
        
        if mad == 0:
            return 0.0
        
        return abs(value - median) / mad

class StatisticalOutlierDetector(AnomalyDetector):
    """Detector de outliers estatísticos."""
    
    def __init__(self):
        super().__init__("statistical_outlier")
    
    async def detect(self, current_data: Any, historical_data: List[Any], 
                    config: AnomalyDetectionConfig) -> List[AnomalyResult]:
        anomalies = []
        
        if len(historical_data) < config.min_historical_points:
            return anomalies
        
        # Campos numéricos para verificar
        numeric_fields = ['price', 'volume', 'close', 'open', 'high', 'low']
        
        for field in numeric_fields:
            current_value = self._extract_numeric_value(current_data, field)
            if current_value is None:
                continue
            
            # Extrair valores históricos
            historical_values = []
            for data in historical_data:
                value = self._extract_numeric_value(data, field)
                if value is not None:
                    historical_values.append(value)
            
            if len(historical_values) < config.min_historical_points:
                continue
            
            # Calcular scores
            z_score = self._calculate_z_score(current_value, historical_values)
            mad_score = self._calculate_mad_score(current_value, historical_values)
            
            # Verificar se é outlier
            is_z_outlier = z_score > config.z_score_threshold
            is_mad_outlier = mad_score > config.mad_threshold
            
            if is_z_outlier or is_mad_outlier:
                # Determinar severidade
                max_score = max(z_score, mad_score)
                if max_score > 5.0:
                    severity = AnomalySeverity.CRITICAL
                    confidence = 0.95
                elif max_score > 4.0:
                    severity = AnomalySeverity.HIGH
                    confidence = 0.9
                elif max_score > 3.0:
                    severity = AnomalySeverity.MEDIUM
                    confidence = 0.8
                else:
                    severity = AnomalySeverity.LOW
                    confidence = 0.7
                
                if confidence >= config.confidence_threshold:
                    # Calcular faixa esperada
                    mean = statistics.mean(historical_values)
                    stdev = statistics.stdev(historical_values)
                    expected_range = (mean - 2*stdev, mean + 2*stdev)
                    
                    anomaly = AnomalyResult(
                        type=AnomalyType.STATISTICAL_OUTLIER,
                        severity=severity,
                        confidence=confidence,
                        description=f"Outlier estatístico detectado em {field}: {current_value}",
                        affected_field=field,
                        current_value=current_value,
                        expected_range=expected_range,
                        statistical_score=max(z_score, mad_score),
                        context={
                            "z_score": z_score,
                            "mad_score": mad_score,
                            "historical_mean": mean,
                            "historical_stdev": stdev
                        }
                    )
                    
                    # Adicionar recomendações
                    if severity in [AnomalySeverity.HIGH, AnomalySeverity.CRITICAL]:
                        anomaly.add_recommendation("Verificar fonte de dados imediatamente")
                        anomaly.add_recommendation("Considerar suspender uso temporário dos dados")
                    else:
                        anomaly.add_recommendation("Monitorar próximas atualizações")
                        anomaly.add_recommendation("Verificar se há eventos de mercado relevantes")
                    
                    anomalies.append(anomaly)
        
        return anomalies

class VolatilityAnomalyDetector(AnomalyDetector):
    """Detector de anomalias de volatilidade."""
    
    def __init__(self):
        super().__init__("volatility_anomaly")
    
    async def detect(self, current_data: Any, historical_data: List[Any], 
                    config: AnomalyDetectionConfig) -> List[AnomalyResult]:
        anomalies = []
        
        if len(historical_data) < config.volatility_window:
            return anomalies
        
        # Extrair preços históricos
        prices = []
        for data in historical_data[-config.volatility_window:]:
            price = self._extract_numeric_value(data, 'price')
            if price is not None:
                prices.append(price)
        
        current_price = self._extract_numeric_value(current_data, 'price')
        if current_price is None or len(prices) < config.volatility_window:
            return anomalies
        
        # Calcular retornos históricos
        returns = []
        for i in range(1, len(prices)):
            if prices[i-1] != 0:
                ret = (prices[i] - prices[i-1]) / prices[i-1]
                returns.append(ret)
        
        if len(returns) < 10:
            return anomalies
        
        # Calcular volatilidade histórica
        historical_volatility = statistics.stdev(returns)
        
        # Calcular retorno atual
        if len(prices) > 0 and prices[-1] != 0:
            current_return = abs((current_price - prices[-1]) / prices[-1])
            
            # Verificar se é um pico de volatilidade
            if historical_volatility > 0:
                volatility_ratio = current_return / historical_volatility
                
                if volatility_ratio > config.volatility_threshold:
                    # Determinar severidade
                    if volatility_ratio > 5.0:
                        severity = AnomalySeverity.CRITICAL
                        confidence = 0.9
                    elif volatility_ratio > 3.0:
                        severity = AnomalySeverity.HIGH
                        confidence = 0.8
                    elif volatility_ratio > 2.0:
                        severity = AnomalySeverity.MEDIUM
                        confidence = 0.7
                    else:
                        severity = AnomalySeverity.LOW
                        confidence = 0.6
                    
                    if confidence >= config.confidence_threshold:
                        anomaly = AnomalyResult(
                            type=AnomalyType.VOLATILITY_SPIKE,
                            severity=severity,
                            confidence=confidence,
                            description=f"Pico de volatilidade detectado: {volatility_ratio:.2f}x normal",
                            affected_field="price",
                            current_value=current_return,
                            context={
                                "volatility_ratio": volatility_ratio,
                                "historical_volatility": historical_volatility,
                                "current_return": current_return,
                                "price_change_percent": current_return * 100
                            }
                        )
                        
                        # Adicionar recomendações
                        if severity == AnomalySeverity.CRITICAL:
                            anomaly.add_recommendation("Possível evento de mercado significativo")
                            anomaly.add_recommendation("Verificar notícias e comunicados")
                        else:
                            anomaly.add_recommendation("Monitorar movimentos subsequentes")
                            anomaly.add_recommendation("Verificar volume de negociação")
                        
                        anomalies.append(anomaly)
        
        return anomalies

class VolumeAnomalyDetector(AnomalyDetector):
    """Detector de anomalias de volume."""
    
    def __init__(self):
        super().__init__("volume_anomaly")
    
    def is_applicable(self, data_type: str) -> bool:
        return data_type in ['ticker', 'ohlcv', 'market_data']
    
    async def detect(self, current_data: Any, historical_data: List[Any], 
                    config: AnomalyDetectionConfig) -> List[AnomalyResult]:
        anomalies = []
        
        current_volume = self._extract_numeric_value(current_data, 'volume')
        if current_volume is None:
            return anomalies
        
        # Extrair volumes históricos
        historical_volumes = []
        for data in historical_data[-50:]:
            volume = self._extract_numeric_value(data, 'volume')
            if volume is not None and volume > 0:
                historical_volumes.append(volume)
        
        if len(historical_volumes) < 10:
            return anomalies
        
        # Calcular estatísticas
        avg_volume = statistics.mean(historical_volumes)
        median_volume = statistics.median(historical_volumes)
        
        if avg_volume == 0:
            return anomalies
        
        # Verificar pico de volume
        volume_ratio = current_volume / avg_volume
        
        if volume_ratio > config.volume_spike_threshold:
            # Pico de volume
            if volume_ratio > 10.0:
                severity = AnomalySeverity.CRITICAL
                confidence = 0.9
            elif volume_ratio > 5.0:
                severity = AnomalySeverity.HIGH
                confidence = 0.8
            elif volume_ratio > 3.0:
                severity = AnomalySeverity.MEDIUM
                confidence = 0.75
            else:
                severity = AnomalySeverity.LOW
                confidence = 0.65
            
            if confidence >= config.confidence_threshold:
                anomaly = AnomalyResult(
                    type=AnomalyType.VOLUME_ANOMALY,
                    severity=severity,
                    confidence=confidence,
                    description=f"Pico de volume detectado: {volume_ratio:.2f}x normal",
                    affected_field="volume",
                    current_value=current_volume,
                    context={
                        "volume_ratio": volume_ratio,
                        "average_volume": avg_volume,
                        "median_volume": median_volume
                    }
                )
                
                anomaly.add_recommendation("Verificar eventos que podem explicar o volume")
                anomaly.add_recommendation("Monitorar impacto no preço")
                
                anomalies.append(anomaly)
        
        elif volume_ratio < config.volume_drop_threshold:
            # Queda significativa de volume
            severity = AnomalySeverity.MEDIUM if volume_ratio < 0.1 else AnomalySeverity.LOW
            confidence = 0.7 if volume_ratio < 0.1 else 0.6
            
            if confidence >= config.confidence_threshold:
                anomaly = AnomalyResult(
                    type=AnomalyType.VOLUME_ANOMALY,
                    severity=severity,
                    confidence=confidence,
                    description=f"Queda significativa de volume: {volume_ratio:.2f}x normal",
                    affected_field="volume",
                    current_value=current_volume,
                    context={
                        "volume_ratio": volume_ratio,
                        "average_volume": avg_volume,
                        "median_volume": median_volume
                    }
                )
                
                anomaly.add_recommendation("Verificar se há feriados ou eventos especiais")
                anomaly.add_recommendation("Monitorar liquidez do mercado")
                
                anomalies.append(anomaly)
        
        return anomalies