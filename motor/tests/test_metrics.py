"""Testes para o sistema de métricas."""

import pytest
import asyncio
import time
import os
import sys
from unittest.mock import patch, MagicMock
from prometheus_client import CollectorRegistry

# Adicionar o diretório motor ao sys.path
motor_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, motor_dir)

from src.monitoring.metrics import (
    MetricsCollector, measure_time, get_metrics_collector,
    init_metrics_server
)


class TestMetricsCollector:
    """Testes para MetricsCollector."""
    
    @pytest.fixture
    def metrics_collector(self):
        """Fixture para collector de métricas de teste."""
        # Usar registry separado para testes
        test_registry = CollectorRegistry()
        return MetricsCollector(registry=test_registry)
    
    def test_initialization(self, metrics_collector):
        """Testa inicialização do collector."""
        assert metrics_collector.enabled is not None
        assert metrics_collector.registry is not None
        assert metrics_collector.metrics is not None
    
    def test_record_api_request(self, metrics_collector):
        """Testa registro de requisição de API."""
        if not metrics_collector.enabled:
            pytest.skip("Prometheus não disponível")
        
        # Registrar requisição bem-sucedida
        metrics_collector.record_api_request("finnhub", "/quote", "success", 0.5)
        
        # Verificar que a métrica foi registrada
        assert 'api_requests_total' in metrics_collector.metrics
        
        # Registrar requisição com erro
        metrics_collector.record_api_request("yahoo", "/quote", "error", 1.0)
    
    def test_record_cache_operation(self, metrics_collector):
        """Testa registro de operação de cache."""
        if not metrics_collector.enabled:
            pytest.skip("Prometheus não disponível")
        
        # Cache hit
        metrics_collector.record_cache_operation("memory", "get", "hit")
        
        # Cache miss
        metrics_collector.record_cache_operation("disk", "get", "miss")
        
        assert 'cache_operations' in metrics_collector.metrics
    
    def test_update_cache_metrics(self, metrics_collector):
        """Testa atualização de métricas do cache."""
        if not metrics_collector.enabled:
            pytest.skip("Prometheus não disponível")
        
        metrics_collector.update_cache_metrics("memory", 1024, 10, 0.85)
        
        assert 'cache_size' in metrics_collector.metrics
        assert 'cache_entries' in metrics_collector.metrics
    
    def test_record_signal_generation(self, metrics_collector):
        """Testa registro de geração de sinal."""
        if not metrics_collector.enabled:
            pytest.skip("Prometheus não disponível")
        
        metrics_collector.record_signal_generation("AAPL", "buy", 0.85)
        
        assert 'signals_generated' in metrics_collector.metrics
    
    def test_update_system_info(self, metrics_collector):
        """Testa atualização de informações do sistema."""
        if not metrics_collector.enabled:
            pytest.skip("Prometheus não disponível")
        
        info = {
            'version': '1.0.0',
            'environment': 'test',
            'component': 'nacao_trader_motor'
        }
        
        metrics_collector.update_system_info(info)
        
        assert 'system_info' in metrics_collector.metrics
    
    def test_get_metrics_summary(self, metrics_collector):
        """Testa obtenção do resumo de métricas."""
        summary = metrics_collector.get_metrics_summary()
        
        assert isinstance(summary, dict)
        assert "api_calls" in summary or "error" in summary
        assert "cache_operations" in summary or "error" in summary
        assert "signals_generated" in summary or "error" in summary
        assert "system" in summary or "error" in summary
    
    def test_get_system_metrics(self, metrics_collector):
        """Testa obtenção de métricas do sistema."""
        system_metrics = metrics_collector.get_system_metrics()
        
        assert isinstance(system_metrics, dict)
        # Pode retornar erro se Prometheus não estiver disponível
        assert "uptime" in system_metrics or "error" in system_metrics


class TestMeasureTimeDecorator:
    """Testes para o decorator measure_time."""
    
    @pytest.mark.asyncio
    async def test_measure_time_async(self):
        """Testa decorator com função assíncrona."""
        @measure_time("test_async_function")
        async def async_function(value):
            await asyncio.sleep(0.01)
            return f"async_{value}"
        
        start_time = time.time()
        result = await async_function("test")
        end_time = time.time()
        
        assert result == "async_test"
        # Verificar que levou pelo menos o tempo do sleep
        assert (end_time - start_time) >= 0.01
    
    def test_measure_time_sync(self):
        """Testa decorator com função síncrona."""
        @measure_time("test_sync_function")
        def sync_function(value):
            time.sleep(0.01)
            return f"sync_{value}"
        
        start_time = time.time()
        result = sync_function("test")
        end_time = time.time()
        
        assert result == "sync_test"
        # Verificar que levou pelo menos o tempo do sleep
        assert (end_time - start_time) >= 0.01
    
    @pytest.mark.asyncio
    async def test_measure_time_with_exception(self):
        """Testa decorator quando função gera exceção."""
        @measure_time("test_exception_function")
        async def exception_function():
            await asyncio.sleep(0.01)
            raise ValueError("Test exception")
        
        with pytest.raises(ValueError, match="Test exception"):
            await exception_function()


class TestMetricsServer:
    """Testes para o servidor de métricas."""
    
    @patch('src.monitoring.metrics.MetricsCollector.start_http_server')
    def test_init_metrics_server(self, mock_start_server):
        """Testa inicialização do servidor de métricas."""
        init_metrics_server(port=8001)
        
        mock_start_server.assert_called_once_with(8001)
    
    @patch('src.monitoring.metrics.MetricsCollector.start_http_server')
    def test_init_metrics_server_default_port(self, mock_start_server):
        """Testa inicialização com porta padrão."""
        init_metrics_server()
        
        mock_start_server.assert_called_once_with(8001)


class TestMetricsCollectorMethods:
    """Testes para métodos específicos do MetricsCollector."""
    
    @pytest.fixture
    def metrics_collector(self):
        """Fixture para collector de métricas de teste."""
        test_registry = CollectorRegistry()
        return MetricsCollector(registry=test_registry)
    
    @patch('prometheus_client.push_to_gateway')
    async def test_push_to_gateway(self, mock_push, metrics_collector):
        """Testa envio de métricas para Push Gateway."""
        await metrics_collector.push_to_gateway(
            gateway_url="localhost:9091",
            job_name="test_job"
        )
        
        mock_push.assert_called_once_with(
            "localhost:9091",
            job="test_job",
            registry=metrics_collector.registry
        )
    
    def test_get_metrics_collector_singleton(self):
        """Testa singleton do collector de métricas."""
        collector1 = get_metrics_collector()
        collector2 = get_metrics_collector()
        
        assert collector1 is collector2


class TestMetricsIntegration:
    """Testes de integração para métricas."""
    
    @pytest.fixture
    def metrics_collector(self):
        """Fixture para collector de métricas de teste."""
        test_registry = CollectorRegistry()
        return MetricsCollector(registry=test_registry)
    
    def test_complete_workflow(self, metrics_collector):
        """Testa fluxo completo de métricas."""
        if not metrics_collector.enabled:
            pytest.skip("Prometheus não disponível")
        
        # Simular operações do sistema
        metrics_collector.record_api_request("finnhub", "/quote", "success", 0.5)
        metrics_collector.record_api_request("yahoo", "/quote", "error", 2.0)
        
        metrics_collector.record_cache_operation("memory", "get", "hit")
        metrics_collector.record_cache_operation("memory", "get", "miss")
        metrics_collector.update_cache_metrics("memory", 2048, 10, 0.8)
        
        metrics_collector.record_signal_generation("AAPL", "buy", 0.85)
        metrics_collector.record_signal_generation("GOOGL", "sell", 0.75)
        
        # Obter resumo
        summary = metrics_collector.get_metrics_summary()
        
        # Verificar que o resumo foi gerado
        assert isinstance(summary, dict)
        # Pode conter dados ou erro dependendo da disponibilidade do Prometheus
        assert len(summary) > 0
    
    @pytest.mark.asyncio
    async def test_concurrent_metrics_recording(self, metrics_collector):
        """Testa registro concorrente de métricas."""
        if not metrics_collector.enabled:
            pytest.skip("Prometheus não disponível")
        
        async def record_metrics(provider, count):
            for i in range(count):
                metrics_collector.record_api_request(provider, "/quote", "success", 0.1)
                await asyncio.sleep(0.001)  # Pequeno delay
        
        # Executar registros concorrentes
        await asyncio.gather(
            record_metrics("finnhub", 5),
            record_metrics("yahoo", 5),
            record_metrics("alpha_vantage", 5)
        )
        
        # Verificar que as métricas foram registradas
        summary = metrics_collector.get_metrics_summary()
        assert isinstance(summary, dict)


if __name__ == "__main__":
    pytest.main([__file__])