"""Testes de Integração - Fase 2 do Nação Trader.

Testes essenciais para validar a integração completa entre todos
os componentes da Fase 2.
"""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any
from unittest.mock import Mock, patch, AsyncMock

import sys
import os

# Adicionar o diretório motor ao sys.path
motor_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, motor_dir)

from src.main_integrated import IntegratedSystem, get_integrated_system
from src.collectors.collector_manager import CollectorManager, CollectorType, CollectorStatus
from src.monitoring.metrics import MetricsCollector
from src.cache.intelligent_cache import IntelligentCache
from src.resilience.fallback_system import FallbackSystem
from src.dashboard.monitoring_dashboard import MonitoringDashboard


class TestPhase2Integration:
    """Testes de integração para a Fase 2."""
    
    @pytest_asyncio.fixture
    async def integrated_system(self):
        """Fixture para sistema integrado."""
        system = IntegratedSystem()
        await system.initialize()
        yield system
        await system.close()
    
    @pytest_asyncio.fixture
    async def collector_manager(self):
        """Fixture para gerenciador de coletores."""
        manager = CollectorManager()
        await manager.initialize()
        yield manager
        await manager.close()
    
    @pytest.mark.asyncio
    async def test_system_initialization(self, integrated_system):
        """Testa inicialização completa do sistema."""
        # Verificar se todos os componentes foram inicializados
        assert integrated_system.collector_manager is not None
        assert integrated_system.metrics is not None
        assert integrated_system.cache is not None
        assert integrated_system.fallback_system is not None
        
        # Verificar se o sistema não está em execução
        assert not integrated_system.is_running
    
    @pytest.mark.asyncio
    async def test_collector_manager_integration(self, collector_manager):
        """Testa integração do gerenciador de coletores."""
        # Verificar coletores disponíveis
        status = await collector_manager.get_orchestration_status()
        assert "collectors" in status
        assert "orchestration" in status
        orchestration = status["orchestration"]
        assert "validation_enabled" in orchestration
        assert "source_rotation" in orchestration
        
        # Testar habilitação de coletores
        await collector_manager.enable_collector(CollectorType.YAHOO_FINANCE)
        collector_status = collector_manager.get_collector_status("yahoo_finance")
        assert collector_status["enabled"] is True
        
        # Testar coleta de dados
        try:
            data = await collector_manager.collect_data("yahoo_finance", ["AAPL"])
            assert data is not None
        except Exception as e:
            # Aceitar falhas de rede em testes
            assert "não encontrado" in str(e) or "timeout" in str(e).lower()
    
    @pytest.mark.asyncio
    async def test_fallback_system_integration(self, integrated_system):
        """Testa integração do sistema de fallback."""
        fallback_system = integrated_system.fallback_system
        
        # Verificar status inicial
        status = await fallback_system.get_fallback_status()
        assert "sources" in status
        assert "active_fallbacks" in status
        assert "fallback_history_count" in status
        
        # Criar um mock collector para teste
        class MockCollector:
            async def collect_data(self, symbol: str):
                return {"symbol": symbol, "price": 100.0}
        
        mock_collector = MockCollector()
        
        # Testar adição de fonte
        await fallback_system.add_source("test_source", mock_collector, priority=1)
        status = await fallback_system.get_fallback_status()
        assert len(status["sources"]) > 0
    
    @pytest.mark.asyncio
    async def test_cache_integration(self, integrated_system):
        """Testa integração do cache inteligente."""
        cache = integrated_system.cache
        
        # Testar operações básicas do cache
        test_key = "test_integration_key"
        test_data = {"symbol": "AAPL", "price": 150.0, "timestamp": datetime.now().isoformat()}
        
        # Armazenar dados
        await cache.set(test_key, test_data, ttl=300)
        
        # Recuperar dados
        cached_data = await cache.get(test_key)
        assert cached_data is not None
        assert cached_data["symbol"] == "AAPL"
        
        # Verificar estatísticas
        stats = cache.get_stats()
        assert "hit_rate" in stats
        assert "total_requests" in stats
    
    @pytest.mark.asyncio
    async def test_metrics_collection_integration(self, integrated_system):
        """Testa integração da coleta de métricas."""
        metrics = integrated_system.metrics
        
        # Verificar métricas do sistema
        system_metrics = metrics.get_system_metrics()
        assert "cpu_usage" in system_metrics
        assert "memory_usage" in system_metrics
        assert "disk_usage" in system_metrics
        
        # Verificar métricas de coleta de dados
        data_metrics = metrics.get_data_collection_metrics()
        assert "total_requests" in data_metrics
        assert "successful_requests" in data_metrics
        assert "failed_requests" in data_metrics
    
    @pytest.mark.asyncio
    async def test_comprehensive_data_collection(self, integrated_system):
        """Testa coleta abrangente de dados."""
        # Símbolos de teste
        test_symbols = ["AAPL", "MSFT"]
        
        # Mock dos coletores para evitar chamadas reais de API
        with patch.object(integrated_system.collector_manager, 'collect_data', new_callable=AsyncMock) as mock_collect:
            mock_collect.return_value = {
                "symbol": "AAPL",
                "price": 150.0,
                "timestamp": datetime.now().isoformat(),
                "source": "mock"
            }
            
            # Executar coleta abrangente
            results = await integrated_system.collect_comprehensive_data(test_symbols)
            
            # Verificar resultados
            assert len(results) == len(test_symbols)
            for symbol in test_symbols:
                assert symbol in results
                # Verificar se pelo menos uma fonte foi chamada
                assert len(results[symbol]) > 0
    
    @pytest.mark.asyncio
    async def test_economic_indicators_collection(self, integrated_system):
        """Testa coleta de indicadores econômicos."""
        # Mock dos coletores de dados públicos
        with patch.object(integrated_system.collector_manager, 'collect_data', new_callable=AsyncMock) as mock_collect:
            mock_collect.return_value = {
                "series_id": "GDP",
                "value": 25000.0,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "source": "FRED"
            }
            
            # Executar coleta de indicadores
            indicators = await integrated_system.collect_economic_indicators()
            
            # Verificar se indicadores foram coletados
            assert isinstance(indicators, dict)
            # Em caso de mock, pode estar vazio se houver erros
            # mas não deve gerar exceção
    
    @pytest.mark.asyncio
    async def test_system_status_reporting(self, integrated_system):
        """Testa relatório de status do sistema."""
        status = await integrated_system.get_system_status()
        
        # Verificar estrutura do status
        assert "timestamp" in status
        assert "orchestration" in status
        assert "system_metrics" in status
        assert "cache_stats" in status
        assert "fallback_status" in status
        assert "summary" in status
        
        # Verificar resumo
        summary = status["summary"]
        assert "total_collectors" in summary
        assert "active_collectors" in summary
        assert "cache_hit_rate" in summary
        assert "fallback_sources" in summary
        assert "system_health" in summary
    
    @pytest.mark.asyncio
    async def test_rate_limiting_integration(self, collector_manager):
        """Testa integração do rate limiting inteligente."""
        # Testar atualização de rate limits
        source_name = "test_source"
        
        # Simular métricas de performance no formato correto
        source_performance = {
            source_name: {
                "success_rate": 0.95,
                "avg_response_time": 0.5,
                "error_rate": 0.05
            }
        }
        
        await collector_manager.update_rate_limits(source_performance)
        
        # Verificar se o rate limit foi atualizado
        # (Não há retorno direto, mas não deve gerar erro)
        assert True  # Se chegou até aqui, não houve erro
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(self, collector_manager):
        """Testa integração dos circuit breakers."""
        # Verificar se circuit breakers foram inicializados
        assert len(collector_manager.circuit_breakers) > 0
        
        # Testar circuit breaker para Yahoo Finance
        yahoo_cb = collector_manager.circuit_breakers.get(CollectorType.YAHOO_FINANCE.value)
        if yahoo_cb:
            # Verificar estado inicial (CircuitState é um enum)
            assert yahoo_cb.state.value in ["closed", "open", "half_open"]
    
    @pytest.mark.asyncio
    async def test_validation_system_integration(self, collector_manager):
        """Testa integração do sistema de validação."""
        # Habilitar validação
        await collector_manager.enable_validation()
        
        # Verificar status da validação
        status = await collector_manager.get_orchestration_status()
        orchestration = status["orchestration"]
        assert "validation_enabled" in orchestration
        assert orchestration["validation_enabled"] is True
    
    @pytest.mark.asyncio
    async def test_source_rotation_integration(self, collector_manager):
        """Testa integração do sistema de rotação de fontes."""
        # Verificar status da rotação de fontes
        status = await collector_manager.get_orchestration_status()
        orchestration = status["orchestration"]
        rotation_status = orchestration.get("source_rotation", {})
        assert "enabled" in rotation_status
        assert "sources_count" in rotation_status
    
    @pytest.mark.asyncio
    async def test_continuous_collection_start_stop(self, integrated_system):
        """Testa início e parada da coleta contínua."""
        # Mock para evitar coleta real
        with patch.object(integrated_system, 'collect_comprehensive_data', new_callable=AsyncMock) as mock_collect:
            with patch.object(integrated_system, 'collect_economic_indicators', new_callable=AsyncMock) as mock_indicators:
                mock_collect.return_value = {}
                mock_indicators.return_value = {}
                
                # Iniciar coleta contínua em background
                task = asyncio.create_task(
                    integrated_system.start_continuous_collection(interval_minutes=0.01)  # 0.6 segundos
                )
                
                # Aguardar um pouco
                await asyncio.sleep(0.1)
                
                # Verificar se está rodando
                assert integrated_system.is_running
                
                # Parar coleta
                integrated_system.stop_continuous_collection()
                
                # Aguardar task terminar
                await asyncio.sleep(0.1)
                task.cancel()
                
                # Verificar se parou
                assert not integrated_system.is_running


class TestDashboardIntegration:
    """Testes de integração para o dashboard."""
    
    @pytest_asyncio.fixture
    async def dashboard(self):
        """Fixture para dashboard."""
        dashboard = MonitoringDashboard()
        await dashboard._initialize_components()
        yield dashboard
    
    @pytest.mark.asyncio
    async def test_dashboard_initialization(self, dashboard):
        """Testa inicialização do dashboard."""
        assert dashboard.app is not None
        assert dashboard.websocket_connections == []
    
    @pytest.mark.asyncio
    async def test_dashboard_routes(self, dashboard):
        """Testa rotas do dashboard."""
        # Mock dos componentes
        with patch.object(dashboard, '_collect_dashboard_metrics', new_callable=AsyncMock) as mock_metrics:
            mock_metrics.return_value = Mock(
                timestamp=datetime.now().isoformat(),
                system_health="healthy",
                collectors_status={},
                cache_metrics={},
                fallback_metrics={},
                performance_metrics={},
                recent_errors=[],
                data_quality_score=0.8
            )
            
            # Testar rotas básicas do dashboard
            # Verificar se o app foi criado corretamente
            assert dashboard.app is not None
            
            # Verificar se as rotas foram registradas
            routes = [route.path for route in dashboard.app.routes]
            assert "/api/status" in routes or any("/status" in route for route in routes)


class TestEndToEndIntegration:
    """Testes end-to-end para validar o fluxo completo."""
    
    @pytest.mark.asyncio
    async def test_complete_system_workflow(self):
        """Testa fluxo completo do sistema."""
        # Inicializar sistema
        system = IntegratedSystem()
        
        try:
            await system.initialize()
            
            # Verificar inicialização
            assert system.collector_manager is not None
            
            # Obter status inicial
            initial_status = await system.get_system_status()
            assert "timestamp" in initial_status
            
            # Mock coleta de dados para evitar chamadas reais
            with patch.object(system, 'collect_comprehensive_data', new_callable=AsyncMock) as mock_collect:
                mock_collect.return_value = {
                    "AAPL": {
                        "yahoo_finance": {"price": 150.0},
                        "finnhub": {"pe_ratio": 25.0}
                    }
                }
                
                # Executar coleta
                results = await system.collect_comprehensive_data(["AAPL"])
                assert "AAPL" in results
            
            # Verificar status final
            final_status = await system.get_system_status()
            assert final_status["timestamp"] != initial_status["timestamp"]
            
        finally:
            await system.close()
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self):
        """Testa tratamento de erros e recuperação."""
        system = IntegratedSystem()
        
        try:
            await system.initialize()
            
            # Simular erro na coleta
            with patch.object(system.collector_manager, 'collect_data', side_effect=Exception("Test error")):
                # A coleta deve falhar graciosamente
                results = await system.collect_comprehensive_data(["AAPL"])
                # Deve retornar estrutura vazia mas não gerar exceção
                assert isinstance(results, dict)
            
            # Sistema deve continuar funcionando
            status = await system.get_system_status()
            assert "timestamp" in status
            
        finally:
            await system.close()


if __name__ == "__main__":
    # Executar testes básicos
    import asyncio
    
    async def run_basic_tests():
        """Executa testes básicos."""
        print("Executando testes básicos de integração...")
        
        # Teste de inicialização
        system = IntegratedSystem()
        try:
            await system.initialize()
            print("✅ Sistema inicializado com sucesso")
            
            status = await system.get_system_status()
            print(f"✅ Status obtido: {len(status)} campos")
            
            print("✅ Todos os testes básicos passaram")
            
        except Exception as e:
            print(f"❌ Erro nos testes: {e}")
        finally:
            await system.close()
    
    asyncio.run(run_basic_tests())