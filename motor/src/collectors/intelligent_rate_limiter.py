"""Sistema de Rate Limiting Inteligente para Coletores.

Este módulo implementa um sistema avançado de rate limiting que:
- Ajusta automaticamente os limites baseado na performance
- Considera métricas de sistema e rede
- Implementa algoritmos adaptativos
- Integra com circuit breakers e métricas
"""

import asyncio
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

from ..monitoring.metrics import MetricsCollector
from ..resilience.circuit_breaker import AdvancedCircuitBreaker


class RateLimitStrategy(Enum):
    """Estratégias de rate limiting."""
    FIXED = "fixed"  # Rate limit fixo
    ADAPTIVE = "adaptive"  # Adaptativo baseado em performance
    AIMD = "aimd"  # Additive Increase Multiplicative Decrease
    TOKEN_BUCKET = "token_bucket"  # Token bucket algorithm
    SLIDING_WINDOW = "sliding_window"  # Sliding window counter


@dataclass
class RateLimitConfig:
    """Configuração do rate limiter."""
    strategy: RateLimitStrategy = RateLimitStrategy.ADAPTIVE
    base_rate: float = 1.0  # Requisições por segundo
    max_rate: float = 10.0  # Rate máximo
    min_rate: float = 0.1  # Rate mínimo
    burst_size: int = 5  # Tamanho do burst
    window_size: int = 60  # Janela em segundos
    adaptation_factor: float = 0.1  # Fator de adaptação (0.1 = 10%)
    performance_threshold: float = 0.8  # Threshold de performance
    error_threshold: float = 0.1  # Threshold de erro
    response_time_threshold: float = 5.0  # Threshold de tempo de resposta


@dataclass
class RequestMetrics:
    """Métricas de uma requisição."""
    timestamp: datetime
    success: bool
    response_time: float
    error_type: Optional[str] = None


class IntelligentRateLimiter:
    """Rate Limiter Inteligente com algoritmos adaptativos."""
    
    def __init__(
        self,
        name: str,
        config: Optional[RateLimitConfig] = None,
        metrics: Optional[MetricsCollector] = None,
        circuit_breaker: Optional[AdvancedCircuitBreaker] = None
    ):
        self.name = name
        self.config = config or RateLimitConfig()
        self.metrics = metrics
        self.circuit_breaker = circuit_breaker
        self.logger = logging.getLogger(__name__)
        
        # Estado do rate limiter
        self.current_rate = self.config.base_rate
        self.tokens = self.config.burst_size
        self.last_refill = time.time()
        
        # Histórico de requisições
        self.request_history: deque = deque(maxlen=1000)
        self.performance_history: deque = deque(maxlen=100)
        
        # Controle de acesso
        self.semaphore = asyncio.Semaphore(max(1, int(self.current_rate)))
        self.request_times: deque = deque(maxlen=self.config.window_size)
        
        # Estatísticas
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_wait_time = 0.0
        
        self.logger.info(f"Rate limiter inteligente inicializado para {name}")
    
    async def acquire(self) -> Tuple[bool, float]:
        """Adquire permissão para fazer uma requisição.
        
        Returns:
            Tuple[bool, float]: (permitido, tempo_de_espera)
        """
        start_time = time.time()
        
        # Verificar circuit breaker
        if self.circuit_breaker and not self.circuit_breaker.can_execute():
            return False, 0.0
        
        # Aplicar estratégia de rate limiting
        if self.config.strategy == RateLimitStrategy.TOKEN_BUCKET:
            allowed, wait_time = await self._token_bucket_acquire()
        elif self.config.strategy == RateLimitStrategy.SLIDING_WINDOW:
            allowed, wait_time = await self._sliding_window_acquire()
        elif self.config.strategy == RateLimitStrategy.ADAPTIVE:
            allowed, wait_time = await self._adaptive_acquire()
        else:  # FIXED
            allowed, wait_time = await self._fixed_acquire()
        
        if allowed:
            self.total_requests += 1
            
            # Registrar tempo de espera
            actual_wait_time = time.time() - start_time
            self.total_wait_time += actual_wait_time
            
            # Registrar métricas
            if self.metrics:
                await self.metrics.record_histogram(
                    "rate_limiter_wait_time_seconds",
                    actual_wait_time,
                    labels={"limiter": self.name, "strategy": self.config.strategy.value}
                )
        
        return allowed, wait_time
    
    async def _token_bucket_acquire(self) -> Tuple[bool, float]:
        """Implementa algoritmo Token Bucket."""
        now = time.time()
        
        # Reabastecer tokens
        time_passed = now - self.last_refill
        tokens_to_add = time_passed * self.current_rate
        self.tokens = min(self.config.burst_size, self.tokens + tokens_to_add)
        self.last_refill = now
        
        # Verificar se há tokens disponíveis
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True, 0.0
        else:
            # Calcular tempo de espera
            wait_time = (1.0 - self.tokens) / self.current_rate
            return False, wait_time
    
    async def _sliding_window_acquire(self) -> Tuple[bool, float]:
        """Implementa algoritmo Sliding Window."""
        now = time.time()
        
        # Remover requisições antigas
        cutoff_time = now - self.config.window_size
        while self.request_times and self.request_times[0] < cutoff_time:
            self.request_times.popleft()
        
        # Verificar se pode fazer requisição
        max_requests = int(self.current_rate * self.config.window_size)
        
        if len(self.request_times) < max_requests:
            self.request_times.append(now)
            return True, 0.0
        else:
            # Calcular tempo de espera
            oldest_request = self.request_times[0]
            wait_time = oldest_request + self.config.window_size - now
            return False, max(0, wait_time)
    
    async def _adaptive_acquire(self) -> Tuple[bool, float]:
        """Implementa algoritmo adaptativo."""
        # Ajustar rate baseado na performance recente
        await self._adapt_rate()
        
        # Usar token bucket com rate adaptado
        return await self._token_bucket_acquire()
    
    async def _fixed_acquire(self) -> Tuple[bool, float]:
        """Implementa rate limiting fixo."""
        async with self.semaphore:
            # Calcular delay necessário
            delay = 1.0 / self.current_rate
            await asyncio.sleep(delay)
            return True, delay
    
    async def _adapt_rate(self) -> None:
        """Adapta o rate baseado na performance recente."""
        if len(self.performance_history) < 5:
            return
        
        # Calcular métricas recentes
        recent_metrics = list(self.performance_history)[-10:]
        
        success_rate = sum(1 for m in recent_metrics if m['success']) / len(recent_metrics)
        avg_response_time = sum(m['response_time'] for m in recent_metrics) / len(recent_metrics)
        error_rate = 1 - success_rate
        
        # Determinar se deve aumentar ou diminuir o rate
        should_increase = (
            success_rate >= self.config.performance_threshold and
            error_rate <= self.config.error_threshold and
            avg_response_time <= self.config.response_time_threshold
        )
        
        should_decrease = (
            success_rate < self.config.performance_threshold or
            error_rate > self.config.error_threshold or
            avg_response_time > self.config.response_time_threshold
        )
        
        # Ajustar rate
        old_rate = self.current_rate
        
        if should_increase:
            # AIMD: Additive Increase
            self.current_rate = min(
                self.config.max_rate,
                self.current_rate + self.config.adaptation_factor
            )
        elif should_decrease:
            # AIMD: Multiplicative Decrease
            self.current_rate = max(
                self.config.min_rate,
                self.current_rate * (1 - self.config.adaptation_factor)
            )
        
        # Atualizar semáforo se necessário
        if abs(self.current_rate - old_rate) > 0.01:
            new_semaphore_value = max(1, int(self.current_rate))
            self.semaphore = asyncio.Semaphore(new_semaphore_value)
            
            self.logger.debug(
                f"Rate adaptado para {self.name}: {old_rate:.3f} -> {self.current_rate:.3f} "
                f"(success: {success_rate:.2f}, error: {error_rate:.2f}, rt: {avg_response_time:.2f})"
            )
    
    async def record_request(self, success: bool, response_time: float, error_type: Optional[str] = None) -> None:
        """Registra resultado de uma requisição."""
        metrics = RequestMetrics(
            timestamp=datetime.now(),
            success=success,
            response_time=response_time,
            error_type=error_type
        )
        
        self.request_history.append(metrics)
        
        # Adicionar ao histórico de performance
        self.performance_history.append({
            'success': success,
            'response_time': response_time,
            'timestamp': time.time()
        })
        
        # Atualizar estatísticas
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        
        # Registrar métricas
        if self.metrics:
            await self.metrics.record_counter(
                "rate_limiter_requests_total",
                labels={
                    "limiter": self.name,
                    "success": str(success),
                    "strategy": self.config.strategy.value
                }
            )
            
            await self.metrics.record_histogram(
                "rate_limiter_response_time_seconds",
                response_time,
                labels={"limiter": self.name}
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do rate limiter."""
        success_rate = (
            self.successful_requests / self.total_requests 
            if self.total_requests > 0 else 0.0
        )
        
        avg_wait_time = (
            self.total_wait_time / self.total_requests 
            if self.total_requests > 0 else 0.0
        )
        
        return {
            "name": self.name,
            "strategy": self.config.strategy.value,
            "current_rate": self.current_rate,
            "base_rate": self.config.base_rate,
            "max_rate": self.config.max_rate,
            "min_rate": self.config.min_rate,
            "total_requests": self.total_requests,
            "successful_requests": self.successful_requests,
            "failed_requests": self.failed_requests,
            "success_rate": success_rate,
            "average_wait_time": avg_wait_time,
            "tokens_available": self.tokens,
            "requests_in_window": len(self.request_times)
        }
    
    async def reset(self) -> None:
        """Reseta o rate limiter."""
        self.current_rate = self.config.base_rate
        self.tokens = self.config.burst_size
        self.last_refill = time.time()
        
        self.request_history.clear()
        self.performance_history.clear()
        self.request_times.clear()
        
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_wait_time = 0.0
        
        self.semaphore = asyncio.Semaphore(max(1, int(self.current_rate)))
        
        self.logger.info(f"Rate limiter {self.name} resetado")
    
    async def close(self) -> None:
        """Finaliza o rate limiter."""
        self.request_history.clear()
        self.performance_history.clear()
        self.request_times.clear()
        
        self.logger.info(f"Rate limiter {self.name} finalizado")


class RateLimiterManager:
    """Gerenciador de múltiplos rate limiters."""
    
    def __init__(self, metrics: Optional[MetricsCollector] = None):
        self.metrics = metrics
        self.limiters: Dict[str, IntelligentRateLimiter] = {}
        self.logger = logging.getLogger(__name__)
    
    def create_limiter(
        self,
        name: str,
        config: Optional[RateLimitConfig] = None,
        circuit_breaker: Optional[AdvancedCircuitBreaker] = None
    ) -> IntelligentRateLimiter:
        """Cria um novo rate limiter."""
        limiter = IntelligentRateLimiter(name, config, self.metrics, circuit_breaker)
        self.limiters[name] = limiter
        return limiter
    
    def get_limiter(self, name: str) -> Optional[IntelligentRateLimiter]:
        """Obtém um rate limiter existente."""
        return self.limiters.get(name)
    
    async def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Retorna estatísticas de todos os rate limiters."""
        return {
            name: limiter.get_stats()
            for name, limiter in self.limiters.items()
        }
    
    async def reset_all(self) -> None:
        """Reseta todos os rate limiters."""
        for limiter in self.limiters.values():
            await limiter.reset()
        
        self.logger.info("Todos os rate limiters foram resetados")
    
    async def close_all(self) -> None:
        """Finaliza todos os rate limiters."""
        for limiter in self.limiters.values():
            await limiter.close()
        
        self.limiters.clear()
        self.logger.info("Todos os rate limiters foram finalizados")


# Instância global
_rate_limiter_manager: Optional[RateLimiterManager] = None


def get_rate_limiter_manager(metrics: Optional[MetricsCollector] = None) -> RateLimiterManager:
    """Obtém instância global do gerenciador de rate limiters."""
    global _rate_limiter_manager
    
    if _rate_limiter_manager is None:
        _rate_limiter_manager = RateLimiterManager(metrics)
    
    return _rate_limiter_manager


async def close_rate_limiter_manager() -> None:
    """Finaliza instância global do gerenciador de rate limiters."""
    global _rate_limiter_manager
    
    if _rate_limiter_manager:
        await _rate_limiter_manager.close_all()
        _rate_limiter_manager = None