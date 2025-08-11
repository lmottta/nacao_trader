"""Sistema de Fallback Automático para Coletores de Dados.

Este módulo implementa um sistema robusto de fallback que:
- Detecta falhas automaticamente
- Executa estratégias de recuperação
- Mantém redundância entre fontes
- Registra métricas de fallback
"""

import asyncio
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from contextlib import asynccontextmanager

from ..monitoring.metrics import MetricsCollector
from ..cache.intelligent_cache import IntelligentCache


class FallbackStrategy(Enum):
    """Estratégias de fallback disponíveis."""
    ROUND_ROBIN = "round_robin"  # Rotação circular entre fontes
    PRIORITY_BASED = "priority_based"  # Baseado em prioridade
    PERFORMANCE_BASED = "performance_based"  # Baseado em performance
    HYBRID = "hybrid"  # Combinação de estratégias


class FallbackTrigger(Enum):
    """Gatilhos para ativação do fallback."""
    ERROR_RATE = "error_rate"  # Taxa de erro alta
    TIMEOUT = "timeout"  # Timeout excessivo
    CIRCUIT_BREAKER = "circuit_breaker"  # Circuit breaker aberto
    MANUAL = "manual"  # Ativação manual
    QUALITY_DEGRADATION = "quality_degradation"  # Degradação da qualidade


@dataclass
class FallbackConfig:
    """Configuração do sistema de fallback."""
    strategy: FallbackStrategy = FallbackStrategy.HYBRID
    max_retries: int = 3
    retry_delay: float = 1.0
    error_threshold: float = 0.3  # 30% de erro
    timeout_threshold: float = 10.0  # 10 segundos
    quality_threshold: float = 0.7  # 70% de qualidade mínima
    fallback_timeout: float = 5.0
    enable_cache_fallback: bool = True
    enable_cross_validation: bool = True
    min_sources_for_consensus: int = 2


@dataclass
class FallbackSource:
    """Representa uma fonte de fallback."""
    name: str
    collector: Any
    priority: int = 1
    weight: float = 1.0
    enabled: bool = True
    last_success: Optional[datetime] = None
    last_error: Optional[datetime] = None
    success_count: int = 0
    error_count: int = 0
    avg_response_time: float = 0.0
    supported_symbols: List[str] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        """Calcula taxa de sucesso."""
        total = self.success_count + self.error_count
        return self.success_count / total if total > 0 else 0.0
    
    @property
    def is_healthy(self) -> bool:
        """Verifica se a fonte está saudável."""
        if not self.enabled:
            return False
        
        # Verificar se teve erros recentes
        if self.last_error:
            time_since_error = datetime.now() - self.last_error
            if time_since_error < timedelta(minutes=5) and self.success_rate < 0.5:
                return False
        
        return True


@dataclass
class FallbackResult:
    """Resultado de uma operação de fallback."""
    success: bool
    data: Optional[Dict[str, Any]] = None
    source_used: Optional[str] = None
    attempts: int = 0
    total_time: float = 0.0
    errors: List[str] = field(default_factory=list)
    trigger: Optional[FallbackTrigger] = None
    fallback_chain: List[str] = field(default_factory=list)


class FallbackSystem:
    """Sistema de Fallback Automático."""
    
    def __init__(
        self,
        config: Optional[FallbackConfig] = None,
        cache: Optional[IntelligentCache] = None,
        metrics: Optional[MetricsCollector] = None
    ):
        self.config = config or FallbackConfig()
        self.cache = cache
        self.metrics = metrics
        self.logger = logging.getLogger(__name__)
        
        # Fontes de fallback
        self.sources: Dict[str, FallbackSource] = {}
        self.source_order: List[str] = []
        
        # Estado do sistema
        self.active_fallbacks: Dict[str, datetime] = {}
        self.fallback_history: List[Dict[str, Any]] = []
        
        # Callbacks
        self.on_fallback_triggered: Optional[Callable] = None
        self.on_fallback_resolved: Optional[Callable] = None
    
    async def add_source(
        self,
        name: str,
        collector: Any,
        priority: int = 1,
        weight: float = 1.0,
        supported_symbols: Optional[List[str]] = None
    ) -> None:
        """Adiciona uma fonte de fallback."""
        source = FallbackSource(
            name=name,
            collector=collector,
            priority=priority,
            weight=weight,
            supported_symbols=supported_symbols or []
        )
        
        self.sources[name] = source
        self._update_source_order()
        
        self.logger.info(f"Fonte de fallback adicionada: {name} (prioridade: {priority})")
    
    def _update_source_order(self) -> None:
        """Atualiza ordem das fontes baseada na estratégia."""
        if self.config.strategy == FallbackStrategy.PRIORITY_BASED:
            self.source_order = sorted(
                self.sources.keys(),
                key=lambda x: self.sources[x].priority
            )
        elif self.config.strategy == FallbackStrategy.PERFORMANCE_BASED:
            self.source_order = sorted(
                self.sources.keys(),
                key=lambda x: (self.sources[x].success_rate, -self.sources[x].avg_response_time),
                reverse=True
            )
        elif self.config.strategy == FallbackStrategy.ROUND_ROBIN:
            # Manter ordem atual para round robin
            if not self.source_order:
                self.source_order = list(self.sources.keys())
        else:  # HYBRID
            # Combinar prioridade e performance
            self.source_order = sorted(
                self.sources.keys(),
                key=lambda x: (
                    self.sources[x].priority,
                    self.sources[x].success_rate,
                    -self.sources[x].avg_response_time
                )
            )
    
    async def execute_with_fallback(
        self,
        symbol: str,
        primary_source: str,
        operation: str = "collect",
        **kwargs
    ) -> FallbackResult:
        """Executa operação com fallback automático."""
        start_time = datetime.now()
        result = FallbackResult(success=False, trigger=None)
        
        # Tentar fonte primária primeiro
        try:
            primary_result = await self._execute_on_source(
                primary_source, symbol, operation, **kwargs
            )
            
            if primary_result:
                await self._record_success(primary_source, start_time)
                result.success = True
                result.data = primary_result
                result.source_used = primary_source
                result.attempts = 1
                result.total_time = (datetime.now() - start_time).total_seconds()
                return result
        
        except Exception as e:
            await self._record_error(primary_source, str(e))
            result.errors.append(f"{primary_source}: {str(e)}")
            
            # Determinar trigger do fallback
            result.trigger = self._determine_fallback_trigger(e)
        
        # Executar fallback
        fallback_result = await self._execute_fallback_chain(
            symbol, primary_source, operation, result, **kwargs
        )
        
        result.total_time = (datetime.now() - start_time).total_seconds()
        
        # Registrar métricas
        if self.metrics:
            await self.metrics.record_counter(
                "fallback_executed_total",
                labels={
                    "symbol": symbol,
                    "primary_source": primary_source,
                    "success": str(result.success),
                    "trigger": result.trigger.value if result.trigger else "unknown"
                }
            )
        
        return result
    
    async def _execute_fallback_chain(
        self,
        symbol: str,
        primary_source: str,
        operation: str,
        result: FallbackResult,
        **kwargs
    ) -> FallbackResult:
        """Executa cadeia de fallback."""
        # Obter fontes de fallback
        fallback_sources = self._get_fallback_sources(symbol, primary_source)
        
        for attempt, source_name in enumerate(fallback_sources, 2):
            if attempt > self.config.max_retries + 1:
                break
            
            try:
                # Delay entre tentativas
                if attempt > 2:
                    await asyncio.sleep(self.config.retry_delay * (attempt - 1))
                
                source_result = await self._execute_on_source(
                    source_name, symbol, operation, **kwargs
                )
                
                if source_result:
                    await self._record_success(source_name, datetime.now())
                    result.success = True
                    result.data = source_result
                    result.source_used = source_name
                    result.attempts = attempt
                    result.fallback_chain.append(source_name)
                    
                    self.logger.info(
                        f"Fallback bem-sucedido: {primary_source} -> {source_name} para {symbol}"
                    )
                    break
            
            except Exception as e:
                await self._record_error(source_name, str(e))
                result.errors.append(f"{source_name}: {str(e)}")
                result.fallback_chain.append(f"{source_name}_failed")
                continue
        
        # Tentar cache como último recurso
        if not result.success and self.config.enable_cache_fallback and self.cache:
            cache_result = await self._try_cache_fallback(symbol)
            if cache_result:
                result.success = True
                result.data = cache_result
                result.source_used = "cache"
                result.fallback_chain.append("cache")
                
                self.logger.info(f"Fallback de cache usado para {symbol}")
        
        return result
    
    def _get_fallback_sources(self, symbol: str, exclude_source: str) -> List[str]:
        """Obtém lista de fontes de fallback ordenadas."""
        # Filtrar fontes disponíveis
        available_sources = [
            name for name, source in self.sources.items()
            if (name != exclude_source and 
                source.is_healthy and 
                (not source.supported_symbols or symbol in source.supported_symbols))
        ]
        
        # Aplicar estratégia de ordenação
        if self.config.strategy == FallbackStrategy.ROUND_ROBIN:
            # Rotacionar a partir da última fonte usada
            last_used_idx = 0
            if exclude_source in self.source_order:
                last_used_idx = self.source_order.index(exclude_source)
            
            ordered_sources = (
                self.source_order[last_used_idx + 1:] + 
                self.source_order[:last_used_idx]
            )
            return [s for s in ordered_sources if s in available_sources]
        
        else:
            # Usar ordem pré-calculada
            return [s for s in self.source_order if s in available_sources]
    
    async def _execute_on_source(
        self,
        source_name: str,
        symbol: str,
        operation: str,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """Executa operação em uma fonte específica."""
        if source_name not in self.sources:
            raise ValueError(f"Fonte não encontrada: {source_name}")
        
        source = self.sources[source_name]
        collector = source.collector
        
        # Timeout para operação
        try:
            if operation == "collect":
                if hasattr(collector, 'collect_data'):
                    return await asyncio.wait_for(
                        collector.collect_data([symbol]),
                        timeout=self.config.fallback_timeout
                    )
                elif hasattr(collector, 'get_data'):
                    return await asyncio.wait_for(
                        collector.get_data(symbol),
                        timeout=self.config.fallback_timeout
                    )
            
            raise AttributeError(f"Operação {operation} não suportada por {source_name}")
        
        except asyncio.TimeoutError:
            raise TimeoutError(f"Timeout na operação {operation} para {source_name}")
    
    async def _try_cache_fallback(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Tenta obter dados do cache como fallback."""
        if not self.cache:
            return None
        
        try:
            # Buscar dados recentes no cache (até 1 hora)
            cache_key = f"fallback_{symbol}"
            cached_data = await self.cache.get(cache_key)
            
            if cached_data:
                # Verificar se os dados não são muito antigos
                if 'timestamp' in cached_data:
                    cache_time = datetime.fromisoformat(cached_data['timestamp'])
                    if datetime.now() - cache_time < timedelta(hours=1):
                        return cached_data
            
            return None
        
        except Exception as e:
            self.logger.warning(f"Erro ao acessar cache para fallback: {e}")
            return None
    
    def _determine_fallback_trigger(self, error: Exception) -> FallbackTrigger:
        """Determina o gatilho do fallback baseado no erro."""
        error_str = str(error).lower()
        
        if "timeout" in error_str:
            return FallbackTrigger.TIMEOUT
        elif "circuit" in error_str or "breaker" in error_str:
            return FallbackTrigger.CIRCUIT_BREAKER
        elif "rate" in error_str or "limit" in error_str:
            return FallbackTrigger.ERROR_RATE
        else:
            return FallbackTrigger.ERROR_RATE
    
    async def _record_success(self, source_name: str, start_time: datetime) -> None:
        """Registra sucesso de uma fonte."""
        if source_name in self.sources:
            source = self.sources[source_name]
            source.last_success = datetime.now()
            source.success_count += 1
            
            # Atualizar tempo médio de resposta
            response_time = (datetime.now() - start_time).total_seconds()
            if source.avg_response_time == 0:
                source.avg_response_time = response_time
            else:
                source.avg_response_time = (
                    source.avg_response_time * 0.8 + response_time * 0.2
                )
    
    async def _record_error(self, source_name: str, error: str) -> None:
        """Registra erro de uma fonte."""
        if source_name in self.sources:
            source = self.sources[source_name]
            source.last_error = datetime.now()
            source.error_count += 1
            
            self.logger.warning(f"Erro em {source_name}: {error}")
    
    async def get_fallback_status(self) -> Dict[str, Any]:
        """Retorna status completo do sistema de fallback."""
        return {
            "config": {
                "strategy": self.config.strategy.value,
                "max_retries": self.config.max_retries,
                "error_threshold": self.config.error_threshold,
                "timeout_threshold": self.config.timeout_threshold,
                "quality_threshold": self.config.quality_threshold
            },
            "sources": {
                name: {
                    "enabled": source.enabled,
                    "priority": source.priority,
                    "weight": source.weight,
                    "success_rate": source.success_rate,
                    "avg_response_time": source.avg_response_time,
                    "is_healthy": source.is_healthy,
                    "last_success": source.last_success.isoformat() if source.last_success else None,
                    "last_error": source.last_error.isoformat() if source.last_error else None,
                    "total_requests": source.success_count + source.error_count
                }
                for name, source in self.sources.items()
            },
            "active_fallbacks": len(self.active_fallbacks),
            "fallback_history_count": len(self.fallback_history)
        }
    
    async def enable_source(self, source_name: str) -> bool:
        """Habilita uma fonte de fallback."""
        if source_name in self.sources:
            self.sources[source_name].enabled = True
            self._update_source_order()
            self.logger.info(f"Fonte {source_name} habilitada")
            return True
        return False
    
    async def disable_source(self, source_name: str) -> bool:
        """Desabilita uma fonte de fallback."""
        if source_name in self.sources:
            self.sources[source_name].enabled = False
            self._update_source_order()
            self.logger.info(f"Fonte {source_name} desabilitada")
            return True
        return False
    
    async def reset_source_stats(self, source_name: str) -> bool:
        """Reseta estatísticas de uma fonte."""
        if source_name in self.sources:
            source = self.sources[source_name]
            source.success_count = 0
            source.error_count = 0
            source.avg_response_time = 0.0
            source.last_success = None
            source.last_error = None
            self.logger.info(f"Estatísticas de {source_name} resetadas")
            return True
        return False
    
    async def close(self) -> None:
        """Finaliza o sistema de fallback."""
        self.active_fallbacks.clear()
        self.fallback_history.clear()
        self.logger.info("Sistema de fallback finalizado")


# Instância global
_fallback_system: Optional[FallbackSystem] = None


async def get_fallback_system(
    config: Optional[FallbackConfig] = None,
    cache: Optional[IntelligentCache] = None,
    metrics: Optional[MetricsCollector] = None
) -> FallbackSystem:
    """Obtém instância global do sistema de fallback."""
    global _fallback_system
    
    if _fallback_system is None:
        _fallback_system = FallbackSystem(config, cache, metrics)
    
    return _fallback_system


async def close_fallback_system() -> None:
    """Finaliza instância global do sistema de fallback."""
    global _fallback_system
    
    if _fallback_system:
        await _fallback_system.close()
        _fallback_system = None