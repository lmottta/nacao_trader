"""Testes para o sistema de Circuit Breakers."""

import pytest
import asyncio
import time
import sys
import os
from unittest.mock import AsyncMock, MagicMock

# Adicionar o diretório motor ao sys.path
motor_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, motor_dir)

from src.resilience.circuit_breaker import (
    AdvancedCircuitBreaker, CircuitBreakerConfig, CircuitState,
    FailureType, CircuitBreakerException, circuit_breaker,
    get_circuit_breaker, reset_all_circuit_breakers
)


class TestCircuitBreakerConfig:
    """Testes para CircuitBreakerConfig."""
    
    def test_default_config(self):
        """Testa configuração padrão."""
        config = CircuitBreakerConfig()
        
        assert config.failure_threshold == 5
        assert config.success_threshold == 3
        assert config.timeout_threshold == 30.0
        assert config.open_timeout == 60.0
        assert config.half_open_timeout == 30.0
        assert config.failure_window == 300.0
        assert config.exponential_backoff is True
        assert config.enable_metrics is True
    
    def test_custom_config(self):
        """Testa configuração customizada."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout_threshold=15.0,
            exponential_backoff=False
        )
        
        assert config.failure_threshold == 3
        assert config.success_threshold == 2
        assert config.timeout_threshold == 15.0
        assert config.exponential_backoff is False


class TestAdvancedCircuitBreaker:
    """Testes para AdvancedCircuitBreaker."""
    
    @pytest.fixture
    def circuit_breaker(self):
        """Fixture para circuit breaker de teste."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            success_threshold=2,
            timeout_threshold=1.0,
            open_timeout=2.0,
            half_open_timeout=1.0,
            exponential_backoff=False  # Desabilitar backoff para testes
        )
        return AdvancedCircuitBreaker("test_cb", config)
    
    def test_initial_state(self, circuit_breaker):
        """Testa estado inicial do circuit breaker."""
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.is_closed
        assert not circuit_breaker.is_open
        assert not circuit_breaker.is_half_open
        assert circuit_breaker._failure_count == 0
        assert circuit_breaker._success_count == 0
    
    @pytest.mark.asyncio
    async def test_successful_call(self, circuit_breaker):
        """Testa chamada bem-sucedida."""
        async def success_func():
            return "success"
        
        result = await circuit_breaker.call(success_func)
        
        assert result == "success"
        assert circuit_breaker._success_count == 1
        assert circuit_breaker._consecutive_successes == 1
        assert circuit_breaker._consecutive_failures == 0
        assert circuit_breaker.state == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_failed_call(self, circuit_breaker):
        """Testa chamada com falha."""
        async def fail_func():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            await circuit_breaker.call(fail_func)
        
        assert circuit_breaker._failure_count == 1
        assert circuit_breaker._consecutive_failures == 1
        assert circuit_breaker._consecutive_successes == 0
        assert len(circuit_breaker._failure_history) == 1
    
    @pytest.mark.asyncio
    async def test_timeout_call(self, circuit_breaker):
        """Testa chamada com timeout."""
        async def slow_func():
            await asyncio.sleep(2.0)  # Maior que timeout_threshold
            return "slow"
        
        with pytest.raises(asyncio.TimeoutError):
            await circuit_breaker.call(slow_func)
        
        assert circuit_breaker._failure_count == 1
        assert len(circuit_breaker._failure_history) == 1
        assert circuit_breaker._failure_history[0].failure_type == FailureType.TIMEOUT
    
    @pytest.mark.asyncio
    async def test_circuit_opens_after_failures(self, circuit_breaker):
        """Testa abertura do circuit após falhas."""
        async def fail_func():
            raise ConnectionError("Connection failed")
        
        # Executar falhas até atingir threshold
        for i in range(circuit_breaker.config.failure_threshold):
            with pytest.raises(ConnectionError):
                await circuit_breaker.call(fail_func)
        
        # Circuit deve estar aberto
        assert circuit_breaker.state == CircuitState.OPEN
        assert circuit_breaker.is_open
        
        # Próxima chamada deve falhar com CircuitBreakerException
        with pytest.raises(CircuitBreakerException):
            await circuit_breaker.call(fail_func)
    
    @pytest.mark.asyncio
    async def test_circuit_half_open_transition(self, circuit_breaker):
        """Testa transição para half-open."""
        # Forçar abertura
        await circuit_breaker.force_open()
        assert circuit_breaker.state == CircuitState.FORCED_OPEN
        
        # Aguardar timeout e verificar transição
        await asyncio.sleep(circuit_breaker.config.open_timeout + 0.1)
        
        # Simular atualização de estado
        await circuit_breaker._update_state()
        
        # Deve estar em half-open após timeout
        assert circuit_breaker.state == CircuitState.HALF_OPEN
    
    @pytest.mark.asyncio
    async def test_circuit_closes_after_successes(self, circuit_breaker):
        """Testa fechamento do circuit após sucessos em half-open."""
        # Colocar em half-open
        await circuit_breaker._transition_to_half_open()
        assert circuit_breaker.state == CircuitState.HALF_OPEN
        
        async def success_func():
            return "success"
        
        # Executar sucessos até atingir threshold
        for i in range(circuit_breaker.config.success_threshold):
            result = await circuit_breaker.call(success_func)
            assert result == "success"
        
        # Circuit deve estar fechado
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.is_closed
    
    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        """Testa backoff exponencial."""
        # Criar circuit breaker com backoff habilitado
        config = CircuitBreakerConfig(
            failure_threshold=5,
            exponential_backoff=True,
            backoff_multiplier=2.0
        )
        cb = AdvancedCircuitBreaker("backoff_test", config)
        
        async def fail_func():
            raise ValueError("Test error")
        
        # Primeira falha
        with pytest.raises(ValueError):
            await cb.call(fail_func)
        
        initial_backoff = cb._current_backoff
        
        # Aguardar backoff antes da próxima tentativa
        await asyncio.sleep(cb._current_backoff + 0.1)
        
        # Segunda falha
        with pytest.raises(ValueError):
            await cb.call(fail_func)
        
        # Backoff deve ter aumentado
        assert cb._current_backoff > initial_backoff
    
    @pytest.mark.asyncio
    async def test_force_open_and_close(self, circuit_breaker):
        """Testa abertura e fechamento forçados."""
        # Forçar abertura
        await circuit_breaker.force_open()
        assert circuit_breaker.state == CircuitState.FORCED_OPEN
        
        # Forçar fechamento
        await circuit_breaker.force_close()
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker._consecutive_failures == 0
        assert circuit_breaker._current_backoff == 1.0
    
    @pytest.mark.asyncio
    async def test_reset(self, circuit_breaker):
        """Testa reset do circuit breaker."""
        # Causar algumas falhas
        async def fail_func():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError):
            await circuit_breaker.call(fail_func)
        
        assert circuit_breaker._failure_count > 0
        assert len(circuit_breaker._failure_history) > 0
        
        # Reset
        await circuit_breaker.reset()
        
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker._failure_count == 0
        assert circuit_breaker._success_count == 0
        assert len(circuit_breaker._failure_history) == 0
        assert circuit_breaker._current_backoff == 1.0
    
    def test_error_classification(self, circuit_breaker):
        """Testa classificação de erros."""
        # Timeout
        timeout_error = Exception("Request timeout")
        assert circuit_breaker._classify_error(timeout_error) == FailureType.TIMEOUT
        
        # Connection error
        conn_error = ConnectionError("Connection refused")
        assert circuit_breaker._classify_error(conn_error) == FailureType.CONNECTION_ERROR
        
        # Rate limit
        rate_error = Exception("Rate limit exceeded (429)")
        assert circuit_breaker._classify_error(rate_error) == FailureType.RATE_LIMIT
        
        # Auth error
        auth_error = Exception("Unauthorized (401)")
        assert circuit_breaker._classify_error(auth_error) == FailureType.AUTHENTICATION_ERROR
        
        # HTTP error
        http_error = Exception("Internal server error (500)")
        assert circuit_breaker._classify_error(http_error) == FailureType.HTTP_ERROR
        
        # Unknown error
        unknown_error = Exception("Unknown error")
        assert circuit_breaker._classify_error(unknown_error) == FailureType.UNKNOWN_ERROR
    
    def test_health_status(self, circuit_breaker):
        """Testa status de saúde."""
        health = circuit_breaker.get_health_status()
        
        assert "name" in health
        assert "state" in health
        assert "time_in_state" in health
        assert "consecutive_failures" in health
        assert "consecutive_successes" in health
        assert "metrics" in health
        assert "config" in health
        
        assert health["name"] == "test_cb"
        assert health["state"] == "closed"
        assert health["consecutive_failures"] == 0


class TestCircuitBreakerDecorator:
    """Testes para o decorator de circuit breaker."""
    
    @pytest.mark.asyncio
    async def test_decorator_success(self):
        """Testa decorator com função bem-sucedida."""
        config = CircuitBreakerConfig(failure_threshold=2)
        
        @circuit_breaker("test_decorator", config)
        async def decorated_func(value):
            return f"result: {value}"
        
        result = await decorated_func("test")
        assert result == "result: test"
        
        # Verificar que circuit breaker foi criado
        assert hasattr(decorated_func, 'circuit_breaker')
        assert decorated_func.circuit_breaker.name == "test_decorator"
    
    @pytest.mark.asyncio
    async def test_decorator_failure(self):
        """Testa decorator com função que falha."""
        config = CircuitBreakerConfig(
            failure_threshold=2,  # Aumentar threshold para 2
            exponential_backoff=False  # Desabilitar backoff para teste
        )
        
        @circuit_breaker("test_fail_decorator", config)
        async def failing_func():
            raise ValueError("Decorator test error")
        
        # Primeira falha
        with pytest.raises(ValueError):
            await failing_func()
        
        # Circuit ainda deve estar fechado
        assert failing_func.circuit_breaker.state == CircuitState.CLOSED
        
        # Segunda falha deve abrir o circuit
        with pytest.raises(ValueError):
            await failing_func()
        
        # Circuit deve estar aberto
        assert failing_func.circuit_breaker.state == CircuitState.OPEN
        
        # Próxima chamada deve falhar com CircuitBreakerException
        with pytest.raises(CircuitBreakerException):
            await failing_func()


class TestCircuitBreakerRegistry:
    """Testes para o registry de circuit breakers."""
    
    def test_get_circuit_breaker(self):
        """Testa obtenção de circuit breaker do registry."""
        cb1 = get_circuit_breaker("registry_test")
        cb2 = get_circuit_breaker("registry_test")
        
        # Deve retornar a mesma instância
        assert cb1 is cb2
        assert cb1.name == "registry_test"
    
    def test_get_circuit_breaker_with_config(self):
        """Testa obtenção com configuração customizada."""
        config = CircuitBreakerConfig(failure_threshold=10)
        cb = get_circuit_breaker("config_test", config)
        
        assert cb.config.failure_threshold == 10
    
    @pytest.mark.asyncio
    async def test_reset_all_circuit_breakers(self):
        """Testa reset de todos os circuit breakers."""
        # Criar alguns circuit breakers
        cb1 = get_circuit_breaker("reset_test_1")
        cb2 = get_circuit_breaker("reset_test_2")
        
        # Simular algumas falhas
        cb1._failure_count = 5
        cb2._failure_count = 3
        
        # Reset todos
        await reset_all_circuit_breakers()
        
        # Verificar que foram resetados
        assert cb1._failure_count == 0
        assert cb2._failure_count == 0
        assert cb1.state == CircuitState.CLOSED
        assert cb2.state == CircuitState.CLOSED


class TestCircuitBreakerIntegration:
    """Testes de integração para circuit breakers."""
    
    @pytest.mark.asyncio
    async def test_multiple_circuit_breakers(self):
        """Testa múltiplos circuit breakers independentes."""
        cb1 = get_circuit_breaker("service_1")
        cb2 = get_circuit_breaker("service_2")
        
        async def service1_func():
            raise ConnectionError("Service 1 error")
        
        async def service2_func():
            return "Service 2 OK"
        
        # Service 1 falha
        with pytest.raises(ConnectionError):
            await cb1.call(service1_func)
        
        # Service 2 funciona
        result = await cb2.call(service2_func)
        assert result == "Service 2 OK"
        
        # Verificar estados independentes
        assert cb1._failure_count > 0
        assert cb2._failure_count == 0
        assert cb1._success_count == 0
        assert cb2._success_count > 0
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_with_retries(self):
        """Testa circuit breaker com lógica de retry."""
        config = CircuitBreakerConfig(
            failure_threshold=5,  # Aumentar threshold para permitir retries
            exponential_backoff=False  # Desabilitar backoff para teste
        )
        cb = get_circuit_breaker("retry_test", config)
        call_count = 0
        
        async def unreliable_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary error")
            return "Success after retries"
        
        # Implementar retry simples
        max_retries = 3
        for attempt in range(max_retries):
            try:
                result = await cb.call(unreliable_func)
                assert result == "Success after retries"
                break
            except (ConnectionError, CircuitBreakerException):
                if attempt == max_retries - 1:
                    raise
                await asyncio.sleep(0.1)
        
        assert call_count == 3
        assert cb._success_count > 0


if __name__ == "__main__":
    pytest.main([__file__])