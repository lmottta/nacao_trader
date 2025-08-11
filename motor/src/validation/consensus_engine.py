from typing import Dict, List, Optional, Any, Union, Callable
from datetime import datetime, timezone
from enum import Enum
from dataclasses import dataclass, field
import asyncio
import logging
import statistics
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class ConsensusStrategy(Enum):
    """Estratégias de consenso para validação de dados."""
    MAJORITY_VOTE = "majority_vote"          # Voto da maioria
    WEIGHTED_AVERAGE = "weighted_average"    # Média ponderada
    MEDIAN = "median"                        # Mediana
    CONFIDENCE_WEIGHTED = "confidence_weighted"  # Ponderado por confiança
    OUTLIER_REJECTION = "outlier_rejection"  # Rejeição de outliers
    BEST_SOURCE = "best_source"              # Melhor fonte

class ConsensusConfidence(Enum):
    """Níveis de confiança do consenso."""
    VERY_LOW = "very_low"      # Muito baixa
    LOW = "low"                # Baixa
    MEDIUM = "medium"          # Média
    HIGH = "high"              # Alta
    VERY_HIGH = "very_high"    # Muito alta

@dataclass
class SourceData:
    """Dados de uma fonte específica."""
    source_id: str                           # ID da fonte
    data: Any                                # Dados da fonte
    confidence: float                        # Confiança na fonte (0-1)
    timestamp: datetime                      # Timestamp dos dados
    quality_score: float = 1.0               # Score de qualidade (0-1)
    latency_ms: float = 0.0                  # Latência em ms
    metadata: Dict[str, Any] = field(default_factory=dict)  # Metadados
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)

@dataclass
class ConsensusResult:
    """Resultado do consenso entre fontes."""
    consensus_value: Any                     # Valor de consenso
    confidence: ConsensusConfidence          # Confiança no consenso
    strategy_used: ConsensusStrategy         # Estratégia utilizada
    participating_sources: List[str]         # Fontes que participaram
    rejected_sources: List[str] = field(default_factory=list)  # Fontes rejeitadas
    confidence_score: float = 0.0            # Score numérico de confiança
    variance: float = 0.0                    # Variância entre fontes
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)  # Metadados do consenso
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        return {
            'consensus_value': self.consensus_value,
            'confidence': self.confidence.value,
            'strategy_used': self.strategy_used.value,
            'participating_sources': self.participating_sources,
            'rejected_sources': self.rejected_sources,
            'confidence_score': self.confidence_score,
            'variance': self.variance,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }

@dataclass
class ConsensusConfig:
    """Configuração para o motor de consenso."""
    # Configurações gerais
    min_sources: int = 2                     # Mínimo de fontes para consenso
    max_sources: int = 10                    # Máximo de fontes consideradas
    default_strategy: ConsensusStrategy = ConsensusStrategy.WEIGHTED_AVERAGE
    
    # Configurações de confiança
    min_confidence_threshold: float = 0.5    # Confiança mínima para participar
    high_confidence_threshold: float = 0.8   # Threshold para alta confiança
    
    # Configurações de outliers
    outlier_threshold: float = 2.0           # Threshold para detecção de outliers (Z-score)
    max_outlier_ratio: float = 0.3           # Máximo de outliers permitidos
    
    # Configurações temporais
    max_age_seconds: int = 300               # Idade máxima dos dados (segundos)
    
    # Configurações de qualidade
    min_quality_score: float = 0.6           # Score mínimo de qualidade
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte para dicionário."""
        return {
            'min_sources': self.min_sources,
            'max_sources': self.max_sources,
            'default_strategy': self.default_strategy.value,
            'min_confidence_threshold': self.min_confidence_threshold,
            'high_confidence_threshold': self.high_confidence_threshold,
            'outlier_threshold': self.outlier_threshold,
            'max_outlier_ratio': self.max_outlier_ratio,
            'max_age_seconds': self.max_age_seconds,
            'min_quality_score': self.min_quality_score
        }

class ConsensusEngine:
    """Motor de consenso para validação de dados entre múltiplas fontes."""
    
    def __init__(self, config: ConsensusConfig = None):
        self.config = config or ConsensusConfig()
        self.source_weights = {}  # Pesos das fontes
        self.source_history = {}  # Histórico de performance das fontes
        
    def set_source_weight(self, source_id: str, weight: float):
        """Define peso para uma fonte específica."""
        self.source_weights[source_id] = max(0.0, min(1.0, weight))
    
    def get_source_weight(self, source_id: str) -> float:
        """Obtém peso de uma fonte."""
        return self.source_weights.get(source_id, 1.0)
    
    async def calculate_consensus(self, sources: List[SourceData], 
                                strategy: ConsensusStrategy = None) -> ConsensusResult:
        """Calcula consenso entre as fontes."""
        if not sources:
            raise ValueError("Nenhuma fonte fornecida")
        
        strategy = strategy or self.config.default_strategy
        
        # Filtrar fontes válidas
        valid_sources = self._filter_valid_sources(sources)
        
        if len(valid_sources) < self.config.min_sources:
            logger.warning(f"Fontes insuficientes para consenso: {len(valid_sources)} < {self.config.min_sources}")
            # Retornar resultado com baixa confiança
            if valid_sources:
                return ConsensusResult(
                    consensus_value=valid_sources[0].data,
                    confidence=ConsensusConfidence.VERY_LOW,
                    strategy_used=strategy,
                    participating_sources=[valid_sources[0].source_id],
                    confidence_score=0.2
                )
            else:
                raise ValueError("Nenhuma fonte válida disponível")
        
        # Aplicar estratégia de consenso
        if strategy == ConsensusStrategy.MAJORITY_VOTE:
            return await self._majority_vote_consensus(valid_sources)
        elif strategy == ConsensusStrategy.WEIGHTED_AVERAGE:
            return await self._weighted_average_consensus(valid_sources)
        elif strategy == ConsensusStrategy.MEDIAN:
            return await self._median_consensus(valid_sources)
        elif strategy == ConsensusStrategy.CONFIDENCE_WEIGHTED:
            return await self._confidence_weighted_consensus(valid_sources)
        elif strategy == ConsensusStrategy.OUTLIER_REJECTION:
            return await self._outlier_rejection_consensus(valid_sources)
        elif strategy == ConsensusStrategy.BEST_SOURCE:
            return await self._best_source_consensus(valid_sources)
        else:
            raise ValueError(f"Estratégia não suportada: {strategy}")
    
    def _filter_valid_sources(self, sources: List[SourceData]) -> List[SourceData]:
        """Filtra fontes válidas baseado na configuração."""
        valid_sources = []
        current_time = datetime.now(timezone.utc)
        
        for source in sources:
            # Verificar idade dos dados
            age_seconds = (current_time - source.timestamp).total_seconds()
            if age_seconds > self.config.max_age_seconds:
                logger.debug(f"Fonte {source.source_id} muito antiga: {age_seconds}s")
                continue
            
            # Verificar confiança mínima
            if source.confidence < self.config.min_confidence_threshold:
                logger.debug(f"Fonte {source.source_id} com confiança baixa: {source.confidence}")
                continue
            
            # Verificar qualidade mínima
            if source.quality_score < self.config.min_quality_score:
                logger.debug(f"Fonte {source.source_id} com qualidade baixa: {source.quality_score}")
                continue
            
            valid_sources.append(source)
        
        # Limitar número máximo de fontes
        if len(valid_sources) > self.config.max_sources:
            # Ordenar por confiança e qualidade
            valid_sources.sort(key=lambda s: s.confidence * s.quality_score, reverse=True)
            valid_sources = valid_sources[:self.config.max_sources]
        
        return valid_sources
    
    async def _majority_vote_consensus(self, sources: List[SourceData]) -> ConsensusResult:
        """Consenso por voto da maioria."""
        # Para dados categóricos ou booleanos
        values = [source.data for source in sources]
        value_counts = {}
        
        for value in values:
            str_value = str(value)
            if str_value not in value_counts:
                value_counts[str_value] = []
            value_counts[str_value].append(value)
        
        # Encontrar valor mais comum
        most_common = max(value_counts.items(), key=lambda x: len(x[1]))
        consensus_value = most_common[1][0]  # Valor original
        vote_count = len(most_common[1])
        
        # Calcular confiança
        confidence_score = vote_count / len(sources)
        confidence = self._calculate_confidence_level(confidence_score)
        
        participating_sources = [s.source_id for s in sources]
        
        return ConsensusResult(
            consensus_value=consensus_value,
            confidence=confidence,
            strategy_used=ConsensusStrategy.MAJORITY_VOTE,
            participating_sources=participating_sources,
            confidence_score=confidence_score,
            metadata={'vote_count': vote_count, 'total_votes': len(sources)}
        )
    
    async def _weighted_average_consensus(self, sources: List[SourceData]) -> ConsensusResult:
        """Consenso por média ponderada."""
        numeric_sources = self._extract_numeric_sources(sources)
        
        if not numeric_sources:
            # Fallback para majority vote
            return await self._majority_vote_consensus(sources)
        
        total_weight = 0.0
        weighted_sum = 0.0
        
        for source in numeric_sources:
            weight = self.get_source_weight(source.source_id) * source.confidence * source.quality_score
            weighted_sum += source.data * weight
            total_weight += weight
        
        if total_weight == 0:
            raise ValueError("Peso total zero")
        
        consensus_value = weighted_sum / total_weight
        
        # Calcular variância
        variance = self._calculate_variance([s.data for s in numeric_sources])
        
        # Calcular confiança baseada na variância e número de fontes
        confidence_score = self._calculate_weighted_confidence(numeric_sources, variance)
        confidence = self._calculate_confidence_level(confidence_score)
        
        participating_sources = [s.source_id for s in numeric_sources]
        
        return ConsensusResult(
            consensus_value=consensus_value,
            confidence=confidence,
            strategy_used=ConsensusStrategy.WEIGHTED_AVERAGE,
            participating_sources=participating_sources,
            confidence_score=confidence_score,
            variance=variance
        )
    
    async def _median_consensus(self, sources: List[SourceData]) -> ConsensusResult:
        """Consenso por mediana."""
        numeric_sources = self._extract_numeric_sources(sources)
        
        if not numeric_sources:
            return await self._majority_vote_consensus(sources)
        
        values = [source.data for source in numeric_sources]
        consensus_value = statistics.median(values)
        
        # Calcular variância
        variance = self._calculate_variance(values)
        
        # Confiança baseada no número de fontes e variância
        confidence_score = min(0.9, len(numeric_sources) / self.config.max_sources * 0.7 + 0.3)
        if variance > 0:
            confidence_score *= max(0.3, 1.0 / (1.0 + variance))
        
        confidence = self._calculate_confidence_level(confidence_score)
        
        participating_sources = [s.source_id for s in numeric_sources]
        
        return ConsensusResult(
            consensus_value=consensus_value,
            confidence=confidence,
            strategy_used=ConsensusStrategy.MEDIAN,
            participating_sources=participating_sources,
            confidence_score=confidence_score,
            variance=variance
        )
    
    async def _confidence_weighted_consensus(self, sources: List[SourceData]) -> ConsensusResult:
        """Consenso ponderado por confiança."""
        numeric_sources = self._extract_numeric_sources(sources)
        
        if not numeric_sources:
            return await self._majority_vote_consensus(sources)
        
        total_confidence = sum(s.confidence for s in numeric_sources)
        if total_confidence == 0:
            return await self._median_consensus(sources)
        
        weighted_sum = sum(s.data * s.confidence for s in numeric_sources)
        consensus_value = weighted_sum / total_confidence
        
        # Calcular variância
        variance = self._calculate_variance([s.data for s in numeric_sources])
        
        # Confiança baseada na confiança média das fontes
        avg_confidence = total_confidence / len(numeric_sources)
        confidence_score = avg_confidence * (1.0 / (1.0 + variance))
        confidence = self._calculate_confidence_level(confidence_score)
        
        participating_sources = [s.source_id for s in numeric_sources]
        
        return ConsensusResult(
            consensus_value=consensus_value,
            confidence=confidence,
            strategy_used=ConsensusStrategy.CONFIDENCE_WEIGHTED,
            participating_sources=participating_sources,
            confidence_score=confidence_score,
            variance=variance
        )
    
    async def _outlier_rejection_consensus(self, sources: List[SourceData]) -> ConsensusResult:
        """Consenso com rejeição de outliers."""
        numeric_sources = self._extract_numeric_sources(sources)
        
        if len(numeric_sources) < 3:
            return await self._weighted_average_consensus(sources)
        
        values = [s.data for s in numeric_sources]
        
        # Detectar outliers usando Z-score
        mean_val = statistics.mean(values)
        stdev_val = statistics.stdev(values) if len(values) > 1 else 0
        
        filtered_sources = []
        rejected_sources = []
        
        for source in numeric_sources:
            if stdev_val == 0:
                filtered_sources.append(source)
            else:
                z_score = abs(source.data - mean_val) / stdev_val
                if z_score <= self.config.outlier_threshold:
                    filtered_sources.append(source)
                else:
                    rejected_sources.append(source.source_id)
        
        # Verificar se não rejeitamos muitas fontes
        rejection_ratio = len(rejected_sources) / len(numeric_sources)
        if rejection_ratio > self.config.max_outlier_ratio:
            # Usar todas as fontes se rejeitamos muitas
            filtered_sources = numeric_sources
            rejected_sources = []
        
        if not filtered_sources:
            filtered_sources = numeric_sources
            rejected_sources = []
        
        # Calcular consenso com fontes filtradas
        result = await self._weighted_average_consensus(filtered_sources)
        result.strategy_used = ConsensusStrategy.OUTLIER_REJECTION
        result.rejected_sources = rejected_sources
        
        return result
    
    async def _best_source_consensus(self, sources: List[SourceData]) -> ConsensusResult:
        """Consenso usando a melhor fonte."""
        # Ordenar por score combinado
        scored_sources = []
        for source in sources:
            score = (source.confidence * 0.4 + 
                    source.quality_score * 0.3 + 
                    self.get_source_weight(source.source_id) * 0.3)
            scored_sources.append((score, source))
        
        scored_sources.sort(key=lambda x: x[0], reverse=True)
        best_source = scored_sources[0][1]
        
        confidence_score = scored_sources[0][0]
        confidence = self._calculate_confidence_level(confidence_score)
        
        return ConsensusResult(
            consensus_value=best_source.data,
            confidence=confidence,
            strategy_used=ConsensusStrategy.BEST_SOURCE,
            participating_sources=[best_source.source_id],
            confidence_score=confidence_score,
            metadata={'best_source_score': scored_sources[0][0]}
        )
    
    def _extract_numeric_sources(self, sources: List[SourceData]) -> List[SourceData]:
        """Extrai fontes com dados numéricos."""
        numeric_sources = []
        for source in sources:
            if isinstance(source.data, (int, float)):
                numeric_sources.append(source)
            elif isinstance(source.data, str):
                try:
                    # Tentar converter string para número
                    numeric_value = float(source.data.replace(',', '').replace('%', ''))
                    # Criar nova fonte com valor numérico
                    numeric_source = SourceData(
                        source_id=source.source_id,
                        data=numeric_value,
                        confidence=source.confidence,
                        timestamp=source.timestamp,
                        quality_score=source.quality_score,
                        latency_ms=source.latency_ms,
                        metadata=source.metadata
                    )
                    numeric_sources.append(numeric_source)
                except ValueError:
                    continue
        return numeric_sources
    
    def _calculate_variance(self, values: List[float]) -> float:
        """Calcula variância dos valores."""
        if len(values) < 2:
            return 0.0
        try:
            return statistics.variance(values)
        except:
            return 0.0
    
    def _calculate_weighted_confidence(self, sources: List[SourceData], variance: float) -> float:
        """Calcula confiança ponderada."""
        if not sources:
            return 0.0
        
        # Confiança baseada no número de fontes
        source_confidence = min(0.9, len(sources) / self.config.max_sources)
        
        # Confiança baseada na qualidade média
        avg_quality = sum(s.quality_score for s in sources) / len(sources)
        quality_confidence = avg_quality
        
        # Confiança baseada na confiança média das fontes
        avg_confidence = sum(s.confidence for s in sources) / len(sources)
        
        # Penalizar alta variância
        variance_penalty = 1.0 / (1.0 + variance) if variance > 0 else 1.0
        
        # Combinar todas as métricas
        final_confidence = (source_confidence * 0.3 + 
                          quality_confidence * 0.3 + 
                          avg_confidence * 0.4) * variance_penalty
        
        return max(0.0, min(1.0, final_confidence))
    
    def _calculate_confidence_level(self, score: float) -> ConsensusConfidence:
        """Converte score numérico para nível de confiança."""
        if score >= 0.9:
            return ConsensusConfidence.VERY_HIGH
        elif score >= 0.75:
            return ConsensusConfidence.HIGH
        elif score >= 0.5:
            return ConsensusConfidence.MEDIUM
        elif score >= 0.25:
            return ConsensusConfidence.LOW
        else:
            return ConsensusConfidence.VERY_LOW
    
    def update_source_performance(self, source_id: str, accuracy: float, latency_ms: float):
        """Atualiza histórico de performance de uma fonte."""
        if source_id not in self.source_history:
            self.source_history[source_id] = {
                'accuracy_history': [],
                'latency_history': [],
                'last_update': datetime.now(timezone.utc)
            }
        
        history = self.source_history[source_id]
        history['accuracy_history'].append(accuracy)
        history['latency_history'].append(latency_ms)
        history['last_update'] = datetime.now(timezone.utc)
        
        # Manter apenas últimas 100 medições
        if len(history['accuracy_history']) > 100:
            history['accuracy_history'] = history['accuracy_history'][-100:]
            history['latency_history'] = history['latency_history'][-100:]
        
        # Atualizar peso da fonte baseado na performance
        avg_accuracy = statistics.mean(history['accuracy_history'])
        avg_latency = statistics.mean(history['latency_history'])
        
        # Peso baseado na acurácia e latência inversa
        latency_score = max(0.1, 1.0 / (1.0 + avg_latency / 1000.0))  # Normalizar latência
        new_weight = avg_accuracy * 0.7 + latency_score * 0.3
        
        self.set_source_weight(source_id, new_weight)
    
    def get_source_stats(self, source_id: str) -> Dict[str, Any]:
        """Obtém estatísticas de uma fonte."""
        if source_id not in self.source_history:
            return {}
        
        history = self.source_history[source_id]
        
        return {
            'weight': self.get_source_weight(source_id),
            'avg_accuracy': statistics.mean(history['accuracy_history']) if history['accuracy_history'] else 0.0,
            'avg_latency_ms': statistics.mean(history['latency_history']) if history['latency_history'] else 0.0,
            'measurement_count': len(history['accuracy_history']),
            'last_update': history['last_update'].isoformat()
        }