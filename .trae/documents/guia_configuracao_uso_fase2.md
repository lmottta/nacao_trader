# Guia de Configuração e Uso - Fase 2

## Motor de Sinais ML - Sistema Avançado de Coleta de Dados

## 1. Pré-requisitos

### 1.1 Requisitos do Sistema

* **Python**: 3.11 ou superior

* **Node.js**: 18 ou superior (para frontend)

* **PostgreSQL**: 14 ou superior (via Supabase)

* **Redis**: 6 ou superior (opcional, para cache distribuído)

### 1.2 Dependências Python

```bash
# Instalar dependências
pip install -r requirements.txt

# Principais dependências
aiohttp>=3.8.0
fastapi>=0.104.0
uvicorn>=0.24.0
supabase>=2.0.0
psycopg2-binary>=2.9.0
redis>=5.0.0
pandas>=2.0.0
numpy>=1.24.0
scipy>=1.10.0
websockets>=11.0.0
requests>=2.31.0
pytest>=7.4.0
pytest-asyncio>=0.21.0
```

### 1.3 APIs Necessárias

* **Supabase**: Banco de dados e autenticação

* **Finnhub**: Dados de mercado (opcional)

* **FRED**: Dados econômicos americanos (opcional)

* **Alpha Vantage**: Dados financeiros (opcional)

* **Binance**: Dados de criptomoedas (opcional)

## 2. Configuração Inicial

### 2.1 Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto:

```bash
# Banco de Dados
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_SERVICE_KEY=your_supabase_service_key
DATABASE_URL=postgresql://postgres:password@db.your-project.supabase.co:5432/postgres

# APIs Externas (opcionais)
FINNHUB_API_KEY=your_finnhub_api_key
FRED_API_KEY=your_fred_api_key
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key
BINANCE_API_KEY=your_binance_api_key
BINANCE_SECRET_KEY=your_binance_secret

# Cache (opcional)
REDIS_URL=redis://localhost:6379/0

# Configurações do Sistema
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# Monitoramento
DASHBOARD_PORT=8081
METRICS_INTERVAL=60
ENABLE_MONITORING=true

# Rate Limiting
DEFAULT_RATE_LIMIT=1.0
WEB_SCRAPING_RATE_LIMIT=2.0
API_RATE_LIMIT=0.5

# Cache
DEFAULT_CACHE_TTL=300
MAX_CACHE_SIZE=1000
CACHE_CLEANUP_INTERVAL=3600

# Proxy (para web scraping)
USE_PROXIES=false
PROXY_LIST=proxy1:port,proxy2:port
PROXY_ROTATION_INTERVAL=300

# WebSocket
WS_RECONNECT_INTERVAL=5
WS_MAX_RECONNECT_ATTEMPTS=10
WS_HEARTBEAT_INTERVAL=30
```

### 2.2 Configuração do Banco de Dados

```bash
# Executar script de configuração
python run_setup.py

# Ou executar manualmente
python -c "from src.db.migrations.setup_timescaledb import main; import asyncio; asyncio.run(main())"
```

### 2.3 Verificação da Instalação

```bash
# Verificar ambiente
python run_setup.py --env-only

# Executar testes
pytest tests/ -v

# Executar testes de integração
python -m pytest tests/test_integration_phase2.py -v
```

## 3. Uso Básico

### 3.1 Inicialização do Sistema

```python
# exemplo_basico.py
import asyncio
from src.collectors.collector_manager import CollectorManager, CollectorType
from src.utils.config import settings

async def main():
    # Inicializar o gerenciador de coletores
    manager = CollectorManager()
    
    # Habilitar coletores desejados
    await manager.enable_collector(CollectorType.YAHOO_FINANCE)
    await manager.enable_collector(CollectorType.WEB_SCRAPING)
    
    # Coletar dados
    symbols = ["AAPL", "GOOGL", "MSFT"]
    data = await manager.collect_data(symbols)
    
    print(f"Dados coletados: {len(data)} registros")
    for symbol, info in data.items():
        print(f"{symbol}: {info['price']} ({info['source']})")
    
    # Obter métricas
    metrics = await manager.get_metrics()
    print(f"Métricas: {metrics}")

if __name__ == "__main__":
    asyncio.run(main())
```

### 3.2 Configuração de Coletores Específicos

#### Yahoo Finance

```python
from src.collectors.yahoo_finance_collector import YahooFinanceCollector
from src.collectors.collector_manager import CollectorConfig

# Configuração personalizada
config = CollectorConfig(
    enabled=True,
    interval=60.0,  # 1 minuto
    timeout=30,
    rate_limit=1.0,
    cache_ttl=300,
    priority=1
)

# Registrar coletor
await manager.register_collector(
    "yahoo_custom",
    CollectorType.MARKET_DATA,
    YahooFinanceCollector().collect_data,
    config
)
```

#### Web Scraping

```python
from src.web_scraping.web_scraping_collector import WebScrapingCollector

# Configurar web scraping
web_config = {
    "use_proxies": True,
    "proxy_list": ["proxy1:8080", "proxy2:8080"],
    "user_agents": [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    ],
    "rate_limit": 2.0,
    "timeout": 45
}

collector = WebScrapingCollector(web_config)
await manager.enable_collector(CollectorType.WEB_SCRAPING)
```

#### WebSocket (Binance)

```python
from src.websockets.binance_websocket_collector import BinanceWebSocketCollector

# Configurar WebSocket
ws_collector = BinanceWebSocketCollector()
await ws_collector.start()

# Subscrever símbolos
symbols = ["BTCUSDT", "ETHUSDT", "ADAUSDT"]
for symbol in symbols:
    await ws_collector.subscribe(symbol)

# Obter dados em tempo real
latest_data = await ws_collector.get_latest_data(symbols)
print(f"Dados em tempo real: {latest_data}")
```

#### Dados Públicos (FRED)

```python
from src.public_data.fred_collector import FREDCollector

# Configurar FRED
fred_collector = FREDCollector()

# Coletar indicadores econômicos
indicators = ["GDP", "UNRATE", "FEDFUNDS", "CPIAUCSL"]
economic_data = await fred_collector.collect_data(indicators)

print(f"Dados econômicos: {economic_data}")
```

### 3.3 Validação Cruzada

```python
from src.validation.cross_validator import CrossValidator

# Inicializar validador
validator = CrossValidator()

# Configurar fontes para validação
sources = ["yahoo_finance", "web_scraping", "finnhub"]

# Validar dados
symbols = ["AAPL", "GOOGL"]
validation_results = await validator.validate_cross_sources(
    symbols, sources
)

for symbol, result in validation_results.items():
    print(f"{symbol}:")
    print(f"  Qualidade: {result['quality_score']:.2f}")
    print(f"  Consistência: {result['consistency_score']:.2f}")
    print(f"  Anomalias: {len(result['anomalies'])}")
```

### 3.4 Sistema de Fallback

```python
from src.resilience.fallback_system import FallbackSystem, FallbackStrategy

# Configurar sistema de fallback
fallback = FallbackSystem(
    strategy=FallbackStrategy.PERFORMANCE_BASED,
    max_retries=3,
    timeout=30
)

# Adicionar fontes
fallback.add_source("yahoo_finance", priority=1)
fallback.add_source("web_scraping", priority=2)
fallback.add_source("finnhub", priority=3)

# Executar com fallback automático
result = await fallback.execute_with_fallback(
    lambda source: manager.collect_data_from_source(["AAPL"], source),
    context={"symbol": "AAPL"}
)

print(f"Dados obtidos de: {result.source_used}")
print(f"Tentativas: {result.attempts}")
print(f"Dados: {result.data}")
```

## 4. Configuração Avançada

### 4.1 Cache Inteligente

```python
from src.cache.intelligent_cache import IntelligentCache

# Configurar cache
cache = IntelligentCache(
    default_ttl=300,  # 5 minutos
    max_size=1000,
    cleanup_interval=3600  # 1 hora
)

# Usar cache manualmente
key = "AAPL_price_data"
data = await cache.get(key)

if data is None:
    # Buscar dados
    data = await fetch_price_data("AAPL")
    await cache.set(key, data, ttl=600)  # Cache por 10 minutos

print(f"Dados (cache): {data}")

# Estatísticas do cache
stats = await cache.get_stats()
print(f"Hit rate: {stats['hit_rate']:.2f}%")
print(f"Itens no cache: {stats['size']}")
```

### 4.2 Métricas e Monitoramento

```python
from src.monitoring.metrics import MetricsCollector

# Inicializar coletor de métricas
metrics = MetricsCollector()

# Registrar métricas customizadas
metrics.record_counter("custom_requests", 1, {"endpoint": "/api/data"})
metrics.record_histogram("response_time", 0.25, {"method": "GET"})
metrics.record_gauge("active_connections", 42)

# Obter métricas do sistema
system_metrics = await metrics.get_system_metrics()
print(f"CPU: {system_metrics['cpu_percent']:.1f}%")
print(f"Memória: {system_metrics['memory_percent']:.1f}%")

# Métricas dos coletores
collector_metrics = await metrics.get_collector_metrics()
for collector, data in collector_metrics.items():
    print(f"{collector}: {data['success_rate']:.1f}% sucesso")
```

### 4.3 Rate Limiting Personalizado

```python
from src.resilience.rate_limiter import RateLimiter

# Configurar rate limiter
limiter = RateLimiter(
    requests_per_second=2.0,
    burst_size=5,
    window_size=60
)

# Usar rate limiter
async def fetch_with_limit(url):
    async with limiter:
        response = await http_client.get(url)
        return response.json()

# Rate limiting por domínio
domain_limiters = {
    "api.example.com": RateLimiter(1.0),
    "data.provider.com": RateLimiter(0.5)
}

async def fetch_with_domain_limit(url):
    domain = extract_domain(url)
    limiter = domain_limiters.get(domain, default_limiter)
    
    async with limiter:
        return await http_client.get(url)
```

## 5. Dashboard de Monitoramento

### 5.1 Iniciar Dashboard

```bash
# Iniciar dashboard na porta 8081
python start_dashboard.py localhost 8081

# Ou usar o script de configuração
python scripts/setup_monitoring.py
```

### 5.2 Acessar Dashboard

* **URL**: <http://localhost:8081>

* **Funcionalidades**:

  * Status em tempo real dos coletores

  * Métricas de performance

  * Gráficos de taxa de sucesso

  * Logs do sistema

  * Controle manual de coletores

### 5.3 API do Dashboard

```python
# Obter status via API
import aiohttp

async def get_dashboard_status():
    async with aiohttp.ClientSession() as session:
        async with session.get("http://localhost:8081/api/status") as response:
            return await response.json()

status = await get_dashboard_status()
print(f"Sistema: {status['system_health']}")
print(f"Coletores ativos: {len(status['active_collectors'])}")
```

## 6. Testes e Validação

### 6.1 Executar Testes

```bash
# Todos os testes
pytest tests/ -v

# Testes específicos
pytest tests/test_collector_manager.py -v
pytest tests/test_integration_phase2.py -v

# Testes com cobertura
pytest tests/ --cov=src --cov-report=html

# Testes de performance
pytest tests/test_performance.py -v --benchmark-only
```

### 6.2 Testes de Integração

```python
# test_custom_integration.py
import pytest
import asyncio
from src.collectors.collector_manager import CollectorManager, CollectorType

@pytest.mark.asyncio
async def test_full_integration():
    """Teste de integração completa."""
    manager = CollectorManager()
    
    # Habilitar coletores
    await manager.enable_collector(CollectorType.YAHOO_FINANCE)
    await manager.enable_collector(CollectorType.WEB_SCRAPING)
    
    # Coletar dados
    symbols = ["AAPL", "GOOGL"]
    data = await manager.collect_data(symbols)
    
    # Validações
    assert len(data) > 0
    assert "AAPL" in data
    assert "price" in data["AAPL"]
    assert data["AAPL"]["price"] > 0
    
    # Verificar métricas
    metrics = await manager.get_metrics()
    assert metrics["total_requests"] > 0
    assert metrics["success_rate"] > 0.8
```

### 6.3 Testes de Carga

```python
# test_load.py
import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

async def load_test():
    """Teste de carga do sistema."""
    manager = CollectorManager()
    await manager.enable_collector(CollectorType.YAHOO_FINANCE)
    
    symbols = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA"]
    
    # Executar 100 requisições concorrentes
    tasks = []
    start_time = time.time()
    
    for i in range(100):
        task = manager.collect_data(symbols)
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    end_time = time.time()
    
    # Analisar resultados
    successful = sum(1 for r in results if not isinstance(r, Exception))
    failed = len(results) - successful
    duration = end_time - start_time
    
    print(f"Requisições: {len
```

