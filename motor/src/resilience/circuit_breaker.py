"""Sistema de Circuit Breakers Avançados para o Nação Trader.

Implementa circuit breakers com múltiplos estados e estratégias de recuperação
para aumentar a resiliência do sistema de coleta de dados.
"""

import asyncio
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import logging
from functools import wraps
import statistics


class CircuitState(Enum):
    """Estados do Circuit Breaker."""
    CLOSED = "closed"        # Funcionamento normal
    OPEN = "open"            # Bloqueando chamadas
    HALF_OPEN = "half_open"  # Testando recuperação
    FORCED_OPEN = "forced_open"  # Forçadamente aberto (manutenção)


class FailureType(Enum):
    """Tipos de falha monitorados."""
    TIMEOUT = "timeout"
    CONNECTION_ERROR = "connection_error"
    HTTP_ERROR = "http_error"
    RATE_LIMIT = "rate_limit"
    AUTHENTICATION_ERROR = "auth_error"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class FailureRecord:
    """Registro de falha."""
    timestamp: float
    failure_type: FailureType
    error_message: str
    duration_ms: float = 0


@dataclass
class CircuitBreakerConfig:
    """Configuração do Circuit Breaker."""
    # Thresholds
    failure_threshold: int = 5  # Número de falhas para abrir
    success_threshold: int = 3  # Sucessos para fechar em half-open
    timeout_threshold: float = 30.0  # Timeout em segundos
    
    # Timeouts
    open_timeout: float = 60.0  # Tempo em estado aberto
    half_open_timeout: float = 30.0  # Tempo máximo em half-open
    
    # Janelas de tempo
    failure_window: float = 300.0  # Janela para contar falhas (5 min)
    recovery_window: float = 600.0  # Janela para análise de recuperação
    
    # Estratégias
    exponential_backoff: bool = True
    max_backoff: float = 3600.0  # Máximo backoff (1 hora)
    backoff_multiplier: float = 2.0
    
    # Monitoramento
    enable_metrics: bool = True
    log_failures: bool = True


@dataclass
class CircuitBreakerMetrics:
    """Métricas do Circuit Breaker."""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    timeouts: int = 0
    circuit_opens: int = 0
    circuit_closes: int = 0
    current_state: CircuitState = CircuitState.CLOSED
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    average_response_time: float = 0.0
    failure_rate: float = 0.0
    uptime_percentage: float = 100.0
    
    # Histórico de falhas por tipo
    failure_counts: Dict[FailureType, int] = field(default_factory=dict)
    
    def update_failure_rate(self):
        """Atualiza taxa de falha."""
        if self.total_requests > 0:
            self.failure_rate = (self.failed_requests / self.total_requests) * 100
    
    def update_uptime(self, total_time: float, downtime: float):
        """Atualiza porcentagem de uptime."""
        if total_time > 0:
            self.uptime_percentage = ((total_time - downtime) / total_time) * 100


class CircuitBreakerException(Exception):
    """Exceção lançada quando circuit breaker está aberto."""
    
    def __init__(self, message: str, state: CircuitState, last_failure: Optional[str] = None):
        self.state = state
        self.last_failure = last_failure
        super().__init__(message)


class AdvancedCircuitBreaker:
    """Circuit Breaker avançado com múltiplos estados e estratégias."""
    
    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        
        # Estado atual
        self._state = CircuitState.CLOSED
        self._state_changed_at = time.time()
        
        # Contadores
        self._failure_count = 0
        self._success_count = 0
        self._consecutive_failures = 0
        self._consecutive_successes = 0
        
        # Histórico
        self._failure_history: List[FailureRecord] = []
        self._response_times: List[float] = []
        
        # Métricas
        self.metrics = CircuitBreakerMetrics()
        
        # Backoff
        self._current_backoff = 1.0
        self._last_attempt_time = 0.0
        
        # Logger
        self.logger = logging.getLogger(f"{__name__}.{name}")
        
        # Lock para thread safety
        self._lock = asyncio.Lock()
    
    @property
    def state(self) -> CircuitState:
        """Estado atual do circuit breaker."""
        return self._state
    
    @property
    def is_closed(self) -> bool:
        """Verifica se o circuit está fechado (funcionando)."""
        return self._state == CircuitState.CLOSED
    
    @property
    def is_open(self) -> bool:
        """Verifica se o circuit está aberto (bloqueando)."""
        return self._state in [CircuitState.OPEN, CircuitState.FORCED_OPEN]
    
    @property
    def is_half_open(self) -> bool:
        """Verifica se o circuit está meio aberto (testando)."""
        return self._state == CircuitState.HALF_OPEN
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """Executa função protegida pelo circuit breaker."""
        async with self._lock:
            await self._update_state()
            
            if self.is_open:
                self._handle_open_circuit()
            
            # Verifica backoff
            if self._should_wait_backoff():
                raise CircuitBreakerException(
                    f"Circuit breaker {self.name} em backoff",
                    self._state
                )
        
        # Executa função
        start_time = time.time()
        try:
            if asyncio.iscoroutinefunction(func):
                result = await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=self.config.timeout_threshold
                )
            else:
                result = func(*args, **kwargs)
            
            # Sucesso
            duration = (time.time() - start_time) * 1000
            await self._record_success(duration)
            return result
            
        except asyncio.TimeoutError:
            duration = (time.time() - start_time) * 1000
            await self._record_failure(FailureType.TIMEOUT, "Timeout", duration)
            raise
        except ConnectionError as e:
            duration = (time.time() - start_time) * 1000
            await self._record_failure(FailureType.CONNECTION_ERROR, str(e), duration)
            raise
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            failure_type = self._classify_error(e)
            await self._record_failure(failure_type, str(e), duration)
            raise
    
    def _classify_error(self, error: Exception) -> FailureType:
        """Classifica tipo de erro."""
        error_str = str(error).lower()
        
        if "timeout" in error_str:
            return FailureType.TIMEOUT
        elif "connection" in error_str or "network" in error_str:
            return FailureType.CONNECTION_ERROR
        elif "rate limit" in error_str or "429" in error_str:
            return FailureType.RATE_LIMIT
        elif "auth" in error_str or "401" in error_str or "403" in error_str:
            return FailureType.AUTHENTICATION_ERROR
        elif any(code in error_str for code in ["400", "404", "500", "502", "503"]):
            return FailureType.HTTP_ERROR
        else:
            return FailureType.UNKNOWN_ERROR
    
    async def _record_success(self, duration_ms: float):
        """Registra sucesso."""
        async with self._lock:
            self._success_count += 1
            self._consecutive_successes += 1
            self._consecutive_failures = 0
            
            self._response_times.append(duration_ms)
            if len(self._response_times) > 100:  # Manter apenas últimas 100
                self._response_times.pop(0)
            
            # Atualiza métricas
            self.metrics.total_requests += 1
            self.metrics.successful_requests += 1
            self.metrics.last_success_time = time.time()
            self.metrics.average_response_time = statistics.mean(self._response_times)
            self.metrics.update_failure_rate()
            
            # Reset backoff em caso de sucesso
            self._current_backoff = 1.0
            
            # Verifica transição de estado
            if self.is_half_open and self._consecutive_successes >= self.config.success_threshold:
                await self._transition_to_closed()
            
            if self.config.log_failures:
                self.logger.debug(f"Sucesso registrado - Duração: {duration_ms:.2f}ms")
    
    async def _record_failure(self, failure_type: FailureType, error_message: str, duration_ms: float):
        """Registra falha."""
        async with self._lock:
            current_time = time.time()
            
            # Registra falha
            failure_record = FailureRecord(
                timestamp=current_time,
                failure_type=failure_type,
                error_message=error_message,
                duration_ms=duration_ms
            )
            
            self._failure_history.append(failure_record)
            self._failure_count += 1
            self._consecutive_failures += 1
            self._consecutive_successes = 0
            
            # Limpa histórico antigo
            cutoff_time = current_time - self.config.failure_window
            self._failure_history = [
                f for f in self._failure_history if f.timestamp > cutoff_time
            ]
            
            # Atualiza métricas
            self.metrics.total_requests += 1
            self.metrics.failed_requests += 1
            self.metrics.last_failure_time = current_time
            
            if failure_type == FailureType.TIMEOUT:
                self.metrics.timeouts += 1
            
            if failure_type not in self.metrics.failure_counts:
                self.metrics.failure_counts[failure_type] = 0
            self.metrics.failure_counts[failure_type] += 1
            
            self.metrics.update_failure_rate()
            
            # Aplica backoff exponencial
            if self.config.exponential_backoff:
                self._current_backoff = min(
                    self._current_backoff * self.config.backoff_multiplier,
                    self.config.max_backoff
                )
            
            self._last_attempt_time = current_time
            
            # Verifica se deve abrir circuit
            recent_failures = len(self._failure_history)
            if (self.is_closed and 
                recent_failures >= self.config.failure_threshold):
                await self._transition_to_open()
            
            if self.config.log_failures:
                self.logger.warning(
                    f"Falha registrada - Tipo: {failure_type.value}, "
                    f"Erro: {error_message}, Duração: {duration_ms:.2f}ms"
                )
    
    async def _update_state(self):
        """Atualiza estado do circuit breaker."""
        current_time = time.time()
        time_in_state = current_time - self._state_changed_at
        
        if self._state in [CircuitState.OPEN, CircuitState.FORCED_OPEN]:
            # Verifica se deve tentar half-open
            if time_in_state >= self.config.open_timeout:
                await self._transition_to_half_open()
        
        elif self._state == CircuitState.HALF_OPEN:
            # Verifica timeout em half-open
            if time_in_state >= self.config.half_open_timeout:
                await self._transition_to_open()
    
    async def _transition_to_open(self):
        """Transição para estado aberto."""
        old_state = self._state
        self._state = CircuitState.OPEN
        self._state_changed_at = time.time()
        
        self.metrics.circuit_opens += 1
        self.metrics.current_state = self._state
        
        self.logger.warning(
            f"Circuit breaker {self.name} ABERTO - "
            f"Falhas consecutivas: {self._consecutive_failures}"
        )
        
        await self._notify_state_change(old_state, self._state)
    
    async def _transition_to_half_open(self):
        """Transição para estado meio aberto."""
        old_state = self._state
        self._state = CircuitState.HALF_OPEN
        self._state_changed_at = time.time()
        self._consecutive_successes = 0
        
        self.metrics.current_state = self._state
        
        self.logger.info(f"Circuit breaker {self.name} MEIO ABERTO - Testando recuperação")
        
        await self._notify_state_change(old_state, self._state)
    
    async def _transition_to_closed(self):
        """Transição para estado fechado."""
        old_state = self._state
        self._state = CircuitState.CLOSED
        self._state_changed_at = time.time()
        self._consecutive_failures = 0
        self._current_backoff = 1.0
        
        self.metrics.circuit_closes += 1
        self.metrics.current_state = self._state
        
        self.logger.info(
            f"Circuit breaker {self.name} FECHADO - "
            f"Sucessos consecutivos: {self._consecutive_successes}"
        )
        
        await self._notify_state_change(old_state, self._state)
    
    async def _notify_state_change(self, old_state: CircuitState, new_state: CircuitState):
        """Notifica mudança de estado (hook para extensões)."""
        pass
    
    def _should_wait_backoff(self) -> bool:
        """Verifica se deve aguardar backoff."""
        if not self.config.exponential_backoff:
            return False
        
        time_since_last_attempt = time.time() - self._last_attempt_time
        return time_since_last_attempt < self._current_backoff
    
    def _handle_open_circuit(self):
        """Lida com circuit aberto."""
        last_failure = None
        if self._failure_history:
            last_failure = self._failure_history[-1].error_message
        
        raise CircuitBreakerException(
            f"Circuit breaker {self.name} está ABERTO",
            self._state,
            last_failure
        )
    
    async def force_open(self):
        """Força abertura do circuit (para manutenção)."""
        async with self._lock:
            old_state = self._state
            self._state = CircuitState.FORCED_OPEN
            self._state_changed_at = time.time()
            
            self.metrics.current_state = self._state
            
            self.logger.warning(f"Circuit breaker {self.name} FORÇADAMENTE ABERTO")
            await self._notify_state_change(old_state, self._state)
    
    async def force_close(self):
        """Força fechamento do circuit."""
        async with self._lock:
            old_state = self._state
            self._state = CircuitState.CLOSED
            self._state_changed_at = time.time()
            self._consecutive_failures = 0
            self._current_backoff = 1.0
            
            self.metrics.current_state = self._state
            
            self.logger.info(f"Circuit breaker {self.name} FORÇADAMENTE FECHADO")
            await self._notify_state_change(old_state, self._state)
    
    async def reset(self):
        """Reseta circuit breaker."""
        async with self._lock:
            self._state = CircuitState.CLOSED
            self._state_changed_at = time.time()
            self._failure_count = 0
            self._success_count = 0
            self._consecutive_failures = 0
            self._consecutive_successes = 0
            self._failure_history.clear()
            self._response_times.clear()
            self._current_backoff = 1.0
            
            # Reset métricas
            self.metrics = CircuitBreakerMetrics()
            
            self.logger.info(f"Circuit breaker {self.name} RESETADO")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Retorna status de saúde do circuit breaker."""
        current_time = time.time()
        time_in_state = current_time - self._state_changed_at
        
        # Calcula uptime
        total_time = current_time - (self.metrics.last_success_time or current_time)
        downtime = sum(
            min(self.config.open_timeout, time_in_state) 
            for _ in range(self.metrics.circuit_opens)
        )
        self.metrics.update_uptime(total_time, downtime)
        
        return {
            "name": self.name,
            "state": self._state.value,
            "time_in_state": time_in_state,
            "consecutive_failures": self._consecutive_failures,
            "consecutive_successes": self._consecutive_successes,
            "recent_failures": len(self._failure_history),
            "current_backoff": self._current_backoff,
            "metrics": {
                "total_requests": self.metrics.total_requests,
                "success_rate": ((self.metrics.successful_requests / self.metrics.total_requests) * 100) if self.metrics.total_requests > 0 else 0,
                "failure_rate": self.metrics.failure_rate,
                "average_response_time": self.metrics.average_response_time,
                "uptime_percentage": self.metrics.uptime_percentage,
                "circuit_opens": self.metrics.circuit_opens,
                "circuit_closes": self.metrics.circuit_closes,
                "failure_counts": dict(self.metrics.failure_counts)
            },
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "success_threshold": self.config.success_threshold,
                "timeout_threshold": self.config.timeout_threshold,
                "open_timeout": self.config.open_timeout
            }
        }


# Decorator para aplicar circuit breaker
def circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None):
    """Decorator para aplicar circuit breaker a funções."""
    def decorator(func):
        cb = AdvancedCircuitBreaker(name, config)
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await cb.call(func, *args, **kwargs)
        
        # Adiciona referência ao circuit breaker
        wrapper.circuit_breaker = cb
        return wrapper
    
    return decorator


# Registry global de circuit breakers
_circuit_breakers: Dict[str, AdvancedCircuitBreaker] = {}


def get_circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None) -> AdvancedCircuitBreaker:
    """Obtém ou cria circuit breaker."""
    if name not in _circuit_breakers:
        _circuit_breakers[name] = AdvancedCircuitBreaker(name, config)
    return _circuit_breakers[name]


def get_all_circuit_breakers() -> Dict[str, AdvancedCircuitBreaker]:
    """Retorna todos os circuit breakers registrados."""
    return _circuit_breakers.copy()


async def reset_all_circuit_breakers():
    """Reseta todos os circuit breakers."""
    for cb in _circuit_breakers.values():
        await cb.reset()