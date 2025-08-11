from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime, timezone, timedelta
from enum import Enum
from dataclasses import dataclass, field
import asyncio
import logging
import random
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class RotationStrategy(Enum):
    """Estratégias de rotação entre fontes."""
    ROUND_ROBIN = "round_robin"          # Rotação circular
    WEIGHTED = "weighted"                # Baseado em pesos/prioridades
    PERFORMANCE = "performance"          # Baseado em performance histórica
    AVAILABILITY = "availability"        # Baseado em disponibilidade
    RANDOM = "random"                    # Seleção aleatória
    HYBRID = "hybrid"                    # Combinação de estratégias

class SourceStatus(Enum):
    """Status de uma fonte de dados."""
    ACTIVE = "active"                    # Fonte ativa e funcionando
    DEGRADED = "degraded"                # Fonte com problemas mas funcional
    FAILED = "failed"                    # Fonte com falha
    MAINTENANCE = "maintenance"          # Fonte em manutenção
    DISABLED = "disabled"                # Fonte desabilitada

@dataclass
class SourceMetrics:
    """Métricas de performance de uma fonte."""
    success_rate: float = 0.0            # Taxa de sucesso (0-1)
    avg_response_time: float = 0.0       # Tempo médio de resposta (ms)
    error_count: int = 0                 # Contagem de erros
    total_requests: int = 0              # Total de requisições
    last_success: Optional[datetime] = None  # Última requisição bem-sucedida
    last_error: Optional[datetime] = None    # Último erro
    consecutive_failures: int = 0        # Falhas consecutivas
    uptime_percentage: float = 100.0     # Percentual de uptime
    data_quality_score: float = 1.0      # Score de qualidade dos dados (0-1)
    
    def update_success(self, response_time: float):
        """Atualiza métricas após sucesso."""
        self.total_requests += 1
        self.avg_response_time = (
            (self.avg_response_time * (self.total_requests - 1) + response_time) / 
            self.total_requests
        )
        self.success_rate = (
            (self.success_rate * (self.total_requests - 1) + 1.0) / 
            self.total_requests
        )
        self.last_success = datetime.now(timezone.utc)
        self.consecutive_failures = 0
    
    def update_failure(self):
        """Atualiza métricas após falha."""
        self.total_requests += 1
        self.error_count += 1
        self.success_rate = (
            (self.success_rate * (self.total_requests - 1)) / 
            self.total_requests
        )
        self.last_error = datetime.now(timezone.utc)
        self.consecutive_failures += 1

@dataclass
class SourceInfo:
    """Informações de uma fonte de dados."""
    name: str                            # Nome da fonte
    collector: Any                       # Instância do coletor
    priority: int = 1                    # Prioridade (1=alta, 10=baixa)
    weight: float = 1.0                  # Peso para balanceamento
    status: SourceStatus = SourceStatus.ACTIVE
    metrics: SourceMetrics = field(default_factory=SourceMetrics)
    supported_symbols: List[str] = field(default_factory=list)
    supported_data_types: List[str] = field(default_factory=list)
    rate_limit: Optional[float] = None   # Limite de requisições por segundo
    cost_per_request: float = 0.0        # Custo por requisição
    max_concurrent: int = 10             # Máximo de requisições concorrentes
    timeout: float = 30.0                # Timeout em segundos
    retry_count: int = 3                 # Número de tentativas
    circuit_breaker_threshold: int = 5   # Limite para circuit breaker
    maintenance_window: Optional[tuple] = None  # Janela de manutenção (hora_inicio, hora_fim)
    tags: List[str] = field(default_factory=list)  # Tags para categorização
    
    def is_available(self) -> bool:
        """Verifica se a fonte está disponível."""
        if self.status in [SourceStatus.FAILED, SourceStatus.DISABLED]:
            return False
        
        # Verificar janela de manutenção
        if self.maintenance_window:
            now = datetime.now(timezone.utc).time()
            start_time, end_time = self.maintenance_window
            if start_time <= now <= end_time:
                return False
        
        # Verificar circuit breaker
        if self.metrics.consecutive_failures >= self.circuit_breaker_threshold:
            return False
        
        return True
    
    def calculate_score(self, strategy: RotationStrategy) -> float:
        """Calcula score da fonte baseado na estratégia."""
        if not self.is_available():
            return 0.0
        
        base_score = 1.0
        
        if strategy == RotationStrategy.WEIGHTED:
            return self.weight
        
        elif strategy == RotationStrategy.PERFORMANCE:
            # Combinar taxa de sucesso, tempo de resposta e qualidade
            performance_score = (
                self.metrics.success_rate * 0.4 +
                (1.0 / max(self.metrics.avg_response_time, 1.0)) * 0.3 +
                self.metrics.data_quality_score * 0.3
            )
            return performance_score * self.weight
        
        elif strategy == RotationStrategy.AVAILABILITY:
            # Baseado em uptime e falhas consecutivas
            availability_score = (
                self.metrics.uptime_percentage / 100.0 * 0.6 +
                max(0, 1.0 - self.metrics.consecutive_failures / 10.0) * 0.4
            )
            return availability_score * self.weight
        
        elif strategy == RotationStrategy.HYBRID:
            # Combinação de múltiplos fatores
            hybrid_score = (
                self.metrics.success_rate * 0.25 +
                (self.metrics.uptime_percentage / 100.0) * 0.25 +
                (1.0 / max(self.metrics.avg_response_time, 1.0)) * 0.2 +
                self.metrics.data_quality_score * 0.2 +
                (1.0 / max(self.priority, 1.0)) * 0.1
            )
            return hybrid_score * self.weight
        
        return base_score

class SourceRotator:
    """Gerenciador de rotação automática entre fontes de dados."""
    
    def __init__(self, strategy: RotationStrategy = RotationStrategy.HYBRID):
        self.strategy = strategy
        self.sources: Dict[str, SourceInfo] = {}
        self.current_index = 0
        self.last_rotation = datetime.now(timezone.utc)
        self.rotation_interval = timedelta(minutes=5)  # Intervalo mínimo entre rotações
        self.active_requests: Dict[str, int] = {}  # Requisições ativas por fonte
        self.request_history: List[Dict] = []  # Histórico de requisições
        self.max_history_size = 1000
        
        logger.info(f"SourceRotator inicializado com estratégia {strategy.value}")
    
    def add_source(self, source_info: SourceInfo):
        """Adiciona uma nova fonte de dados."""
        self.sources[source_info.name] = source_info
        self.active_requests[source_info.name] = 0
        
        logger.info(f"Fonte {source_info.name} adicionada com prioridade {source_info.priority}")
    
    def remove_source(self, source_name: str):
        """Remove uma fonte de dados."""
        if source_name in self.sources:
            del self.sources[source_name]
            del self.active_requests[source_name]
            logger.info(f"Fonte {source_name} removida")
    
    def update_source_status(self, source_name: str, status: SourceStatus):
        """Atualiza o status de uma fonte."""
        if source_name in self.sources:
            self.sources[source_name].status = status
            logger.info(f"Status da fonte {source_name} atualizado para {status.value}")
    
    def get_available_sources(self, symbol: str = None, data_type: str = None) -> List[SourceInfo]:
        """Obtém lista de fontes disponíveis para um símbolo/tipo de dados."""
        available = []
        
        for source in self.sources.values():
            if not source.is_available():
                continue
            
            # Filtrar por símbolo se especificado
            if symbol and source.supported_symbols:
                if symbol not in source.supported_symbols:
                    continue
            
            # Filtrar por tipo de dados se especificado
            if data_type and source.supported_data_types:
                if data_type not in source.supported_data_types:
                    continue
            
            available.append(source)
        
        return available
    
    def select_source(self, symbol: str = None, data_type: str = None, 
                     exclude: List[str] = None) -> Optional[SourceInfo]:
        """Seleciona a melhor fonte baseada na estratégia configurada."""
        available_sources = self.get_available_sources(symbol, data_type)
        
        # Filtrar fontes excluídas
        if exclude:
            available_sources = [s for s in available_sources if s.name not in exclude]
        
        if not available_sources:
            logger.warning(f"Nenhuma fonte disponível para símbolo={symbol}, tipo={data_type}")
            return None
        
        # Aplicar estratégia de seleção
        if self.strategy == RotationStrategy.ROUND_ROBIN:
            return self._select_round_robin(available_sources)
        
        elif self.strategy == RotationStrategy.RANDOM:
            return random.choice(available_sources)
        
        elif self.strategy in [RotationStrategy.WEIGHTED, RotationStrategy.PERFORMANCE, 
                              RotationStrategy.AVAILABILITY, RotationStrategy.HYBRID]:
            return self._select_by_score(available_sources)
        
        # Fallback para primeira fonte disponível
        return available_sources[0]
    
    def _select_round_robin(self, sources: List[SourceInfo]) -> SourceInfo:
        """Seleção round-robin."""
        if not sources:
            return None
        
        # Ordenar por nome para consistência
        sources.sort(key=lambda x: x.name)
        
        selected = sources[self.current_index % len(sources)]
        self.current_index += 1
        
        return selected
    
    def _select_by_score(self, sources: List[SourceInfo]) -> SourceInfo:
        """Seleção baseada em score calculado."""
        if not sources:
            return None
        
        # Calcular scores
        scored_sources = []
        for source in sources:
            score = source.calculate_score(self.strategy)
            
            # Penalizar fontes com muitas requisições ativas
            if self.active_requests[source.name] >= source.max_concurrent:
                score *= 0.1  # Reduzir drasticamente o score
            elif self.active_requests[source.name] > source.max_concurrent * 0.8:
                score *= 0.5  # Reduzir score moderadamente
            
            scored_sources.append((source, score))
        
        # Ordenar por score (maior primeiro)
        scored_sources.sort(key=lambda x: x[1], reverse=True)
        
        # Seleção probabilística baseada nos scores
        if len(scored_sources) == 1:
            return scored_sources[0][0]
        
        # Usar weighted random selection
        total_score = sum(score for _, score in scored_sources)
        if total_score <= 0:
            return scored_sources[0][0]  # Fallback para primeira fonte
        
        # Normalizar scores e fazer seleção probabilística
        rand_val = random.random() * total_score
        cumulative = 0
        
        for source, score in scored_sources:
            cumulative += score
            if rand_val <= cumulative:
                return source
        
        # Fallback
        return scored_sources[0][0]
    
    async def execute_with_rotation(self, operation: Callable, symbol: str = None,
                                  data_type: str = None, max_retries: int = 3,
                                  **kwargs) -> Any:
        """Executa uma operação com rotação automática entre fontes."""
        tried_sources = []
        last_exception = None
        
        for attempt in range(max_retries):
            # Selecionar fonte
            source = self.select_source(symbol, data_type, exclude=tried_sources)
            
            if not source:
                logger.error(f"Nenhuma fonte disponível após {attempt + 1} tentativas")
                break
            
            tried_sources.append(source.name)
            
            # Incrementar contador de requisições ativas
            self.active_requests[source.name] += 1
            
            start_time = datetime.now(timezone.utc)
            
            try:
                # Executar operação
                result = await operation(source.collector, **kwargs)
                
                # Calcular tempo de resposta
                response_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                
                # Atualizar métricas de sucesso
                source.metrics.update_success(response_time)
                
                # Registrar no histórico
                self._record_request(source.name, True, response_time)
                
                logger.debug(f"Operação executada com sucesso na fonte {source.name}")
                return result
            
            except Exception as e:
                # Calcular tempo até falha
                response_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                
                # Atualizar métricas de falha
                source.metrics.update_failure()
                
                # Registrar no histórico
                self._record_request(source.name, False, response_time, str(e))
                
                logger.warning(f"Falha na fonte {source.name}: {e}")
                last_exception = e
                
                # Verificar se deve marcar fonte como degradada/falha
                if source.metrics.consecutive_failures >= 3:
                    source.status = SourceStatus.DEGRADED
                if source.metrics.consecutive_failures >= source.circuit_breaker_threshold:
                    source.status = SourceStatus.FAILED
                    logger.error(f"Fonte {source.name} marcada como falha após {source.metrics.consecutive_failures} falhas consecutivas")
            
            finally:
                # Decrementar contador de requisições ativas
                self.active_requests[source.name] = max(0, self.active_requests[source.name] - 1)
        
        # Se chegou aqui, todas as tentativas falharam
        if last_exception:
            raise last_exception
        else:
            raise Exception("Todas as fontes falharam e nenhuma exceção foi capturada")
    
    def _record_request(self, source_name: str, success: bool, response_time: float, error: str = None):
        """Registra uma requisição no histórico."""
        record = {
            'timestamp': datetime.now(timezone.utc),
            'source': source_name,
            'success': success,
            'response_time': response_time,
            'error': error
        }
        
        self.request_history.append(record)
        
        # Limitar tamanho do histórico
        if len(self.request_history) > self.max_history_size:
            self.request_history = self.request_history[-self.max_history_size:]
    
    def get_source_statistics(self) -> Dict[str, Dict]:
        """Obtém estatísticas de todas as fontes."""
        stats = {}
        
        for name, source in self.sources.items():
            stats[name] = {
                'status': source.status.value,
                'priority': source.priority,
                'weight': source.weight,
                'metrics': {
                    'success_rate': source.metrics.success_rate,
                    'avg_response_time': source.metrics.avg_response_time,
                    'error_count': source.metrics.error_count,
                    'total_requests': source.metrics.total_requests,
                    'consecutive_failures': source.metrics.consecutive_failures,
                    'uptime_percentage': source.metrics.uptime_percentage,
                    'data_quality_score': source.metrics.data_quality_score
                },
                'active_requests': self.active_requests[name],
                'is_available': source.is_available()
            }
        
        return stats
    
    def reset_source_metrics(self, source_name: str = None):
        """Reseta métricas de uma fonte específica ou todas."""
        if source_name:
            if source_name in self.sources:
                self.sources[source_name].metrics = SourceMetrics()
                logger.info(f"Métricas da fonte {source_name} resetadas")
        else:
            for source in self.sources.values():
                source.metrics = SourceMetrics()
            logger.info("Métricas de todas as fontes resetadas")
    
    def set_strategy(self, strategy: RotationStrategy):
        """Altera a estratégia de rotação."""
        self.strategy = strategy
        logger.info(f"Estratégia de rotação alterada para {strategy.value}")
    
    def get_request_history(self, source_name: str = None, limit: int = 100) -> List[Dict]:
        """Obtém histórico de requisições."""
        history = self.request_history
        
        if source_name:
            history = [r for r in history if r['source'] == source_name]
        
        return history[-limit:] if limit else history