"""Gerenciador de Coletores Avançado para o Nação Trader.

Integra cache inteligente, circuit breakers e métricas para
melhorar a resiliência e performance do sistema de coleta de dados.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
from contextlib import asynccontextmanager

from ..cache.intelligent_cache import get_cache, IntelligentCache
from ..resilience.circuit_breaker import (
    get_circuit_breaker, AdvancedCircuitBreaker, CircuitBreakerConfig,
    CircuitBreakerException
)
from ..monitoring.metrics import get_metrics_collector, MetricsCollector
from ..utils.config import settings

# Importações dos coletores existentes
from .finnhub_collector import get_finnhub_collector
from .yahoo_finance_collector import get_yahoo_finance_collector
from .realtime_market_data import RealtimeMarketData

# Novos coletores da Fase 2
from ..scraping.web_scraping_collector import WebScrapingCollector
from ..websocket.websocket_collector import WebSocketCollector
from ..websocket.binance_websocket import BinanceWebSocketCollector
from ..public_data.fred_collector import FREDCollector
from ..public_data.banco_central_collector import BancoCentralCollector
from ..validation.cross_validator import CrossValidator
from ..rotation.source_rotator import SourceRotator
from ..resilience.fallback_system import get_fallback_system, FallbackSystem, FallbackConfig


class CollectorType(Enum):
    """Tipos de coletores disponíveis."""
    YAHOO_FINANCE = "yahoo_finance"
    FINNHUB = "finnhub"
    REALTIME = "realtime"
    COINGECKO = "coingecko"
    WEB_SCRAPING = "web_scraping"
    WEBSOCKET = "websocket"
    BINANCE_WEBSOCKET = "binance_websocket"
    FRED = "fred"
    BANCO_CENTRAL = "banco_central"
    PUBLIC_DATA = "public_data"


class CollectorStatus(Enum):
    """Status dos coletores."""
    IDLE = "idle"
    RUNNING = "running"
    ERROR = "error"
    DISABLED = "disabled"
    MAINTENANCE = "maintenance"


@dataclass
class CollectorConfig:
    """Configuração de um coletor."""
    name: str
    collector_type: CollectorType
    enabled: bool = True
    priority: int = 1  # 1 = alta, 2 = média, 3 = baixa
    max_retries: int = 3
    retry_delay: float = 5.0
    timeout: float = 30.0
    rate_limit: Optional[float] = None  # Requisições por segundo
    cache_ttl: int = 300  # TTL do cache em segundos
    
    # Configuração do circuit breaker
    circuit_breaker_config: Optional[CircuitBreakerConfig] = None
    
    # Símbolos/ativos para coletar
    symbols: List[str] = field(default_factory=list)
    
    # Configurações específicas
    specific_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CollectorStats:
    """Estatísticas de um coletor."""
    name: str
    status: CollectorStatus = CollectorStatus.IDLE
    last_run: Optional[datetime] = None
    last_success: Optional[datetime] = None
    last_error: Optional[str] = None
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    average_duration: float = 0.0
    data_points_collected: int = 0
    cache_hit_rate: float = 0.0
    circuit_breaker_state: str = "closed"


class CollectorManager:
    """Gerenciador avançado de coletores com resiliência."""
    
    def __init__(self):
        self.cache: Optional[IntelligentCache] = None
        self.metrics: Optional[MetricsCollector] = None
        
        # Configurações dos coletores
        self.collectors_config: Dict[str, CollectorConfig] = {}
        self.collectors_stats: Dict[str, CollectorStats] = {}
        
        # Circuit breakers por coletor
        self.circuit_breakers: Dict[str, AdvancedCircuitBreaker] = {}
        
        # Instâncias dos coletores
        self.collector_instances: Dict[str, Any] = {}
        
        # Controle de execução
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.shutdown_event = asyncio.Event()
        
        # Rate limiting
        self.rate_limiters: Dict[str, asyncio.Semaphore] = {}
        self.last_request_times: Dict[str, float] = {}
        
        # Novos componentes da Fase 2
        self.cross_validator: Optional[CrossValidator] = None
        self.source_rotator: Optional[SourceRotator] = None
        self.fallback_system: Optional[FallbackSystem] = None
        self.fallback_enabled = True
        self.validation_enabled = True
        
        # Logger
        self.logger = logging.getLogger(__name__)
        
        # Inicializar configurações padrão
        self._init_default_configs()
    
    async def initialize(self):
        """Inicializa o gerenciador de coletores."""
        # Inicializar componentes
        self.cache = await get_cache()
        self.metrics = get_metrics_collector()
        
        # Inicializar novos componentes da Fase 2
        self.cross_validator = CrossValidator()
        self.source_rotator = SourceRotator()
        self.fallback_system = await get_fallback_system()
        
        # Inicializar circuit breakers
        for name, config in self.collectors_config.items():
            cb_config = config.circuit_breaker_config or CircuitBreakerConfig()
            self.circuit_breakers[name] = get_circuit_breaker(f"collector_{name}", cb_config)
            
            # Inicializar rate limiter
            if config.rate_limit:
                # Converter para requisições por segundo em semáforo
                max_concurrent = max(1, int(config.rate_limit))
                self.rate_limiters[name] = asyncio.Semaphore(max_concurrent)
            
            # Inicializar estatísticas
            self.collectors_stats[name] = CollectorStats(name=name)
        
        # Inicializar instâncias dos coletores
        await self._init_collector_instances()
        
        # Configurar rotação de fontes
        await self._setup_source_rotation()
        
        self.logger.info("Gerenciador de coletores inicializado com componentes da Fase 2")
    
    def _init_default_configs(self):
        """Inicializa configurações padrão dos coletores."""
        # Yahoo Finance
        self.collectors_config["yahoo_finance"] = CollectorConfig(
            name="yahoo_finance",
            collector_type=CollectorType.YAHOO_FINANCE,
            priority=1,
            timeout=30.0,
            rate_limit=1.0,  # 1 req/sec
            cache_ttl=300,
            circuit_breaker_config=CircuitBreakerConfig(
                failure_threshold=5,
                open_timeout=60.0,
                timeout_threshold=30.0
            ),
            symbols=[
                "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA",
                "EURUSD=X", "GBPUSD=X", "USDJPY=X", "^GSPC", "^DJI"
            ]
        )
        
        # Finnhub
        self.collectors_config["finnhub"] = CollectorConfig(
            name="finnhub",
            collector_type=CollectorType.FINNHUB,
            priority=2,
            timeout=20.0,
            rate_limit=0.5,  # 0.5 req/sec (rate limit mais conservador)
            cache_ttl=600,
            circuit_breaker_config=CircuitBreakerConfig(
                failure_threshold=3,
                open_timeout=120.0,
                timeout_threshold=20.0
            ),
            enabled=bool(getattr(settings, 'FINNHUB_API_KEY', None))
        )
        
        # Realtime Market Data
        self.collectors_config["realtime"] = CollectorConfig(
            name="realtime",
            collector_type=CollectorType.REALTIME,
            priority=1,
            timeout=15.0,
            rate_limit=2.0,  # 2 req/sec
            cache_ttl=60,  # Cache mais curto para dados em tempo real
            circuit_breaker_config=CircuitBreakerConfig(
                failure_threshold=5,
                open_timeout=30.0,
                timeout_threshold=15.0
            )
        )
        
        # Web Scraping Collector
        self.collectors_config["web_scraping"] = CollectorConfig(
            name="web_scraping",
            collector_type=CollectorType.WEB_SCRAPING,
            priority=2,
            timeout=30.0,
            rate_limit=0.5,  # 0.5 req/sec para evitar detecção
            cache_ttl=300,
            circuit_breaker_config=CircuitBreakerConfig(
                failure_threshold=3,
                open_timeout=300.0,
                timeout_threshold=30.0
            ),
            symbols=[
                "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA",
                "EURUSD=X", "GBPUSD=X", "USDJPY=X", "^GSPC", "^DJI"
            ]
        )
        
        # Binance WebSocket
        self.collectors_config["binance_websocket"] = CollectorConfig(
            name="binance_websocket",
            collector_type=CollectorType.BINANCE_WEBSOCKET,
            priority=1,
            timeout=60.0,
            rate_limit=None,  # WebSocket não tem rate limit tradicional
            cache_ttl=30,  # Cache muito curto para dados em tempo real
            circuit_breaker_config=CircuitBreakerConfig(
                failure_threshold=3,
                open_timeout=120.0,
                timeout_threshold=60.0
            ),
            symbols=["BTCUSDT", "ETHUSDT", "ADAUSDT", "DOTUSDT", "LINKUSDT"]
        )
        
        # FRED Collector
        self.collectors_config["fred"] = CollectorConfig(
            name="fred",
            collector_type=CollectorType.FRED,
            priority=3,
            timeout=20.0,
            rate_limit=0.2,  # 0.2 req/sec (5 req/min)
            cache_ttl=3600,  # 1 hora para dados econômicos
            circuit_breaker_config=CircuitBreakerConfig(
                failure_threshold=2,
                open_timeout=600.0,
                timeout_threshold=20.0
            ),
            enabled=bool(getattr(settings, 'FRED_API_KEY', None))
        )
        
        # Banco Central Collector
        self.collectors_config["banco_central"] = CollectorConfig(
            name="banco_central",
            collector_type=CollectorType.BANCO_CENTRAL,
            priority=3,
            timeout=25.0,
            rate_limit=0.3,  # 0.3 req/sec
            cache_ttl=3600,  # 1 hora para dados econômicos
            circuit_breaker_config=CircuitBreakerConfig(
                failure_threshold=2,
                open_timeout=600.0,
                timeout_threshold=25.0
            )
        )
    
    async def _init_collector_instances(self):
        """Inicializa instâncias dos coletores."""
        for name, config in self.collectors_config.items():
            if not config.enabled:
                continue
            
            try:
                if config.collector_type == CollectorType.YAHOO_FINANCE:
                    self.collector_instances[name] = get_yahoo_finance_collector()
                elif config.collector_type == CollectorType.FINNHUB:
                    self.collector_instances[name] = get_finnhub_collector()
                elif config.collector_type == CollectorType.REALTIME:
                    self.collector_instances[name] = RealtimeMarketData()
                elif config.collector_type == CollectorType.WEB_SCRAPING:
                    self.collector_instances[name] = WebScrapingCollector(self.cache, self.metrics)
                elif config.collector_type == CollectorType.BINANCE_WEBSOCKET:
                    self.collector_instances[name] = BinanceWebSocketCollector(self.cache, self.metrics)
                elif config.collector_type == CollectorType.FRED:
                    self.collector_instances[name] = FREDCollector(self.cache, self.metrics)
                elif config.collector_type == CollectorType.BANCO_CENTRAL:
                    self.collector_instances[name] = BancoCentralCollector(self.cache, self.metrics)
                
                self.logger.info(f"Coletor {name} inicializado")
            except Exception as e:
                self.logger.error(f"Erro ao inicializar coletor {name}: {e}")
                self.collectors_stats[name].status = CollectorStatus.ERROR
                self.collectors_stats[name].last_error = str(e)
    
    async def _setup_source_rotation(self):
        """Configura o sistema de rotação de fontes."""
        if not self.source_rotator:
            return
        
        # Adicionar fontes ao rotator
        from src.rotation.source_rotator import SourceInfo
        
        for name, config in self.collectors_config.items():
            if config.enabled:
                collector_instance = self.collector_instances.get(name)
                if collector_instance:
                    source_info = SourceInfo(
                        name=name,
                        collector=collector_instance,
                        priority=config.priority,
                        weight=1.0 / config.priority,  # Peso inversamente proporcional à prioridade
                        supported_symbols=config.symbols,
                        rate_limit=config.rate_limit,
                        timeout=config.timeout
                    )
                    self.source_rotator.add_source(source_info)
        
        self.logger.info(f"Rotação de fontes configurada com {len(self.collector_instances)} coletores")
    
    @asynccontextmanager
    async def _rate_limit_context(self, collector_name: str):
        """Context manager para rate limiting."""
        config = self.collectors_config[collector_name]
        
        if config.rate_limit and collector_name in self.rate_limiters:
            # Aguardar semáforo
            async with self.rate_limiters[collector_name]:
                # Verificar tempo desde última requisição
                now = time.time()
                last_request = self.last_request_times.get(collector_name, 0)
                min_interval = 1.0 / config.rate_limit
                
                time_since_last = now - last_request
                if time_since_last < min_interval:
                    await asyncio.sleep(min_interval - time_since_last)
                
                self.last_request_times[collector_name] = time.time()
                yield
        else:
            yield
    
    async def _execute_with_resilience(self, 
                                     collector_name: str, 
                                     operation: Callable,
                                     *args, **kwargs) -> Any:
        """Executa operação com resiliência (cache, circuit breaker, métricas)."""
        config = self.collectors_config[collector_name]
        circuit_breaker = self.circuit_breakers[collector_name]
        stats = self.collectors_stats[collector_name]
        
        # Gerar chave de cache
        cache_key = f"{collector_name}:{operation.__name__}:{hash(str(args) + str(kwargs))}"
        
        # Tentar cache primeiro
        if self.cache:
            cached_result = await self.cache.get(cache_key, namespace="collectors")
            if cached_result is not None:
                self.metrics.record_cache_operation("memory", "get", "hit")
                self.logger.debug(f"Cache hit para {collector_name}:{operation.__name__}")
                return cached_result
            else:
                self.metrics.record_cache_operation("memory", "get", "miss")
        
        # Executar com circuit breaker e rate limiting
        start_time = time.time()
        try:
            async with self._rate_limit_context(collector_name):
                result = await circuit_breaker.call(operation, *args, **kwargs)
            
            duration = time.time() - start_time
            
            # Armazenar no cache
            if self.cache and result is not None:
                await self.cache.set(
                    cache_key, result, 
                    ttl=config.cache_ttl, 
                    namespace="collectors"
                )
            
            # Atualizar estatísticas
            stats.successful_runs += 1
            stats.last_success = datetime.now()
            stats.average_duration = (
                (stats.average_duration * (stats.successful_runs - 1) + duration) / 
                stats.successful_runs
            )
            
            # Registrar métricas
            self.metrics.record_api_request(
                provider=collector_name,
                endpoint=operation.__name__,
                status="success",
                duration=duration
            )
            
            return result
            
        except CircuitBreakerException as e:
            # Circuit breaker aberto
            stats.status = CollectorStatus.ERROR
            stats.last_error = f"Circuit breaker aberto: {e}"
            
            self.metrics.record_api_request(
                provider=collector_name,
                endpoint=operation.__name__,
                status="circuit_breaker_open",
                duration=time.time() - start_time
            )
            
            self.logger.warning(f"Circuit breaker aberto para {collector_name}: {e}")
            raise
            
        except Exception as e:
            duration = time.time() - start_time
            
            # Atualizar estatísticas
            stats.failed_runs += 1
            stats.last_error = str(e)
            
            # Registrar métricas
            self.metrics.record_api_request(
                provider=collector_name,
                endpoint=operation.__name__,
                status="error",
                duration=duration
            )
            
            self.metrics.record_collection_error(
                source=collector_name,
                error_type=type(e).__name__
            )
            
            self.logger.error(f"Erro em {collector_name}:{operation.__name__}: {e}")
            raise
        
        finally:
            stats.total_runs += 1
            stats.last_run = datetime.now()
    
    async def collect_data(self, collector_name: str, symbols: Optional[List[str]] = None) -> Dict[str, Any]:
        """Coleta dados de um coletor específico."""
        if collector_name not in self.collectors_config:
            raise ValueError(f"Coletor {collector_name} não configurado")
        
        config = self.collectors_config[collector_name]
        if not config.enabled:
            raise ValueError(f"Coletor {collector_name} está desabilitado")
        
        collector = self.collector_instances.get(collector_name)
        if not collector:
            raise ValueError(f"Instância do coletor {collector_name} não encontrada")
        
        stats = self.collectors_stats[collector_name]
        stats.status = CollectorStatus.RUNNING
        
        try:
            symbols_to_collect = symbols or config.symbols
            results = {}
            
            if config.collector_type == CollectorType.YAHOO_FINANCE:
                # Coleta dados históricos
                historical_data = await self._execute_with_resilience(
                    collector_name,
                    collector.batch_fetch_historical_data,
                    symbols=symbols_to_collect,
                    period="1y",
                    interval="1d"
                )
                results["historical"] = historical_data
                
                # Atualizar informações dos ativos
                await self._execute_with_resilience(
                    collector_name,
                    collector.update_assets_info,
                    symbols_to_collect
                )
                
            elif config.collector_type == CollectorType.FINNHUB:
                # Buscar e armazenar ativos
                await self._execute_with_resilience(
                    collector_name,
                    collector.fetch_and_store_assets
                )
                
                # Atualizar preços
                await self._execute_with_resilience(
                    collector_name,
                    collector.update_asset_prices
                )
                
            elif config.collector_type == CollectorType.REALTIME:
                # Coleta dados em tempo real
                if symbols_to_collect:
                    realtime_data = await self._execute_with_resilience(
                        collector_name,
                        collector.get_bulk_realtime_prices,
                        symbols_to_collect
                    )
                    results["realtime"] = realtime_data
            
            # Contar pontos de dados coletados
            data_points = sum(len(data) if isinstance(data, (list, dict)) else 1 
                            for data in results.values())
            stats.data_points_collected += data_points
            
            self.metrics.record_data_collection(
                source=collector_name,
                symbol="bulk",
                data_type="mixed",
                count=data_points
            )
            
            stats.status = CollectorStatus.IDLE
            return results
            
        except Exception as e:
            stats.status = CollectorStatus.ERROR
            raise
    
    async def collect_with_validation(self, symbol: str, sources: Optional[List[str]] = None) -> Dict[str, Any]:
        """Coleta dados com validação cruzada e fallback automático."""
        if not sources:
            # Usar rotação de fontes para selecionar as melhores
            if self.source_rotator:
                sources = await self.source_rotator.get_best_sources(symbol, max_sources=3)
            else:
                # Fallback para fontes por prioridade
                sources = [name for name, config in sorted(
                    self.collectors_config.items(),
                    key=lambda x: x[1].priority
                ) if config.enabled][:3]
        
        # Coletar dados de múltiplas fontes
        source_data = {}
        for source_name in sources:
            try:
                if source_name in self.collector_instances:
                    data = await self.collect_data(source_name, [symbol])
                    if data:
                        source_data[source_name] = data
            except Exception as e:
                self.logger.warning(f"Erro ao coletar de {source_name} para {symbol}: {e}")
                continue
        
        # Validação cruzada se habilitada
        if self.validation_enabled and self.cross_validator and len(source_data) > 1:
            try:
                validation_result = await self.cross_validator.validate_cross_source(
                    symbol=symbol,
                    source_data=source_data
                )
                
                # Registrar resultado da validação
                await self.metrics.record_counter(
                    "cross_validation_total",
                    labels={
                        "symbol": symbol,
                        "status": validation_result.status.value,
                        "sources_count": str(len(source_data))
                    }
                )
                
                # Se validação falhou, tentar fallback
                if validation_result.status.value in ['INVALID', 'SUSPICIOUS'] and self.fallback_enabled:
                    fallback_data = await self._execute_fallback(symbol, sources)
                    if fallback_data:
                        source_data.update(fallback_data)
                
                return {
                    "symbol": symbol,
                    "data": source_data,
                    "validation": {
                        "status": validation_result.status.value,
                        "confidence": validation_result.confidence,
                        "consensus_value": validation_result.consensus_value,
                        "issues": [issue.description for issue in validation_result.issues]
                    },
                    "timestamp": datetime.now().isoformat()
                }
            
            except Exception as e:
                self.logger.error(f"Erro na validação cruzada para {symbol}: {e}")
        
        # Retornar dados sem validação
        return {
            "symbol": symbol,
            "data": source_data,
            "validation": None,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _execute_fallback(self, symbol: str, used_sources: List[str]) -> Dict[str, Any]:
        """Executa fallback usando o sistema de fallback integrado."""
        if not self.fallback_system:
            return await self._legacy_fallback(symbol, used_sources)
        
        try:
            # Usar sistema de fallback avançado
            fallback_result = await self.fallback_system.execute_fallback(
                symbol=symbol,
                failed_sources=used_sources,
                available_collectors=self.collector_instances,
                collector_configs=self.collectors_config
            )
            
            if fallback_result.success:
                await self.metrics.record_counter(
                    "fallback_success_total",
                    labels={"source": fallback_result.source_used, "symbol": symbol}
                )
                
                self.logger.info(f"Fallback bem-sucedido com {fallback_result.source_used} para {symbol}")
                return {f"{fallback_result.source_used}_fallback": fallback_result.data}
            else:
                await self.metrics.record_counter(
                    "fallback_error_total",
                    labels={"symbol": symbol, "reason": fallback_result.error or "unknown"}
                )
                
                self.logger.warning(f"Fallback falhou para {symbol}: {fallback_result.error}")
                return {}
        
        except Exception as e:
            self.logger.error(f"Erro no sistema de fallback para {symbol}: {e}")
            return await self._legacy_fallback(symbol, used_sources)
    
    async def _legacy_fallback(self, symbol: str, used_sources: List[str]) -> Dict[str, Any]:
        """Fallback legado para compatibilidade."""
        fallback_data = {}
        
        # Obter fontes não utilizadas
        available_sources = [
            name for name, config in self.collectors_config.items()
            if config.enabled and name not in used_sources
        ]
        
        # Ordenar por prioridade
        available_sources.sort(key=lambda x: self.collectors_config[x].priority)
        
        # Tentar até 2 fontes de fallback
        for source_name in available_sources[:2]:
            try:
                data = await self.collect_data(source_name, [symbol])
                if data:
                    fallback_data[f"{source_name}_fallback"] = data
                    
                    await self.metrics.record_counter(
                        "fallback_success_total",
                        labels={"source": source_name, "symbol": symbol}
                    )
                    
                    self.logger.info(f"Fallback bem-sucedido com {source_name} para {symbol}")
            
            except Exception as e:
                await self.metrics.record_counter(
                    "fallback_error_total",
                    labels={"source": source_name, "symbol": symbol}
                )
                self.logger.warning(f"Fallback falhou com {source_name} para {symbol}: {e}")
        
        return fallback_data
    
    async def update_rate_limits(self, source_performance: Dict[str, Dict[str, float]]) -> None:
        """Atualiza rate limits baseado na performance das fontes com algoritmo inteligente."""
        for source_name, performance in source_performance.items():
            if source_name in self.collectors_config:
                config = self.collectors_config[source_name]
                stats = self.collectors_stats[source_name]
                
                # Métricas de performance
                success_rate = performance.get('success_rate', 0.0)
                avg_response_time = performance.get('avg_response_time', 1.0)
                error_rate = performance.get('error_rate', 0.0)
                circuit_breaker_state = self.circuit_breakers[source_name].state.value if source_name in self.circuit_breakers else 'closed'
                
                # Algoritmo inteligente de ajuste
                base_rate = config.rate_limit or 1.0
                
                # Fator de performance (0.1 a 2.0)
                performance_factor = self._calculate_performance_factor(
                    success_rate, avg_response_time, error_rate, circuit_breaker_state
                )
                
                # Fator de histórico (baseado em estatísticas)
                history_factor = self._calculate_history_factor(stats)
                
                # Fator de carga do sistema
                load_factor = self._calculate_load_factor(source_name)
                
                # Calcular novo rate limit
                new_rate_limit = base_rate * performance_factor * history_factor * load_factor
                
                # Aplicar limites mínimos e máximos
                new_rate_limit = max(0.1, min(new_rate_limit, base_rate * 3.0))
                
                # Atualizar configuração
                old_rate_limit = config.rate_limit
                config.rate_limit = new_rate_limit
                
                # Atualizar rate limiter se existir
                if source_name in self.rate_limiters:
                    max_concurrent = max(1, int(new_rate_limit))
                    self.rate_limiters[source_name] = asyncio.Semaphore(max_concurrent)
                
                self.logger.info(
                    f"Rate limit inteligente atualizado para {source_name}: "
                    f"{old_rate_limit:.3f} -> {new_rate_limit:.3f} "
                    f"(perf: {performance_factor:.2f}, hist: {history_factor:.2f}, load: {load_factor:.2f})"
                )
    
    def _calculate_performance_factor(self, success_rate: float, avg_response_time: float, 
                                    error_rate: float, circuit_breaker_state: str) -> float:
        """Calcula fator de performance para ajuste de rate limit."""
        # Base: taxa de sucesso
        factor = success_rate
        
        # Penalizar tempo de resposta alto
        if avg_response_time > 5.0:
            factor *= 0.8
        elif avg_response_time > 10.0:
            factor *= 0.6
        elif avg_response_time > 20.0:
            factor *= 0.4
        
        # Penalizar alta taxa de erro
        factor *= (1 - error_rate * 0.5)
        
        # Penalizar circuit breaker aberto
        if circuit_breaker_state == 'open':
            factor *= 0.2
        elif circuit_breaker_state == 'half_open':
            factor *= 0.5
        
        return max(0.1, min(factor, 2.0))
    
    def _calculate_history_factor(self, stats: CollectorStats) -> float:
        """Calcula fator baseado no histórico de performance."""
        if stats.total_runs == 0:
            return 1.0
        
        # Taxa de sucesso histórica
        historical_success_rate = stats.successful_runs / stats.total_runs
        
        # Fator baseado na duração média
        duration_factor = 1.0
        if stats.average_duration > 10.0:
            duration_factor = 0.8
        elif stats.average_duration > 20.0:
            duration_factor = 0.6
        
        # Combinar fatores
        factor = historical_success_rate * duration_factor
        
        return max(0.5, min(factor, 1.5))
    
    def _calculate_load_factor(self, source_name: str) -> float:
        """Calcula fator baseado na carga atual do sistema."""
        # Verificar se há tarefas em execução
        running_tasks_count = len([task for task in self.running_tasks.values() if not task.done()])
        
        # Fator baseado na carga
        if running_tasks_count > 5:
            return 0.7
        elif running_tasks_count > 3:
            return 0.85
        else:
            return 1.0
    
    async def get_orchestration_status(self) -> Dict[str, Any]:
        """Retorna status completo do sistema de orquestração."""
        status = self.get_all_status()
        
        # Adicionar informações específicas da orquestração
        orchestration_info = {
            "validation_enabled": self.validation_enabled,
            "fallback_enabled": self.fallback_enabled,
            "source_rotation": {
                "enabled": self.source_rotator is not None,
                "sources_count": len(self.collector_instances) if self.source_rotator else 0
            },
            "fallback_system": {
                "enabled": self.fallback_system is not None,
                "fallback_enabled": self.fallback_enabled,
                "system_type": type(self.fallback_system).__name__ if self.fallback_system else None
            },
            "cross_validation": {
                "enabled": self.cross_validator is not None,
                "validator_type": type(self.cross_validator).__name__ if self.cross_validator else None
            }
        }
        
        status["orchestration"] = orchestration_info
        return status
    
    async def enable_validation(self, enable: bool = True) -> None:
        """Habilita/desabilita validação cruzada."""
        self.validation_enabled = enable
        self.logger.info(f"Validação cruzada {'habilitada' if enable else 'desabilitada'}")
    
    async def enable_fallback(self, enable: bool = True) -> None:
        """Habilita/desabilita sistema de fallback."""
        self.fallback_enabled = enable
        self.logger.info(f"Sistema de fallback {'habilitado' if enable else 'desabilitado'}")
    
    async def collect_all(self, symbols: Optional[List[str]] = None) -> Dict[str, Any]:
        """Coleta dados de todos os coletores habilitados."""
        results = {}
        
        # Ordenar coletores por prioridade
        sorted_collectors = sorted(
            [(name, config) for name, config in self.collectors_config.items() if config.enabled],
            key=lambda x: x[1].priority
        )
        
        for collector_name, config in sorted_collectors:
            try:
                self.logger.info(f"Iniciando coleta com {collector_name}")
                collector_results = await self.collect_data(collector_name, symbols)
                results[collector_name] = collector_results
                self.logger.info(f"Coleta com {collector_name} concluída")
                
            except Exception as e:
                self.logger.error(f"Erro na coleta com {collector_name}: {e}")
                results[collector_name] = {"error": str(e)}
        
        return results
    
    async def start_continuous_collection(self, interval: int = None):
        """Inicia coleta contínua de dados."""
        interval = interval or getattr(settings, 'DATA_COLLECTION_INTERVAL', 3600)
        
        self.logger.info(f"Iniciando coleta contínua com intervalo de {interval} segundos")
        
        while not self.shutdown_event.is_set():
            try:
                start_time = time.time()
                
                # Executar coleta
                await self.collect_all()
                
                # Limpeza de cache expirado
                if self.cache:
                    await self.cache.clear_expired()
                
                # Calcular tempo restante
                elapsed = time.time() - start_time
                sleep_time = max(0, interval - elapsed)
                
                self.logger.info(f"Ciclo de coleta concluído em {elapsed:.2f}s. Próximo em {sleep_time:.2f}s")
                
                # Aguardar próximo ciclo ou shutdown
                try:
                    await asyncio.wait_for(self.shutdown_event.wait(), timeout=sleep_time)
                    break  # Shutdown solicitado
                except asyncio.TimeoutError:
                    continue  # Continuar próximo ciclo
                    
            except Exception as e:
                self.logger.error(f"Erro na coleta contínua: {e}")
                await asyncio.sleep(60)  # Aguardar 1 minuto antes de tentar novamente
    
    async def stop_continuous_collection(self):
        """Para a coleta contínua."""
        self.shutdown_event.set()
        
        # Aguardar tarefas em execução
        if self.running_tasks:
            await asyncio.gather(*self.running_tasks.values(), return_exceptions=True)
        
        self.logger.info("Coleta contínua interrompida")
    
    def get_collector_status(self, collector_name: str) -> Dict[str, Any]:
        """Retorna status de um coletor específico."""
        if collector_name not in self.collectors_config:
            raise ValueError(f"Coletor {collector_name} não encontrado")
        
        config = self.collectors_config[collector_name]
        stats = self.collectors_stats[collector_name]
        circuit_breaker = self.circuit_breakers.get(collector_name)
        
        status = {
            "name": collector_name,
            "type": config.collector_type.value,
            "enabled": config.enabled,
            "status": stats.status.value,
            "last_run": stats.last_run.isoformat() if stats.last_run else None,
            "last_success": stats.last_success.isoformat() if stats.last_success else None,
            "last_error": stats.last_error,
            "total_runs": stats.total_runs,
            "success_rate": (stats.successful_runs / stats.total_runs * 100) if stats.total_runs > 0 else 0,
            "average_duration": stats.average_duration,
            "data_points_collected": stats.data_points_collected
        }
        
        if circuit_breaker:
            cb_health = circuit_breaker.get_health_status()
            status["circuit_breaker"] = cb_health
        
        return status
    
    def get_all_status(self) -> Dict[str, Any]:
        """Retorna status de todos os coletores."""
        return {
            "collectors": {
                name: self.get_collector_status(name)
                for name in self.collectors_config.keys()
            },
            "cache_stats": self.cache.get_stats() if self.cache else None,
            "metrics_available": self.metrics.enabled if self.metrics else False
        }
    
    async def enable_collector(self, collector_name: str):
        """Habilita um coletor."""
        if collector_name in self.collectors_config:
            self.collectors_config[collector_name].enabled = True
            self.collectors_stats[collector_name].status = CollectorStatus.IDLE
            await self._init_collector_instances()  # Reinicializar instância
            self.logger.info(f"Coletor {collector_name} habilitado")
    
    async def disable_collector(self, collector_name: str):
        """Desabilita um coletor."""
        if collector_name in self.collectors_config:
            self.collectors_config[collector_name].enabled = False
            self.collectors_stats[collector_name].status = CollectorStatus.DISABLED
            self.logger.info(f"Coletor {collector_name} desabilitado")
    
    async def reset_collector(self, collector_name: str):
        """Reseta estatísticas e circuit breaker de um coletor."""
        if collector_name in self.collectors_stats:
            self.collectors_stats[collector_name] = CollectorStats(name=collector_name)
        
        if collector_name in self.circuit_breakers:
            await self.circuit_breakers[collector_name].reset()
        
        self.logger.info(f"Coletor {collector_name} resetado")
    
    async def close(self):
        """Fecha o gerenciador e limpa recursos."""
        await self.stop_continuous_collection()
        
        if self.cache:
            await self.cache.close()
        
        if self.fallback_system:
            await self.fallback_system.close()
        
        self.logger.info("Gerenciador de coletores finalizado")


# Instância global do gerenciador
_collector_manager: Optional[CollectorManager] = None


async def get_collector_manager() -> CollectorManager:
    """Retorna instância global do gerenciador de coletores."""
    global _collector_manager
    
    if _collector_manager is None:
        _collector_manager = CollectorManager()
        await _collector_manager.initialize()
    
    return _collector_manager


async def close_collector_manager():
    """Fecha instância global do gerenciador."""
    global _collector_manager
    
    if _collector_manager:
        await _collector_manager.close()
        _collector_manager = None