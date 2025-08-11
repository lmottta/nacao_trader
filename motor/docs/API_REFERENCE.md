# API Reference - Fase 2: Sistema Avançado de Coleta

## Visão Geral

Esta documentação descreve as APIs e interfaces dos componentes implementados na Fase 2 do Motor de Sinais ML.

## CollectorManager

### Classe Principal

```python
class CollectorManager:
    """Gerenciador central de coletores de dados."""
```

### Métodos

#### `register_collector(name, collector_type, collector_func, config)`

Registra um novo coletor no sistema.

**Parâmetros:**
- `name` (str): Nome único do coletor
- `collector_type` (CollectorType): Tipo do coletor
- `collector_func` (callable): Função de coleta
- `config` (CollectorConfig): Configuração do coletor

**Retorno:** None

**Exemplo:**
```python
await manager.register_collector(
    "yahoo_finance",
    CollectorType.MARKET_DATA,
    yahoo_collector_func,
    CollectorConfig(interval=60.0)
)
```

#### `collect_data(collector_name, symbol, **kwargs)`

Coleta dados usando um coletor específico.

**Parâmetros:**
- `collector_name` (str): Nome do coletor
- `symbol` (str): Símbolo do ativo
- `**kwargs`: Parâmetros adicionais

**Retorno:** Dict com os dados coletados

**Exemplo:**
```python
data = await manager.collect_data("yahoo_finance", "AAPL")
```

#### `get_collector_status(collector_name)`

Obtém o status de um coletor.

**Parâmetros:**
- `collector_name` (str): Nome do coletor

**Retorno:** Dict com informações de status

**Exemplo:**
```python
status = manager.get_collector_status("yahoo_finance")
# Retorna: {
#     "active": True,
#     "last_collection": "2025-01-04T10:30:00Z",
#     "success_rate": 0.95,
#     "total_collections": 1500
# }
```

#### `enable_collector(collector_name)`

Habilita um coletor.

**Parâmetros:**
- `collector_name` (str): Nome do coletor

**Retorno:** None

#### `disable_collector(collector_name)`

Desabilita um coletor.

**Parâmetros:**
- `collector_name` (str): Nome do coletor

**Retorno:** None

## FallbackSystem

### Classe Principal

```python
class FallbackSystem:
    """Sistema de fallback automático entre fontes."""
```

### Métodos

#### `add_source(name, collector_func, priority)`

Adiciona uma fonte de dados ao sistema de fallback.

**Parâmetros:**
- `name` (str): Nome da fonte
- `collector_func` (callable): Função de coleta
- `priority` (int): Prioridade da fonte (menor = maior prioridade)

**Retorno:** None

**Exemplo:**
```python
await fallback.add_source("yahoo", yahoo_func, priority=1)
await fallback.add_source("alpha_vantage", av_func, priority=2)
```

#### `collect_with_fallback(symbol, **kwargs)`

Coleta dados com fallback automático.

**Parâmetros:**
- `symbol` (str): Símbolo do ativo
- `**kwargs`: Parâmetros adicionais

**Retorno:** Tuple (data, source_used)

**Exemplo:**
```python
data, source = await fallback.collect_with_fallback("AAPL")
print(f"Dados obtidos de: {source}")
```

#### `get_status()`

Obtém status do sistema de fallback.

**Retorno:** Dict com informações de status

**Exemplo:**
```python
status = await fallback.get_status()
# Retorna: {
#     "sources": [
#         {"name": "yahoo", "priority": 1, "active": True, "success_rate": 0.98},
#         {"name": "alpha_vantage", "priority": 2, "active": True, "success_rate": 0.92}
#     ],
#     "current_source": "yahoo",
#     "fallback_count": 5
# }
```

## IntelligentCache

### Classe Principal

```python
class IntelligentCache:
    """Cache inteligente com TTL dinâmico."""
```

### Métodos

#### `set(key, value, ttl=None)`

Armazena um valor no cache.

**Parâmetros:**
- `key` (str): Chave do cache
- `value` (Any): Valor a ser armazenado
- `ttl` (int, optional): TTL em segundos

**Retorno:** None

**Exemplo:**
```python
await cache.set("AAPL_price", {"price": 150.0}, ttl=300)
```

#### `get(key)`

Recupera um valor do cache.

**Parâmetros:**
- `key` (str): Chave do cache

**Retorno:** Valor armazenado ou None

**Exemplo:**
```python
value = await cache.get("AAPL_price")
if value:
    print(f"Preço em cache: {value['price']}")
```

#### `delete(key)`

Remove um valor do cache.

**Parâmetros:**
- `key` (str): Chave do cache

**Retorno:** bool (True se removido)

#### `clear()`

Limpa todo o cache.

**Retorno:** None

#### `get_stats()`

Obtém estatísticas do cache.

**Retorno:** Dict com estatísticas

**Exemplo:**
```python
stats = await cache.get_stats()
# Retorna: {
#     "hits": 1250,
#     "misses": 180,
#     "hit_rate": 0.874,
#     "size": 450,
#     "max_size": 1000
# }
```

## MetricsCollector

### Classe Principal

```python
class MetricsCollector:
    """Coletor de métricas do sistema."""
```

### Métodos

#### `collect_system_metrics()`

Coleta métricas do sistema.

**Retorno:** Dict com métricas do sistema

**Exemplo:**
```python
metrics = await collector.collect_system_metrics()
# Retorna: {
#     "cpu_percent": 15.2,
#     "memory_percent": 45.8,
#     "disk_usage": 67.3,
#     "network_io": {"bytes_sent": 1024000, "bytes_recv": 2048000}
# }
```

#### `record_data_collection(collector_name, success, duration, data_size)`

Registra uma coleta de dados.

**Parâmetros:**
- `collector_name` (str): Nome do coletor
- `success` (bool): Se a coleta foi bem-sucedida
- `duration` (float): Duração em segundos
- `data_size` (int): Tamanho dos dados em bytes

**Retorno:** None

#### `get_collector_metrics(collector_name)`

Obtém métricas de um coletor específico.

**Parâmetros:**
- `collector_name` (str): Nome do coletor

**Retorno:** Dict com métricas do coletor

**Exemplo:**
```python
metrics = await collector.get_collector_metrics("yahoo_finance")
# Retorna: {
#     "total_requests": 1500,
#     "successful_requests": 1425,
#     "failed_requests": 75,
#     "success_rate": 0.95,
#     "avg_response_time": 0.245,
#     "total_data_collected": 15728640
# }
```

## RateLimiter

### Classe Principal

```python
class RateLimiter:
    """Rate limiter inteligente com token bucket."""
```

### Métodos

#### `__init__(requests_per_minute, burst_size=None, adaptive=False)`

Inicializa o rate limiter.

**Parâmetros:**
- `requests_per_minute` (int): Limite de requisições por minuto
- `burst_size` (int, optional): Tamanho do burst
- `adaptive` (bool): Se deve ajustar limites automaticamente

#### `acquire(tokens=1)`

Adquire tokens para fazer requisições.

**Parâmetros:**
- `tokens` (int): Número de tokens necessários

**Retorno:** bool (True se tokens foram adquiridos)

**Exemplo:**
```python
if await rate_limiter.acquire():
    # Fazer requisição
    response = await make_request()
else:
    # Rate limit atingido, aguardar
    await asyncio.sleep(1)
```

#### `get_status()`

Obtém status do rate limiter.

**Retorno:** Dict com informações de status

**Exemplo:**
```python
status = rate_limiter.get_status()
# Retorna: {
#     "available_tokens": 45,
#     "max_tokens": 100,
#     "requests_per_minute": 100,
#     "last_refill": "2025-01-04T10:30:00Z"
# }
```

## CrossValidator

### Classe Principal

```python
class CrossValidator:
    """Validador cruzado de dados entre fontes."""
```

### Métodos

#### `add_source(name, collector_func, weight=1.0)`

Adiciona uma fonte para validação.

**Parâmetros:**
- `name` (str): Nome da fonte
- `collector_func` (callable): Função de coleta
- `weight` (float): Peso da fonte na validação

**Retorno:** None

#### `validate_data(symbol, **kwargs)`

Valida dados coletando de múltiplas fontes.

**Parâmetros:**
- `symbol` (str): Símbolo do ativo
- `**kwargs`: Parâmetros adicionais

**Retorno:** Dict com dados validados e score de confiança

**Exemplo:**
```python
result = await validator.validate_data("AAPL")
# Retorna: {
#     "validated_data": {"price": 150.25, "volume": 1000000},
#     "confidence_score": 0.95,
#     "sources_used": ["yahoo", "alpha_vantage"],
#     "discrepancies": []
# }
```

#### `get_validation_stats()`

Obtém estatísticas de validação.

**Retorno:** Dict com estatísticas

## CircuitBreaker

### Classe Principal

```python
class CircuitBreaker:
    """Circuit breaker para proteção contra falhas."""
```

### Métodos

#### `__init__(failure_threshold=5, recovery_timeout=60, expected_exception=Exception)`

Inicializa o circuit breaker.

**Parâmetros:**
- `failure_threshold` (int): Número de falhas para abrir o circuito
- `recovery_timeout` (int): Tempo para tentar recovery
- `expected_exception` (Exception): Tipo de exceção esperada

#### `call(func, *args, **kwargs)`

Executa uma função protegida pelo circuit breaker.

**Parâmetros:**
- `func` (callable): Função a ser executada
- `*args, **kwargs`: Argumentos da função

**Retorno:** Resultado da função ou levanta CircuitBreakerOpenException

**Exemplo:**
```python
cb = CircuitBreaker(failure_threshold=3, recovery_timeout=30)

try:
    result = await cb.call(risky_function, param1, param2)
except CircuitBreakerOpenException:
    # Circuito aberto, usar fallback
    result = await fallback_function()
```

#### `get_state()`

Obtém o estado atual do circuit breaker.

**Retorno:** str ("closed", "open", "half_open")

## WebScrapingCollector

### Classe Principal

```python
class WebScrapingCollector:
    """Coletor de dados via web scraping."""
```

### Métodos

#### `collect_data(url, selectors, **kwargs)`

Coleta dados de uma página web.

**Parâmetros:**
- `url` (str): URL da página
- `selectors` (dict): Seletores CSS para extração
- `**kwargs`: Parâmetros adicionais

**Retorno:** Dict com dados extraídos

**Exemplo:**
```python
data = await scraper.collect_data(
    "https://example.com/stock/AAPL",
    {
        "price": ".price-value",
        "volume": ".volume-value",
        "change": ".change-value"
    }
)
```

## WebSocketCollector

### Classe Principal

```python
class WebSocketCollector:
    """Coletor de dados via WebSocket."""
```

### Métodos

#### `connect(url, **kwargs)`

Conecta ao WebSocket.

**Parâmetros:**
- `url` (str): URL do WebSocket
- `**kwargs`: Parâmetros de conexão

**Retorno:** None

#### `subscribe(symbol, callback)`

Inscreve-se para receber dados de um símbolo.

**Parâmetros:**
- `symbol` (str): Símbolo do ativo
- `callback` (callable): Função de callback para dados

**Retorno:** None

**Exemplo:**
```python
def on_data(data):
    print(f"Dados recebidos: {data}")

await ws_collector.connect("wss://api.example.com/ws")
await ws_collector.subscribe("AAPL", on_data)
```

## PublicDataCollector

### Classe Principal

```python
class PublicDataCollector:
    """Coletor de dados de APIs públicas."""
```

### Métodos

#### `collect_fred_data(series_id, **kwargs)`

Coleta dados do FRED.

**Parâmetros:**
- `series_id` (str): ID da série do FRED
- `**kwargs`: Parâmetros adicionais

**Retorno:** Dict com dados da série

#### `collect_world_bank_data(indicator, country, **kwargs)`

Coleta dados do World Bank.

**Parâmetros:**
- `indicator` (str): Indicador econômico
- `country` (str): Código do país
- `**kwargs`: Parâmetros adicionais

**Retorno:** Dict com dados do indicador

## Tipos e Enums

### CollectorType

```python
class CollectorType(Enum):
    MARKET_DATA = "market_data"
    ECONOMIC_DATA = "economic_data"
    NEWS_DATA = "news_data"
    SOCIAL_DATA = "social_data"
    TECHNICAL_DATA = "technical_data"
```

### CollectorConfig

```python
@dataclass
class CollectorConfig:
    interval: float = 60.0
    max_retries: int = 3
    timeout: float = 30.0
    rate_limit: int = 100
    enable_cache: bool = True
    cache_ttl: int = 300
    enable_fallback: bool = True
    priority: int = 1
```

## Exceções

### CollectorException

```python
class CollectorException(Exception):
    """Exceção base para coletores."""
```

### RateLimitExceededException

```python
class RateLimitExceededException(CollectorException):
    """Exceção para rate limit excedido."""
```

### CircuitBreakerOpenException

```python
class CircuitBreakerOpenException(CollectorException):
    """Exceção para circuit breaker aberto."""
```

### ValidationException

```python
class ValidationException(CollectorException):
    """Exceção para falhas de validação."""
```

## Exemplos de Uso Completo

### Sistema Integrado

```python
import asyncio
from src.main_integrated import IntegratedSystem

async def exemplo_completo():
    # Inicializar sistema
    system = IntegratedSystem()
    await system.initialize()
    
    # Configurar coletores
    await system.setup_default_collectors()
    
    # Coletar dados com validação
    data = await system.collect_validated_data("AAPL")
    print(f"Dados validados: {data}")
    
    # Obter métricas
    metrics = await system.get_comprehensive_metrics()
    print(f"Métricas do sistema: {metrics}")
    
    # Parar sistema
    await system.stop()

if __name__ == "__main__":
    asyncio.run(exemplo_completo())
```

### Uso Individual de Componentes

```python
import asyncio
from src.collectors.collector_manager import CollectorManager
from src.resilience.fallback_system import FallbackSystem
from src.cache.intelligent_cache import IntelligentCache

async def exemplo_componentes():
    # Configurar cache
    cache = IntelligentCache(max_size=1000)
    
    # Configurar fallback
    fallback = FallbackSystem()
    await fallback.add_source("primary", primary_collector, 1)
    await fallback.add_source("secondary", secondary_collector, 2)
    
    # Configurar manager
    manager = CollectorManager(cache=cache, fallback=fallback)
    
    # Registrar coletor
    await manager.register_collector(
        "yahoo",
        CollectorType.MARKET_DATA,
        yahoo_collector,
        CollectorConfig(interval=30.0)
    )
    
    # Coletar dados
    data = await manager.collect_data("yahoo", "AAPL")
    print(f"Dados coletados: {data}")

if __name__ == "__main__":
    asyncio.run(exemplo_componentes())
```

Esta documentação fornece uma referência completa das APIs implementadas na Fase 2. Todos os métodos são assíncronos e seguem as melhores práticas de Python para programação assíncrona.