"""Dashboard de Monitoramento - Fase 2 do Nação Trader.

Dashboard básico para monitorar o status de todos os componentes
do sistema integrado da Fase 2.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from ..main_integrated import get_integrated_system
from ..collectors.collector_manager import CollectorType, CollectorStatus
from ..monitoring.metrics import get_metrics_collector
from ..cache.intelligent_cache import get_cache
from ..resilience.fallback_system import get_fallback_system


class HealthStatus(Enum):
    """Status de saúde do sistema."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class DashboardMetrics:
    """Métricas para o dashboard."""
    timestamp: str
    system_health: HealthStatus
    collectors_status: Dict[str, Any]
    cache_metrics: Dict[str, Any]
    fallback_metrics: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    recent_errors: List[Dict[str, Any]]
    data_quality_score: float


class MonitoringDashboard:
    """Dashboard de monitoramento do sistema."""
    
    def __init__(self):
        self.app = FastAPI(title="Nação Trader - Dashboard de Monitoramento")
        self.integrated_system = None
        self.metrics_collector = None
        self.cache = None
        self.fallback_system = None
        self.websocket_connections: List[WebSocket] = []
        
        self._setup_routes()
        self._setup_middleware()
    
    def _setup_middleware(self):
        """Configura middleware do FastAPI."""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    def _setup_routes(self):
        """Configura as rotas do dashboard."""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def dashboard_home():
            """Página principal do dashboard."""
            return self._get_dashboard_html()
        
        @self.app.get("/api/status")
        async def get_system_status():
            """Obtém status completo do sistema."""
            try:
                if not self.integrated_system:
                    await self._initialize_components()
                
                metrics = await self._collect_dashboard_metrics()
                return asdict(metrics)
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/collectors")
        async def get_collectors_status():
            """Obtém status detalhado dos coletores."""
            try:
                if not self.integrated_system:
                    await self._initialize_components()
                
                status = await self.integrated_system.get_system_status()
                return status.get("orchestration", {})
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/metrics")
        async def get_performance_metrics():
            """Obtém métricas de performance."""
            try:
                if not self.metrics_collector:
                    await self._initialize_components()
                
                return {
                    "system": self.metrics_collector.get_system_metrics(),
                    "data_collection": self.metrics_collector.get_data_collection_metrics(),
                    "cache": self.metrics_collector.get_cache_metrics(),
                    "circuit_breaker": self.metrics_collector.get_circuit_breaker_metrics()
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/cache")
        async def get_cache_status():
            """Obtém status do cache."""
            try:
                if not self.cache:
                    await self._initialize_components()
                
                return self.cache.get_stats()
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/fallback")
        async def get_fallback_status():
            """Obtém status do sistema de fallback."""
            try:
                if not self.fallback_system:
                    await self._initialize_components()
                
                return await self.fallback_system.get_fallback_status()
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/collectors/{collector_type}/enable")
        async def enable_collector(collector_type: str):
            """Habilita um coletor específico."""
            try:
                if not self.integrated_system:
                    await self._initialize_components()
                
                collector_enum = CollectorType(collector_type)
                await self.integrated_system.collector_manager.enable_collector(collector_enum)
                return {"status": "success", "message": f"Coletor {collector_type} habilitado"}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.post("/api/collectors/{collector_type}/disable")
        async def disable_collector(collector_type: str):
            """Desabilita um coletor específico."""
            try:
                if not self.integrated_system:
                    await self._initialize_components()
                
                collector_enum = CollectorType(collector_type)
                await self.integrated_system.collector_manager.disable_collector(collector_enum)
                return {"status": "success", "message": f"Coletor {collector_type} desabilitado"}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """WebSocket para atualizações em tempo real."""
            await websocket.accept()
            self.websocket_connections.append(websocket)
            
            try:
                while True:
                    # Enviar métricas atualizadas a cada 5 segundos
                    if self.integrated_system:
                        metrics = await self._collect_dashboard_metrics()
                        await websocket.send_text(json.dumps(asdict(metrics), default=str))
                    
                    await asyncio.sleep(5)
            except WebSocketDisconnect:
                self.websocket_connections.remove(websocket)
    
    async def _initialize_components(self):
        """Inicializa os componentes do sistema."""
        if not self.integrated_system:
            self.integrated_system = get_integrated_system()
            await self.integrated_system.initialize()
        
        if not self.metrics_collector:
            self.metrics_collector = get_metrics_collector()
        
        if not self.cache:
            self.cache = await get_cache()
        
        if not self.fallback_system:
            self.fallback_system = await get_fallback_system()
    
    async def _collect_dashboard_metrics(self) -> DashboardMetrics:
        """Coleta métricas para o dashboard."""
        try:
            # Status do sistema
            system_status = await self.integrated_system.get_system_status()
            
            # Métricas de performance
            system_metrics = self.metrics_collector.get_system_metrics()
            cache_metrics = self.cache.get_stats()
            fallback_status = await self.fallback_system.get_fallback_status()
            
            # Determinar saúde do sistema
            health = self._determine_system_health(system_metrics, system_status)
            
            # Calcular score de qualidade dos dados
            data_quality = self._calculate_data_quality_score(system_status)
            
            # Obter erros recentes
            recent_errors = self._get_recent_errors()
            
            return DashboardMetrics(
                timestamp=datetime.now().isoformat(),
                system_health=health,
                collectors_status=system_status.get("orchestration", {}),
                cache_metrics=cache_metrics,
                fallback_metrics=fallback_status,
                performance_metrics=system_metrics,
                recent_errors=recent_errors,
                data_quality_score=data_quality
            )
        
        except Exception as e:
            return DashboardMetrics(
                timestamp=datetime.now().isoformat(),
                system_health=HealthStatus.UNKNOWN,
                collectors_status={},
                cache_metrics={},
                fallback_metrics={},
                performance_metrics={},
                recent_errors=[{"error": str(e), "timestamp": datetime.now().isoformat()}],
                data_quality_score=0.0
            )
    
    def _determine_system_health(self, system_metrics: Dict, system_status: Dict) -> HealthStatus:
        """Determina a saúde geral do sistema."""
        try:
            cpu_usage = system_metrics.get("cpu_percent", 0)
            memory_usage = system_metrics.get("memory_percent", 0)
            
            active_collectors = system_status.get("summary", {}).get("active_collectors", 0)
            total_collectors = system_status.get("summary", {}).get("total_collectors", 1)
            
            collector_ratio = active_collectors / total_collectors if total_collectors > 0 else 0
            
            # Critérios de saúde
            if cpu_usage > 90 or memory_usage > 90 or collector_ratio < 0.3:
                return HealthStatus.CRITICAL
            elif cpu_usage > 70 or memory_usage > 70 or collector_ratio < 0.7:
                return HealthStatus.WARNING
            elif collector_ratio >= 0.7:
                return HealthStatus.HEALTHY
            else:
                return HealthStatus.UNKNOWN
        
        except Exception:
            return HealthStatus.UNKNOWN
    
    def _calculate_data_quality_score(self, system_status: Dict) -> float:
        """Calcula um score de qualidade dos dados."""
        try:
            cache_hit_rate = system_status.get("cache_stats", {}).get("hit_rate", 0)
            active_collectors = system_status.get("summary", {}).get("active_collectors", 0)
            total_collectors = system_status.get("summary", {}).get("total_collectors", 1)
            
            collector_score = (active_collectors / total_collectors) * 0.6
            cache_score = cache_hit_rate * 0.4
            
            return min(1.0, collector_score + cache_score)
        
        except Exception:
            return 0.0
    
    def _get_recent_errors(self) -> List[Dict[str, Any]]:
        """Obtém erros recentes do sistema."""
        # Por enquanto, retorna lista vazia
        # Em uma implementação completa, isso viria de um sistema de logging
        return []
    
    def _get_dashboard_html(self) -> str:
        """Retorna o HTML do dashboard."""
        return """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nação Trader - Dashboard de Monitoramento</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            min-height: 100vh;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .card {
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            transition: transform 0.3s ease;
        }
        
        .card:hover {
            transform: translateY(-5px);
        }
        
        .card h3 {
            color: #4a5568;
            margin-bottom: 15px;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 10px;
        }
        
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        
        .status-healthy { background-color: #48bb78; }
        .status-warning { background-color: #ed8936; }
        .status-critical { background-color: #f56565; }
        .status-unknown { background-color: #a0aec0; }
        
        .metric-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
            padding: 8px 0;
            border-bottom: 1px solid #f7fafc;
        }
        
        .metric-label {
            font-weight: 500;
            color: #4a5568;
        }
        
        .metric-value {
            font-weight: bold;
            color: #2d3748;
        }
        
        .progress-bar {
            width: 100%;
            height: 8px;
            background-color: #e2e8f0;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 5px;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #48bb78, #38a169);
            transition: width 0.3s ease;
        }
        
        .collectors-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 10px;
            margin-top: 15px;
        }
        
        .collector-item {
            background: #f7fafc;
            padding: 10px;
            border-radius: 6px;
            text-align: center;
        }
        
        .refresh-btn {
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 16px;
            margin: 20px auto;
            display: block;
            transition: transform 0.2s ease;
        }
        
        .refresh-btn:hover {
            transform: scale(1.05);
        }
        
        .timestamp {
            text-align: center;
            color: white;
            margin-top: 20px;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Nação Trader</h1>
            <p>Dashboard de Monitoramento - Fase 2</p>
        </div>
        
        <div class="dashboard-grid">
            <div class="card">
                <h3>🏥 Saúde do Sistema</h3>
                <div id="system-health">
                    <div class="metric-row">
                        <span class="metric-label">Status:</span>
                        <span class="metric-value" id="health-status">
                            <span class="status-indicator status-unknown"></span>
                            Carregando...
                        </span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">CPU:</span>
                        <span class="metric-value" id="cpu-usage">--%</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Memória:</span>
                        <span class="metric-value" id="memory-usage">--%</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Qualidade dos Dados:</span>
                        <span class="metric-value" id="data-quality">--%</span>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <h3>📊 Coletores</h3>
                <div id="collectors-status">
                    <div class="metric-row">
                        <span class="metric-label">Ativos:</span>
                        <span class="metric-value" id="active-collectors">-- / --</span>
                    </div>
                    <div class="collectors-grid" id="collectors-grid">
                        <!-- Coletores serão inseridos aqui -->
                    </div>
                </div>
            </div>
            
            <div class="card">
                <h3>💾 Cache</h3>
                <div id="cache-metrics">
                    <div class="metric-row">
                        <span class="metric-label">Taxa de Hit:</span>
                        <span class="metric-value" id="cache-hit-rate">--%</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Entradas:</span>
                        <span class="metric-value" id="cache-entries">--</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Tamanho:</span>
                        <span class="metric-value" id="cache-size">-- MB</span>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <h3>🔄 Sistema de Fallback</h3>
                <div id="fallback-metrics">
                    <div class="metric-row">
                        <span class="metric-label">Fontes Ativas:</span>
                        <span class="metric-value" id="fallback-sources">--</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Execuções:</span>
                        <span class="metric-value" id="fallback-executions">--</span>
                    </div>
                    <div class="metric-row">
                        <span class="metric-label">Taxa de Sucesso:</span>
                        <span class="metric-value" id="fallback-success-rate">--%</span>
                    </div>
                </div>
            </div>
        </div>
        
        <button class="refresh-btn" onclick="refreshDashboard()">🔄 Atualizar Dashboard</button>
        
        <div class="timestamp" id="last-update">
            Última atualização: --
        </div>
    </div>
    
    <script>
        let ws = null;
        
        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws`;
            
            ws = new WebSocket(wsUrl);
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                updateDashboard(data);
            };
            
            ws.onclose = function() {
                setTimeout(connectWebSocket, 5000); // Reconectar após 5 segundos
            };
        }
        
        function updateDashboard(data) {
            // Atualizar saúde do sistema
            const healthStatus = document.getElementById('health-status');
            const healthIndicator = healthStatus.querySelector('.status-indicator');
            
            healthIndicator.className = `status-indicator status-${data.system_health}`;
            healthStatus.innerHTML = `<span class="status-indicator status-${data.system_health}"></span>${data.system_health.toUpperCase()}`;
            
            // Atualizar métricas de performance
            document.getElementById('cpu-usage').textContent = `${(data.performance_metrics.cpu_percent || 0).toFixed(1)}%`;
            document.getElementById('memory-usage').textContent = `${(data.performance_metrics.memory_percent || 0).toFixed(1)}%`;
            document.getElementById('data-quality').textContent = `${(data.data_quality_score * 100).toFixed(1)}%`;
            
            // Atualizar coletores
            const collectorsData = data.collectors_status.collectors || {};
            const activeCount = Object.values(collectorsData).filter(c => c.status === 'running').length;
            const totalCount = Object.keys(collectorsData).length;
            
            document.getElementById('active-collectors').textContent = `${activeCount} / ${totalCount}`;
            
            // Atualizar grid de coletores
            const collectorsGrid = document.getElementById('collectors-grid');
            collectorsGrid.innerHTML = '';
            
            Object.entries(collectorsData).forEach(([name, collector]) => {
                const item = document.createElement('div');
                item.className = 'collector-item';
                item.innerHTML = `
                    <div><strong>${name}</strong></div>
                    <div><span class="status-indicator status-${collector.status === 'running' ? 'healthy' : 'critical'}"></span>${collector.status}</div>
                `;
                collectorsGrid.appendChild(item);
            });
            
            // Atualizar cache
            document.getElementById('cache-hit-rate').textContent = `${((data.cache_metrics.hit_rate || 0) * 100).toFixed(1)}%`;
            document.getElementById('cache-entries').textContent = data.cache_metrics.total_entries || 0;
            document.getElementById('cache-size').textContent = `${((data.cache_metrics.memory_usage || 0) / 1024 / 1024).toFixed(1)} MB`;
            
            // Atualizar fallback
            const fallbackSources = data.fallback_metrics.sources || [];
            document.getElementById('fallback-sources').textContent = fallbackSources.length;
            document.getElementById('fallback-executions').textContent = data.fallback_metrics.total_executions || 0;
            
            const successRate = data.fallback_metrics.success_rate || 0;
            document.getElementById('fallback-success-rate').textContent = `${(successRate * 100).toFixed(1)}%`;
            
            // Atualizar timestamp
            document.getElementById('last-update').textContent = `Última atualização: ${new Date(data.timestamp).toLocaleString()}`;
        }
        
        async function refreshDashboard() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                updateDashboard(data);
            } catch (error) {
                console.error('Erro ao atualizar dashboard:', error);
            }
        }
        
        // Inicializar
        document.addEventListener('DOMContentLoaded', function() {
            refreshDashboard();
            connectWebSocket();
        });
    </script>
</body>
</html>
        """
    
    async def start_server(self, host: str = "0.0.0.0", port: int = 8080):
        """Inicia o servidor do dashboard."""
        await self._initialize_components()
        
        config = uvicorn.Config(
            app=self.app,
            host=host,
            port=port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()


# Instância global do dashboard
_dashboard: Optional[MonitoringDashboard] = None


def get_monitoring_dashboard() -> MonitoringDashboard:
    """Obtém a instância global do dashboard."""
    global _dashboard
    if _dashboard is None:
        _dashboard = MonitoringDashboard()
    return _dashboard


async def start_dashboard(host: str = "0.0.0.0", port: int = 8080):
    """Inicia o dashboard de monitoramento."""
    dashboard = get_monitoring_dashboard()
    await dashboard.start_server(host, port)


if __name__ == "__main__":
    import sys
    
    host = sys.argv[1] if len(sys.argv) > 1 else "0.0.0.0"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8080
    
    print(f"Iniciando Dashboard de Monitoramento em http://{host}:{port}")
    asyncio.run(start_dashboard(host, port))