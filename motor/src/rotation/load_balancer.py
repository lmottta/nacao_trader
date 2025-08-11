from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime, timezone, timedelta
from enum import Enum
from dataclasses import dataclass, field
import asyncio
import logging
import random
import math
from collections import defaultdict, deque

from .source_rotator import SourceInfo, SourceStatus, SourceRotator

logger = logging.getLogger(__name__)

class LoadBalancingStrategy(Enum):
    """Estratégias de balanceamento de carga."""
    ROUND_ROBIN = "round_robin"              # Distribuição circular
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"  # Round robin com pesos
    LEAST_CONNECTIONS = "least_connections"  # Menor número de conexões ativas
    LEAST_RESPONSE_TIME = "least_response_time"  # Menor tempo de resposta
    RESOURCE_BASED = "resource_based"        # Baseado em recursos disponíveis
    ADAPTIVE = "adaptive"                    # Adaptativo baseado em múltiplas métricas
    GEOGRAPHIC = "geographic"                # Baseado em localização geográfica
    COST_OPTIMIZED = "cost_optimized"        # Otimizado por custo

@dataclass
class LoadMetrics:
    """Métricas de carga de uma fonte."""
    active_connections: int = 0              # Conexões ativas
    requests_per_second: float = 0.0         # Requisições por segundo
    cpu_usage: float = 0.0                   # Uso de CPU (0-100)
    memory_usage: float = 0.0                # Uso de memória (0-100)
    bandwidth_usage: float = 0.0             # Uso de largura de banda (MB/s)
    queue_length: int = 0                    # Tamanho da fila de requisições
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def calculate_load_score(self) -> float:
        """Calcula um score de carga normalizado (0-1, onde 0 = sem carga)."""
        # Normalizar métricas (assumindo limites máximos)
        connection_score = min(1.0, self.active_connections / 100.0)
        rps_score = min(1.0, self.requests_per_second / 1000.0)
        cpu_score = self.cpu_usage / 100.0
        memory_score = self.memory_usage / 100.0
        bandwidth_score = min(1.0, self.bandwidth_usage / 100.0)  # 100 MB/s max
        queue_score = min(1.0, self.queue_length / 50.0)
        
        # Média ponderada
        load_score = (
            connection_score * 0.25 +
            rps_score * 0.20 +
            cpu_score * 0.20 +
            memory_score * 0.15 +
            bandwidth_score * 0.10 +
            queue_score * 0.10
        )
        
        return min(1.0, load_score)

@dataclass
class RequestContext:
    """Contexto de uma requisição para balanceamento."""
    request_id: str                          # ID único da requisição
    symbol: str = None                       # Símbolo solicitado
    data_type: str = None                    # Tipo de dados
    priority: int = 1                        # Prioridade (1=alta, 10=baixa)
    max_latency: float = None                # Latência máxima aceitável (ms)
    cost_limit: float = None                 # Limite de custo
    preferred_sources: List[str] = field(default_factory=list)  # Fontes preferidas
    excluded_sources: List[str] = field(default_factory=list)   # Fontes excluídas
    geographic_preference: str = None        # Preferência geográfica
    quality_requirement: float = 0.8         # Requisito mínimo de qualidade (0-1)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

class LoadBalancer:
    """Balanceador de carga inteligente para fontes de dados."""
    
    def __init__(self, source_rotator: SourceRotator, 
                 strategy: LoadBalancingStrategy = LoadBalancingStrategy.ADAPTIVE):
        self.source_rotator = source_rotator
        self.strategy = strategy
        self.load_metrics: Dict[str, LoadMetrics] = {}
        self.request_queues: Dict[str, deque] = defaultdict(deque)
        self.round_robin_counters: Dict[str, int] = defaultdict(int)
        self.weighted_counters: Dict[str, int] = defaultdict(int)
        
        # Configurações
        self.max_queue_size = 100
        self.metrics_update_interval = timedelta(seconds=10)
        self.last_metrics_update = datetime.now(timezone.utc)
        
        # Histórico de performance
        self.performance_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # Callbacks
        self.on_overload_detected: Optional[Callable] = None
        self.on_source_selected: Optional[Callable] = None
        
        logger.info(f"LoadBalancer inicializado com estratégia {strategy.value}")
    
    def update_load_metrics(self, source_name: str, metrics: LoadMetrics):
        """Atualiza métricas de carga de uma fonte."""
        self.load_metrics[source_name] = metrics
        
        # Registrar no histórico
        self.performance_history[source_name].append({
            'timestamp': datetime.now(timezone.utc),
            'load_score': metrics.calculate_load_score(),
            'active_connections': metrics.active_connections,
            'response_time': getattr(metrics, 'avg_response_time', 0)
        })
    
    async def select_source(self, context: RequestContext) -> Optional[SourceInfo]:
        """Seleciona a melhor fonte baseada na estratégia de balanceamento."""
        available_sources = self._get_available_sources(context)
        
        if not available_sources:
            logger.warning(f"Nenhuma fonte disponível para requisição {context.request_id}")
            return None
        
        # Aplicar estratégia de balanceamento
        selected_source = None
        
        if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            selected_source = self._select_round_robin(available_sources, context)
        
        elif self.strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
            selected_source = self._select_weighted_round_robin(available_sources, context)
        
        elif self.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            selected_source = self._select_least_connections(available_sources, context)
        
        elif self.strategy == LoadBalancingStrategy.LEAST_RESPONSE_TIME:
            selected_source = self._select_least_response_time(available_sources, context)
        
        elif self.strategy == LoadBalancingStrategy.RESOURCE_BASED:
            selected_source = self._select_resource_based(available_sources, context)
        
        elif self.strategy == LoadBalancingStrategy.ADAPTIVE:
            selected_source = self._select_adaptive(available_sources, context)
        
        elif self.strategy == LoadBalancingStrategy.COST_OPTIMIZED:
            selected_source = self._select_cost_optimized(available_sources, context)
        
        else:
            # Fallback para primeira fonte disponível
            selected_source = available_sources[0]
        
        if selected_source:
            # Incrementar contador de conexões ativas
            if selected_source.name in self.load_metrics:
                self.load_metrics[selected_source.name].active_connections += 1
            
            # Chamar callback se configurado
            if self.on_source_selected:
                try:
                    await self.on_source_selected(selected_source, context)
                except Exception as e:
                    logger.error(f"Erro no callback de seleção: {e}")
            
            logger.debug(f"Fonte {selected_source.name} selecionada para requisição {context.request_id}")
        
        return selected_source
    
    def _get_available_sources(self, context: RequestContext) -> List[SourceInfo]:
        """Obtém fontes disponíveis baseadas no contexto da requisição."""
        available = []
        
        for source in self.source_rotator.sources.values():
            # Verificar disponibilidade básica
            if not source.is_available():
                continue
            
            # Verificar fontes excluídas
            if source.name in context.excluded_sources:
                continue
            
            # Verificar sobrecarga
            if self._is_source_overloaded(source.name):
                continue
            
            # Verificar requisitos de qualidade
            if source.metrics.data_quality_score < context.quality_requirement:
                continue
            
            # Verificar limite de custo
            if context.cost_limit and source.cost_per_request > context.cost_limit:
                continue
            
            # Verificar latência máxima
            if (context.max_latency and 
                source.metrics.avg_response_time > context.max_latency):
                continue
            
            # Verificar suporte ao símbolo/tipo de dados
            if context.symbol and source.supported_symbols:
                if context.symbol not in source.supported_symbols:
                    continue
            
            if context.data_type and source.supported_data_types:
                if context.data_type not in source.supported_data_types:
                    continue
            
            available.append(source)
        
        # Priorizar fontes preferidas
        if context.preferred_sources:
            preferred = [s for s in available if s.name in context.preferred_sources]
            if preferred:
                return preferred
        
        return available
    
    def _is_source_overloaded(self, source_name: str) -> bool:
        """Verifica se uma fonte está sobrecarregada."""
        if source_name not in self.load_metrics:
            return False
        
        metrics = self.load_metrics[source_name]
        source = self.source_rotator.sources[source_name]
        
        # Verificar limites
        if metrics.active_connections >= source.max_concurrent:
            return True
        
        if metrics.queue_length >= self.max_queue_size:
            return True
        
        # Verificar score de carga
        load_score = metrics.calculate_load_score()
        if load_score > 0.9:  # 90% de carga
            return True
        
        return False
    
    def _select_round_robin(self, sources: List[SourceInfo], context: RequestContext) -> SourceInfo:
        """Seleção round-robin simples."""
        if not sources:
            return None
        
        # Ordenar por nome para consistência
        sources.sort(key=lambda x: x.name)
        
        key = f"{context.symbol}_{context.data_type}"
        index = self.round_robin_counters[key] % len(sources)
        self.round_robin_counters[key] += 1
        
        return sources[index]
    
    def _select_weighted_round_robin(self, sources: List[SourceInfo], context: RequestContext) -> SourceInfo:
        """Seleção round-robin com pesos."""
        if not sources:
            return None
        
        # Criar lista expandida baseada nos pesos
        weighted_sources = []
        for source in sources:
            weight = max(1, int(source.weight * 10))  # Converter para inteiro
            weighted_sources.extend([source] * weight)
        
        if not weighted_sources:
            return sources[0]
        
        key = f"{context.symbol}_{context.data_type}"
        index = self.weighted_counters[key] % len(weighted_sources)
        self.weighted_counters[key] += 1
        
        return weighted_sources[index]
    
    def _select_least_connections(self, sources: List[SourceInfo], context: RequestContext) -> SourceInfo:
        """Seleção baseada no menor número de conexões ativas."""
        if not sources:
            return None
        
        # Ordenar por número de conexões ativas
        sources_with_connections = []
        for source in sources:
            connections = 0
            if source.name in self.load_metrics:
                connections = self.load_metrics[source.name].active_connections
            sources_with_connections.append((source, connections))
        
        # Ordenar por conexões (menor primeiro)
        sources_with_connections.sort(key=lambda x: x[1])
        
        return sources_with_connections[0][0]
    
    def _select_least_response_time(self, sources: List[SourceInfo], context: RequestContext) -> SourceInfo:
        """Seleção baseada no menor tempo de resposta."""
        if not sources:
            return None
        
        # Ordenar por tempo de resposta médio
        sources.sort(key=lambda x: x.metrics.avg_response_time)
        
        return sources[0]
    
    def _select_resource_based(self, sources: List[SourceInfo], context: RequestContext) -> SourceInfo:
        """Seleção baseada em recursos disponíveis."""
        if not sources:
            return None
        
        # Calcular score baseado em recursos
        scored_sources = []
        for source in sources:
            load_score = 0.0
            if source.name in self.load_metrics:
                load_score = self.load_metrics[source.name].calculate_load_score()
            
            # Inverter score (menor carga = melhor)
            resource_score = 1.0 - load_score
            scored_sources.append((source, resource_score))
        
        # Ordenar por score (maior primeiro)
        scored_sources.sort(key=lambda x: x[1], reverse=True)
        
        return scored_sources[0][0]
    
    def _select_adaptive(self, sources: List[SourceInfo], context: RequestContext) -> SourceInfo:
        """Seleção adaptativa baseada em múltiplas métricas."""
        if not sources:
            return None
        
        scored_sources = []
        
        for source in sources:
            # Calcular score composto
            performance_score = self._calculate_performance_score(source)
            load_score = self._calculate_load_score(source)
            reliability_score = self._calculate_reliability_score(source)
            cost_score = self._calculate_cost_score(source, context)
            
            # Pesos adaptativos baseados na prioridade da requisição
            if context.priority <= 2:  # Alta prioridade
                composite_score = (
                    performance_score * 0.4 +
                    reliability_score * 0.3 +
                    load_score * 0.2 +
                    cost_score * 0.1
                )
            else:  # Baixa prioridade
                composite_score = (
                    cost_score * 0.4 +
                    load_score * 0.3 +
                    performance_score * 0.2 +
                    reliability_score * 0.1
                )
            
            scored_sources.append((source, composite_score))
        
        # Ordenar por score (maior primeiro)
        scored_sources.sort(key=lambda x: x[1], reverse=True)
        
        return scored_sources[0][0]
    
    def _select_cost_optimized(self, sources: List[SourceInfo], context: RequestContext) -> SourceInfo:
        """Seleção otimizada por custo."""
        if not sources:
            return None
        
        # Filtrar fontes dentro do limite de custo
        affordable_sources = sources
        if context.cost_limit:
            affordable_sources = [
                s for s in sources 
                if s.cost_per_request <= context.cost_limit
            ]
        
        if not affordable_sources:
            affordable_sources = sources  # Fallback
        
        # Ordenar por custo (menor primeiro)
        affordable_sources.sort(key=lambda x: x.cost_per_request)
        
        return affordable_sources[0]
    
    def _calculate_performance_score(self, source: SourceInfo) -> float:
        """Calcula score de performance de uma fonte."""
        # Baseado em tempo de resposta e taxa de sucesso
        response_score = 1.0 / max(1.0, source.metrics.avg_response_time / 1000.0)
        success_score = source.metrics.success_rate
        quality_score = source.metrics.data_quality_score
        
        return (response_score * 0.4 + success_score * 0.4 + quality_score * 0.2)
    
    def _calculate_load_score(self, source: SourceInfo) -> float:
        """Calcula score de carga de uma fonte (maior = menos carregada)."""
        if source.name not in self.load_metrics:
            return 1.0  # Assumir sem carga se não há métricas
        
        load_score = self.load_metrics[source.name].calculate_load_score()
        return 1.0 - load_score  # Inverter (menos carga = melhor)
    
    def _calculate_reliability_score(self, source: SourceInfo) -> float:
        """Calcula score de confiabilidade de uma fonte."""
        uptime_score = source.metrics.uptime_percentage / 100.0
        failure_penalty = max(0, 1.0 - source.metrics.consecutive_failures / 10.0)
        
        return (uptime_score * 0.7 + failure_penalty * 0.3)
    
    def _calculate_cost_score(self, source: SourceInfo, context: RequestContext) -> float:
        """Calcula score de custo de uma fonte (maior = mais barato)."""
        if source.cost_per_request == 0:
            return 1.0  # Fonte gratuita
        
        # Normalizar custo (assumindo máximo de $1.00 por requisição)
        max_cost = context.cost_limit or 1.0
        cost_score = 1.0 - (source.cost_per_request / max_cost)
        
        return max(0.0, cost_score)
    
    async def release_source(self, source_name: str, success: bool, response_time: float = 0):
        """Libera uma fonte após uso e atualiza métricas."""
        if source_name in self.load_metrics:
            # Decrementar conexões ativas
            self.load_metrics[source_name].active_connections = max(
                0, self.load_metrics[source_name].active_connections - 1
            )
            
            # Atualizar métricas de performance
            if success:
                # Atualizar tempo de resposta médio
                current_avg = getattr(self.load_metrics[source_name], 'avg_response_time', 0)
                if current_avg == 0:
                    self.load_metrics[source_name].avg_response_time = response_time
                else:
                    # Média móvel simples
                    self.load_metrics[source_name].avg_response_time = (
                        current_avg * 0.9 + response_time * 0.1
                    )
    
    def get_load_statistics(self) -> Dict[str, Any]:
        """Obtém estatísticas de balanceamento de carga."""
        stats = {
            'strategy': self.strategy.value,
            'total_sources': len(self.source_rotator.sources),
            'available_sources': len([
                s for s in self.source_rotator.sources.values() 
                if s.is_available()
            ]),
            'overloaded_sources': len([
                name for name in self.source_rotator.sources.keys()
                if self._is_source_overloaded(name)
            ]),
            'source_metrics': {}
        }
        
        for name, metrics in self.load_metrics.items():
            stats['source_metrics'][name] = {
                'active_connections': metrics.active_connections,
                'requests_per_second': metrics.requests_per_second,
                'load_score': metrics.calculate_load_score(),
                'queue_length': metrics.queue_length,
                'last_updated': metrics.last_updated
            }
        
        return stats
    
    def set_strategy(self, strategy: LoadBalancingStrategy):
        """Altera a estratégia de balanceamento."""
        self.strategy = strategy
        logger.info(f"Estratégia de balanceamento alterada para {strategy.value}")
    
    def reset_counters(self):
        """Reseta contadores de round-robin."""
        self.round_robin_counters.clear()
        self.weighted_counters.clear()
        logger.info("Contadores de balanceamento resetados")
    
    async def health_check_sources(self):
        """Executa health check em todas as fontes e atualiza métricas."""
        for source_name, source in self.source_rotator.sources.items():
            if hasattr(source.collector, 'test_connection'):
                try:
                    start_time = datetime.now(timezone.utc)
                    is_healthy = await source.collector.test_connection()
                    response_time = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                    
                    # Atualizar métricas baseadas no health check
                    if source_name not in self.load_metrics:
                        self.load_metrics[source_name] = LoadMetrics()
                    
                    if is_healthy:
                        # Fonte saudável - pode reduzir carga artificialmente
                        if self.load_metrics[source_name].active_connections == 0:
                            self.load_metrics[source_name].requests_per_second *= 0.9
                    else:
                        # Fonte não saudável - aumentar carga artificialmente
                        self.load_metrics[source_name].requests_per_second += 10
                    
                    self.load_metrics[source_name].last_updated = datetime.now(timezone.utc)
                
                except Exception as e:
                    logger.debug(f"Erro no health check da fonte {source_name}: {e}")
    
    def simulate_load_metrics(self):
        """Simula métricas de carga para teste (remover em produção)."""
        for source_name in self.source_rotator.sources.keys():
            if source_name not in self.load_metrics:
                self.load_metrics[source_name] = LoadMetrics()
            
            # Simular variações aleatórias
            metrics = self.load_metrics[source_name]
            metrics.cpu_usage = max(0, min(100, metrics.cpu_usage + random.uniform(-5, 5)))
            metrics.memory_usage = max(0, min(100, metrics.memory_usage + random.uniform(-3, 3)))
            metrics.requests_per_second = max(0, metrics.requests_per_second + random.uniform(-10, 10))
            metrics.last_updated = datetime.now(timezone.utc)