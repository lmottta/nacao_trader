"""Sistema de Métricas com Prometheus para o Nação Trader.

Implementa coleta e exposição de métricas para monitoramento do sistema
de coleta de dados e geração de sinais.
"""

import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
import logging
from functools import wraps
import asyncio
from datetime import datetime, timedelta

try:
    from prometheus_client import (
        Counter, Histogram, Gauge, Summary, Info,
        CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST,
        start_http_server, push_to_gateway
    )
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logging.warning("Prometheus client não disponível. Métricas desabilitadas.")

from ..utils.config import settings


class MetricType(Enum):
    """Tipos de métricas disponíveis."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"
    INFO = "info"


@dataclass
class MetricConfig:
    """Configuração de métrica."""
    name: str
    description: str
    labels: List[str] = None
    buckets: List[float] = None  # Para histogramas
    
    def __post_init__(self):
        if self.labels is None:
            self.labels = []
        if self.buckets is None:
            self.buckets = [0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 25.0, 50.0, 100.0]


class MetricsCollector:
    """Coletor de métricas com Prometheus."""
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        self.enabled = PROMETHEUS_AVAILABLE
        self.start_time = time.time()  # Para rastrear uptime
        
        if not self.enabled:
            self.logger = logging.getLogger(__name__)
            self.logger.warning("Métricas desabilitadas - Prometheus não disponível")
            return
        
        self.registry = registry or CollectorRegistry()
        self.metrics: Dict[str, Any] = {}
        self.logger = logging.getLogger(__name__)
        
        # Métricas do sistema
        self._init_system_metrics()
        
        # Métricas de coleta de dados
        self._init_data_collection_metrics()
        
        # Métricas de cache
        self._init_cache_metrics()
        
        # Métricas de circuit breakers
        self._init_circuit_breaker_metrics()
        
        # Métricas de sinais
        self._init_signal_metrics()
        
        self.logger.info("Sistema de métricas inicializado")
    
    def _init_system_metrics(self):
        """Inicializa métricas do sistema."""
        if not self.enabled:
            return
        
        # Informações do sistema
        self.metrics['system_info'] = Info(
            'nacao_trader_system_info',
            'Informações do sistema Nação Trader',
            registry=self.registry
        )
        
        # Uptime do sistema
        self.metrics['system_uptime'] = Gauge(
            'nacao_trader_uptime_seconds',
            'Tempo de atividade do sistema em segundos',
            registry=self.registry
        )
        
        # Uso de memória
        self.metrics['memory_usage'] = Gauge(
            'nacao_trader_memory_usage_bytes',
            'Uso de memória em bytes',
            ['component'],
            registry=self.registry
        )
        
        # CPU usage
        self.metrics['cpu_usage'] = Gauge(
            'nacao_trader_cpu_usage_percent',
            'Uso de CPU em porcentagem',
            ['component'],
            registry=self.registry
        )
    
    def _init_data_collection_metrics(self):
        """Inicializa métricas de coleta de dados."""
        if not self.enabled:
            return
        
        # Requisições de API
        self.metrics['api_requests_total'] = Counter(
            'nacao_trader_api_requests_total',
            'Total de requisições de API',
            ['provider', 'endpoint', 'status'],
            registry=self.registry
        )
        
        # Duração das requisições
        self.metrics['api_request_duration'] = Histogram(
            'nacao_trader_api_request_duration_seconds',
            'Duração das requisições de API',
            ['provider', 'endpoint'],
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
            registry=self.registry
        )
        
        # Rate limits
        self.metrics['rate_limit_hits'] = Counter(
            'nacao_trader_rate_limit_hits_total',
            'Total de rate limits atingidos',
            ['provider'],
            registry=self.registry
        )
        
        # Dados coletados
        self.metrics['data_points_collected'] = Counter(
            'nacao_trader_data_points_collected_total',
            'Total de pontos de dados coletados',
            ['source', 'symbol', 'data_type'],
            registry=self.registry
        )
        
        # Erros de coleta
        self.metrics['collection_errors'] = Counter(
            'nacao_trader_collection_errors_total',
            'Total de erros na coleta de dados',
            ['source', 'error_type'],
            registry=self.registry
        )
        
        # Latência da coleta
        self.metrics['collection_latency'] = Summary(
            'nacao_trader_collection_latency_seconds',
            'Latência da coleta de dados',
            ['source'],
            registry=self.registry
        )
    
    def _init_cache_metrics(self):
        """Inicializa métricas de cache."""
        if not self.enabled:
            return
        
        # Cache hits/misses
        self.metrics['cache_operations'] = Counter(
            'nacao_trader_cache_operations_total',
            'Total de operações de cache',
            ['level', 'operation', 'result'],
            registry=self.registry
        )
        
        # Tamanho do cache
        self.metrics['cache_size'] = Gauge(
            'nacao_trader_cache_size_bytes',
            'Tamanho do cache em bytes',
            ['level'],
            registry=self.registry
        )
        
        # Entradas no cache
        self.metrics['cache_entries'] = Gauge(
            'nacao_trader_cache_entries_count',
            'Número de entradas no cache',
            ['level'],
            registry=self.registry
        )
        
        # Taxa de hit do cache
        self.metrics['cache_hit_rate'] = Gauge(
            'nacao_trader_cache_hit_rate_percent',
            'Taxa de hit do cache em porcentagem',
            ['level'],
            registry=self.registry
        )
        
        # Evictions
        self.metrics['cache_evictions'] = Counter(
            'nacao_trader_cache_evictions_total',
            'Total de evictions do cache',
            ['level', 'reason'],
            registry=self.registry
        )
    
    def _init_circuit_breaker_metrics(self):
        """Inicializa métricas de circuit breakers."""
        if not self.enabled:
            return
        
        # Estado dos circuit breakers
        self.metrics['circuit_breaker_state'] = Gauge(
            'nacao_trader_circuit_breaker_state',
            'Estado do circuit breaker (0=closed, 1=open, 2=half-open)',
            ['name'],
            registry=self.registry
        )
        
        # Transições de estado
        self.metrics['circuit_breaker_transitions'] = Counter(
            'nacao_trader_circuit_breaker_transitions_total',
            'Total de transições de estado',
            ['name', 'from_state', 'to_state'],
            registry=self.registry
        )
        
        # Falhas
        self.metrics['circuit_breaker_failures'] = Counter(
            'nacao_trader_circuit_breaker_failures_total',
            'Total de falhas registradas',
            ['name', 'failure_type'],
            registry=self.registry
        )
        
        # Sucessos
        self.metrics['circuit_breaker_successes'] = Counter(
            'nacao_trader_circuit_breaker_successes_total',
            'Total de sucessos registrados',
            ['name'],
            registry=self.registry
        )
        
        # Tempo de resposta
        self.metrics['circuit_breaker_response_time'] = Histogram(
            'nacao_trader_circuit_breaker_response_time_seconds',
            'Tempo de resposta das operações',
            ['name'],
            registry=self.registry
        )
    
    def _init_signal_metrics(self):
        """Inicializa métricas de sinais."""
        if not self.enabled:
            return
        
        # Sinais gerados
        self.metrics['signals_generated'] = Counter(
            'nacao_trader_signals_generated_total',
            'Total de sinais gerados',
            ['symbol', 'direction', 'confidence_level'],
            registry=self.registry
        )
        
        # Tempo de processamento de sinais
        self.metrics['signal_processing_time'] = Histogram(
            'nacao_trader_signal_processing_time_seconds',
            'Tempo de processamento de sinais',
            ['symbol'],
            registry=self.registry
        )
        
        # Acurácia dos sinais
        self.metrics['signal_accuracy'] = Gauge(
            'nacao_trader_signal_accuracy_percent',
            'Acurácia dos sinais em porcentagem',
            ['symbol', 'timeframe'],
            registry=self.registry
        )
        
        # Modelos ML
        self.metrics['ml_model_predictions'] = Counter(
            'nacao_trader_ml_model_predictions_total',
            'Total de predições do modelo ML',
            ['model_name', 'symbol'],
            registry=self.registry
        )
        
        # Confiança do modelo
        self.metrics['ml_model_confidence'] = Histogram(
            'nacao_trader_ml_model_confidence',
            'Distribuição da confiança do modelo ML',
            ['model_name'],
            buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            registry=self.registry
        )
    
    def record_api_request(self, provider: str, endpoint: str, status: str, duration: float):
        """Registra requisição de API."""
        if not self.enabled:
            return
        
        self.metrics['api_requests_total'].labels(
            provider=provider, endpoint=endpoint, status=status
        ).inc()
        
        self.metrics['api_request_duration'].labels(
            provider=provider, endpoint=endpoint
        ).observe(duration)
    
    def record_rate_limit(self, provider: str):
        """Registra rate limit atingido."""
        if not self.enabled:
            return
        
        self.metrics['rate_limit_hits'].labels(provider=provider).inc()
    
    def record_data_collection(self, source: str, symbol: str, data_type: str, count: int = 1):
        """Registra coleta de dados."""
        if not self.enabled:
            return
        
        self.metrics['data_points_collected'].labels(
            source=source, symbol=symbol, data_type=data_type
        ).inc(count)
    
    def record_collection_error(self, source: str, error_type: str):
        """Registra erro de coleta."""
        if not self.enabled:
            return
        
        self.metrics['collection_errors'].labels(
            source=source, error_type=error_type
        ).inc()
    
    def record_collection_latency(self, source: str, latency: float):
        """Registra latência de coleta."""
        if not self.enabled:
            return
        
        self.metrics['collection_latency'].labels(source=source).observe(latency)
    
    def record_cache_operation(self, level: str, operation: str, result: str):
        """Registra operação de cache."""
        if not self.enabled:
            return
        
        self.metrics['cache_operations'].labels(
            level=level, operation=operation, result=result
        ).inc()
    
    def update_cache_metrics(self, level: str, size_bytes: int, entries_count: int, hit_rate: float):
        """Atualiza métricas de cache."""
        if not self.enabled:
            return
        
        self.metrics['cache_size'].labels(level=level).set(size_bytes)
        self.metrics['cache_entries'].labels(level=level).set(entries_count)
        self.metrics['cache_hit_rate'].labels(level=level).set(hit_rate)
    
    def record_cache_eviction(self, level: str, reason: str):
        """Registra eviction de cache."""
        if not self.enabled:
            return
        
        self.metrics['cache_evictions'].labels(level=level, reason=reason).inc()
    
    def update_circuit_breaker_state(self, name: str, state: str):
        """Atualiza estado do circuit breaker."""
        if not self.enabled:
            return
        
        state_mapping = {'closed': 0, 'open': 1, 'half_open': 2, 'forced_open': 1}
        state_value = state_mapping.get(state, 0)
        
        self.metrics['circuit_breaker_state'].labels(name=name).set(state_value)
    
    def record_circuit_breaker_transition(self, name: str, from_state: str, to_state: str):
        """Registra transição de circuit breaker."""
        if not self.enabled:
            return
        
        self.metrics['circuit_breaker_transitions'].labels(
            name=name, from_state=from_state, to_state=to_state
        ).inc()
    
    def record_circuit_breaker_failure(self, name: str, failure_type: str):
        """Registra falha de circuit breaker."""
        if not self.enabled:
            return
        
        self.metrics['circuit_breaker_failures'].labels(
            name=name, failure_type=failure_type
        ).inc()
    
    def record_circuit_breaker_success(self, name: str, response_time: float):
        """Registra sucesso de circuit breaker."""
        if not self.enabled:
            return
        
        self.metrics['circuit_breaker_successes'].labels(name=name).inc()
        self.metrics['circuit_breaker_response_time'].labels(name=name).observe(response_time)
    
    def record_signal_generation(self, symbol: str, direction: str, confidence: float):
        """Registra geração de sinal."""
        if not self.enabled:
            return
        
        # Classifica nível de confiança
        if confidence >= 0.8:
            confidence_level = "high"
        elif confidence >= 0.6:
            confidence_level = "medium"
        else:
            confidence_level = "low"
        
        self.metrics['signals_generated'].labels(
            symbol=symbol, direction=direction, confidence_level=confidence_level
        ).inc()
    
    def record_signal_processing_time(self, symbol: str, processing_time: float):
        """Registra tempo de processamento de sinal."""
        if not self.enabled:
            return
        
        self.metrics['signal_processing_time'].labels(symbol=symbol).observe(processing_time)
    
    def update_signal_accuracy(self, symbol: str, timeframe: str, accuracy: float):
        """Atualiza acurácia dos sinais."""
        if not self.enabled:
            return
        
        self.metrics['signal_accuracy'].labels(
            symbol=symbol, timeframe=timeframe
        ).set(accuracy * 100)  # Converte para porcentagem
    
    def record_ml_prediction(self, model_name: str, symbol: str, confidence: float):
        """Registra predição do modelo ML."""
        if not self.enabled:
            return
        
        self.metrics['ml_model_predictions'].labels(
            model_name=model_name, symbol=symbol
        ).inc()
        
        self.metrics['ml_model_confidence'].labels(
            model_name=model_name
        ).observe(confidence)
    
    def update_system_info(self, info: Dict[str, str]):
        """Atualiza informações do sistema."""
        if not self.enabled:
            return
        
        self.metrics['system_info'].info(info)
    
    def update_uptime(self, uptime_seconds: float):
        """Atualiza uptime do sistema."""
        if not self.enabled:
            return
        
        self.metrics['system_uptime'].set(uptime_seconds)
    
    def update_memory_usage(self, component: str, usage_bytes: int):
        """Atualiza uso de memória."""
        if not self.enabled:
            return
        
        self.metrics['memory_usage'].labels(component=component).set(usage_bytes)
    
    def update_cpu_usage(self, component: str, usage_percent: float):
        """Atualiza uso de CPU."""
        if not self.enabled:
            return
        
        self.metrics['cpu_usage'].labels(component=component).set(usage_percent)
    
    def get_metrics(self) -> str:
        """Retorna métricas no formato Prometheus."""
        if not self.enabled:
            return "# Métricas não disponíveis\n"
        
        return generate_latest(self.registry).decode('utf-8')
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Retorna métricas do sistema em formato dict."""
        if not self.enabled:
            return {"error": "Métricas não disponíveis"}
        
        try:
            # Coleta métricas básicas do sistema
            import psutil
            
            return {
                "memory_usage": psutil.virtual_memory().percent,
                "cpu_usage": psutil.cpu_percent(),
                "disk_usage": psutil.disk_usage('/').percent if hasattr(psutil.disk_usage('/'), 'percent') else 0,
                "process_count": len(psutil.pids()),
                "uptime": time.time() - self.start_time if hasattr(self, 'start_time') else 0
            }
        except Exception as e:
            self.logger.error(f"Erro ao coletar métricas do sistema: {e}")
            return {"error": str(e)}
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Retorna resumo das métricas coletadas."""
        if not self.enabled:
            return {"error": "Métricas não disponíveis"}
        
        try:
            return {
                "api_calls": self._get_metric_value('api_calls_total'),
                "cache_operations": self._get_metric_value('cache_operations_total'),
                "signals_generated": self._get_metric_value('signals_generated'),
                "system": self.get_system_metrics()
            }
        except Exception as e:
            self.logger.error(f"Erro ao gerar resumo de métricas: {e}")
            return {"error": str(e)}
    
    def _get_metric_value(self, metric_name: str) -> float:
        """Obtém valor de uma métrica específica."""
        try:
            if metric_name in self.metrics:
                metric = self.metrics[metric_name]
                # Para métricas Counter, retorna o valor atual
                if hasattr(metric, '_value'):
                    return metric._value.get()
                # Para métricas com labels, soma todos os valores
                elif hasattr(metric, '_metrics'):
                    return sum(m._value.get() for m in metric._metrics.values())
            return 0.0
        except Exception:
            return 0.0
    
    def get_data_collection_metrics(self) -> Dict[str, Any]:
        """Retorna métricas de coleta de dados."""
        if not self.enabled:
            return {"error": "Métricas não disponíveis"}
        
        try:
            return {
                "total_requests": self._get_metric_value('api_requests_total'),
                "successful_requests": self._get_metric_value('api_requests_total'),  # Filtrar por status success
                "failed_requests": self._get_metric_value('collection_errors'),
                "data_points_collected": self._get_metric_value('data_points_collected'),
                "rate_limit_hits": self._get_metric_value('rate_limit_hits'),
                "avg_request_duration": 0.0  # Seria calculado a partir do histogram
            }
        except Exception as e:
            self.logger.error(f"Erro ao obter métricas de coleta: {e}")
            return {"error": str(e)}
    
    def get_cache_metrics(self) -> Dict[str, Any]:
        """Retorna métricas do cache."""
        if not self.enabled:
            return {"error": "Métricas não disponíveis"}
        
        try:
            return {
                "total_operations": self._get_metric_value('cache_operations'),
                "hit_rate": 0.0,  # Seria calculado a partir das operações
                "cache_size_bytes": self._get_metric_value('cache_size'),
                "cache_entries": self._get_metric_value('cache_entries'),
                "evictions": self._get_metric_value('cache_evictions')
            }
        except Exception as e:
            self.logger.error(f"Erro ao obter métricas de cache: {e}")
            return {"error": str(e)}
    
    def get_circuit_breaker_metrics(self) -> Dict[str, Any]:
        """Retorna métricas dos circuit breakers."""
        if not self.enabled:
            return {"error": "Métricas não disponíveis"}
        
        try:
            return {
                "total_breakers": len([m for name, m in self.metrics.items() if 'circuit_breaker' in name]),
                "open_breakers": 0,  # Seria calculado verificando estados
                "total_failures": self._get_metric_value('circuit_breaker_failures'),
                "state_transitions": self._get_metric_value('circuit_breaker_transitions')
            }
        except Exception as e:
            self.logger.error(f"Erro ao obter métricas de circuit breaker: {e}")
            return {"error": str(e)}
    
    def start_http_server(self, port: int = 8001):
        """Inicia servidor HTTP para exposição de métricas."""
        if not self.enabled:
            self.logger.warning("Não é possível iniciar servidor de métricas - Prometheus não disponível")
            return
        
        try:
            start_http_server(port, registry=self.registry)
            self.logger.info(f"Servidor de métricas iniciado na porta {port}")
        except Exception as e:
            self.logger.error(f"Erro ao iniciar servidor de métricas: {e}")
    
    async def push_to_gateway(self, gateway_url: str, job_name: str = "nacao_trader"):
        """Envia métricas para Pushgateway."""
        if not self.enabled:
            return
        
        try:
            push_to_gateway(gateway_url, job=job_name, registry=self.registry)
            self.logger.debug(f"Métricas enviadas para {gateway_url}")
        except Exception as e:
            self.logger.error(f"Erro ao enviar métricas para gateway: {e}")


# Decorator para medir tempo de execução
def measure_time(metric_name: str, labels: Dict[str, str] = None):
    """Decorator para medir tempo de execução."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Registra métrica de sucesso
                if hasattr(func, '_metrics_collector'):
                    collector = func._metrics_collector
                    if metric_name in collector.metrics:
                        metric = collector.metrics[metric_name]
                        if labels:
                            metric.labels(**labels).observe(duration)
                        else:
                            metric.observe(duration)
                
                return result
            except Exception as e:
                duration = time.time() - start_time
                
                # Registra métrica de erro
                if hasattr(func, '_metrics_collector'):
                    collector = func._metrics_collector
                    error_labels = {**(labels or {}), 'status': 'error'}
                    if metric_name in collector.metrics:
                        metric = collector.metrics[metric_name]
                        metric.labels(**error_labels).observe(duration)
                
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                # Registra métrica de sucesso
                if hasattr(func, '_metrics_collector'):
                    collector = func._metrics_collector
                    if metric_name in collector.metrics:
                        metric = collector.metrics[metric_name]
                        if labels:
                            metric.labels(**labels).observe(duration)
                        else:
                            metric.observe(duration)
                
                return result
            except Exception as e:
                duration = time.time() - start_time
                
                # Registra métrica de erro
                if hasattr(func, '_metrics_collector'):
                    collector = func._metrics_collector
                    error_labels = {**(labels or {}), 'status': 'error'}
                    if metric_name in collector.metrics:
                        metric = collector.metrics[metric_name]
                        metric.labels(**error_labels).observe(duration)
                
                raise
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Instância global do coletor de métricas
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Retorna instância global do coletor de métricas."""
    global _metrics_collector
    
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    
    return _metrics_collector


def init_metrics_server(port: int = 8001):
    """Inicializa servidor de métricas."""
    collector = get_metrics_collector()
    collector.start_http_server(port)
    
    # Atualiza informações do sistema
    collector.update_system_info({
        'version': '1.0.0',
        'environment': 'production' if not settings.DEBUG else 'development',
        'component': 'nacao_trader_motor'
    })