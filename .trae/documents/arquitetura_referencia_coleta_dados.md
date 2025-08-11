# Arquitetura de Referência - Sistema de Coleta de Dados
## Projeto Nação Trader - Guia de Implementação

## 1. Visão Geral da Arquitetura

### 1.1 Princípios Arquiteturais

- **Resiliência**: Sistema deve operar mesmo com falhas parciais
- **Escalabilidade**: Suporte a crescimento horizontal e vertical
- **Observabilidade**: Visibilidade completa do comportamento do sistema
- **Independência**: Redução máxima de dependências externas
- **Performance**: Latência mínima e throughput máximo

### 1.2 Arquitetura de Alto Nível

```mermaid
graph TB
    subgraph "Frontend Layer"
        UI["React Dashboard"]
        API_GW["API Gateway"]
    end
    
    subgraph "Application Layer"
        LB["Load Balancer"]
        CM["Collector Manager"]
        SG["Signal Generator"]
        WS["WebSocket Server"]
    end
    
    subgraph "Data Collection Layer"
        YFC["Yahoo Finance Collector"]
        WSC["WebSocket Collector"]
        SCR["Web Scraping Collector"]
        PDC["Public Data Collector"]
        FHC["Finnhub Collector"]
    end
    
    subgraph "Intelligence Layer"
        CB["Circuit Breakers"]
        IC["Intelligent Cache"]
        PC["Predictive Cache"]
        HM["Health Monitor"]
    end
    
    subgraph "Storage Layer"
        REDIS[("Redis Cluster")]
        TSDB[("TimescaleDB")]
        DISK[("Disk Cache")]
    end
    
    subgraph "Monitoring Layer"
        PROM["Prometheus"]
        GRAF["Grafana"]
        ALERT["AlertManager"]
    end
    
    subgraph "External Sources"
        YF["Yahoo Finance"]
        BIN["Binance"]
        FRED["FRED API"]
        BCB["Banco Central"]
    end
    
    UI --> API_GW
    API_GW --> LB
    LB --> CM
    CM --> SG
    CM --> WS
    
    CM --> YFC
    CM --> WSC
    CM --> SCR
    CM --> PDC
    CM --> FHC
    
    YFC --> CB
    WSC --> CB
    SCR --> CB
    PDC --> CB
    FHC --> CB
    
    CB --> IC
    IC --> PC
    IC --> HM
    
    IC --> REDIS
    IC --> TSDB
    IC --> DISK
    
    CM --> PROM
    PROM --> GRAF
    PROM --> ALERT
    
    YFC --> YF
    WSC --> BIN
    PDC --> FRED
    PDC --> BCB
```

## 2. Componentes Detalhados

### 2.1 Collector Manager

**Responsabilidades:**
- Orquestração de todos os coletores
- Load balancing entre fontes
- Failover automático
- Agregação de dados

**Interface:**
```python
class CollectorManager:
    async def collect_realtime_data(self, symbols: List[str]) -> Dict[str, MarketData]
    async def collect_historical_data(self, symbol: str, period: str) -> List[MarketData]
    async def get_health_status(self) -> Dict[str, HealthStatus]
    async def force_refresh(self, symbol: str) -> MarketData
```

**Configuração:**
```yaml
collector_manager:
  load_balancing:
    strategy: "health_weighted"  # round_robin, weighted, health_weighted
    health_check_interval: 30s
  
  failover:
    max_retries: 3
    retry_delay: 5s
    circuit_breaker_threshold: 5
  
  sources:
    yahoo_finance:
      weight: 30
      priority: 1
      rate_limit: 100/minute
    
    web_scraping:
      weight: 25
      priority: 2
      rate_limit: 60/minute
    
    websocket:
      weight: 35
      priority: 1
      rate_limit: unlimited
    
    public_data:
      weight: 10
      priority: 3
      rate_limit: 50/minute
```

### 2.2 Intelligent Cache

**Arquitetura de Cache:**
```mermaid
graph LR
    subgraph "Cache Hierarchy"
        L1["L1: Memory Cache<br/>TTL: 5min<br/>Size: 1000 items"]
        L2["L2: Redis Cache<br/>TTL: 1hour<br/>Size: 100k items"]
        L3["L3: Disk Cache<br/>TTL: 24hours<br/>Size: 1M items"]
        L4["L4: Database<br/>TTL: Permanent<br/>Size: Unlimited"]
    end
    
    APP["Application"] --> L1
    L1 --> L2
    L2 --> L3
    L3 --> L4
```

**Estratégias de Cache:**

1. **Cache por Volatilidade:**
   - Ativos de alta volatilidade: TTL menor (30s)
   - Ativos estáveis: TTL maior (5min)
   - Dados históricos: TTL longo (1h)

2. **Cache por Horário:**
   - Horário de mercado: TTL reduzido
   - Pré/pós mercado: TTL aumentado
   - Finais de semana: TTL máximo

3. **Cache por Popularidade:**
   - Top 100 ativos: Cache permanente em L1
   - Ativos médios: Cache em L2
   - Ativos raros: Cache apenas em L3/L4

### 2.3 Web Scraping Collector

**Arquitetura Anti-Detecção:**
```python
class AntiDetectionSystem:
    def __init__(self):
        self.proxy_rotator = ProxyRotator()
        self.user_agent_rotator = UserAgentRotator()
        self.session_manager = SessionManager()
        self.captcha_solver = CaptchaSolver()
        
    async def get_session(self, domain: str) -> aiohttp.ClientSession:
        # Rotacionar proxy baseado no domínio
        proxy = await self.proxy_rotator.get_proxy(domain)
        
        # Selecionar user agent realístico
        user_agent = self.user_agent_rotator.get_realistic_ua()
        
        # Configurar headers para parecer navegador real
        headers = self.generate_realistic_headers(user_agent)
        
        # Aplicar delays humanos
        await self.apply_human_delay()
        
        return self.session_manager.get_session(proxy, headers)
```

**Fontes de Scraping:**

| Fonte | Dados Disponíveis | Rate Limit | Complexidade |
|-------|------------------|------------|-------------|
| Yahoo Finance | Preços, volume, indicadores | 60 req/min | Média |
| Google Finance | Preços, fundamentals | 30 req/min | Baixa |
| MarketWatch | Notícias, análises | 40 req/min | Alta |
| Investing.com | Dados globais | 20 req/min | Alta |
| TradingView | Indicadores técnicos | 10 req/min | Muito Alta |

### 2.4 WebSocket Collector

**Conexões Suportadas:**

```python
class WebSocketCollector:
    def __init__(self):
        self.connections = {
            'binance': BinanceWebSocket(),
            'coinbase': CoinbaseWebSocket(),
            'iex': IEXWebSocket(),
            'polygon': PolygonWebSocket()
        }
        
    async def start_all_connections(self):
        tasks = []
        for name, ws in self.connections.items():
            task = asyncio.create_task(self.maintain_connection(name, ws))
            tasks.append(task)
        
        await asyncio.gather(*tasks)
    
    async def maintain_connection(self, name: str, websocket):
        while True:
            try:
                await websocket.connect()
                await websocket.listen()
            except Exception as e:
                logger.error(f"WebSocket {name} error: {e}")
                await self.handle_reconnection(name)
```

**Configuração de Reconexão:**
```yaml
websocket_config:
  binance:
    url: "wss://stream.binance.com:9443/ws"
    reconnect_delay: [1, 2, 4, 8, 16, 32]  # Backoff exponencial
    max_reconnect_attempts: 10
    ping_interval: 30s
    
  coinbase:
    url: "wss://ws-feed.pro.coinbase.com"
    reconnect_delay: [2, 4, 8, 16, 32]
    max_reconnect_attempts: 5
    ping_interval: 20s
```

### 2.5 Circuit Breaker System

**Estados e Transições:**
```mermaid
stateDiagram-v2
    [*] --> CLOSED
    CLOSED --> OPEN : failures >= threshold
    OPEN --> HALF_OPEN : timeout elapsed
    HALF_OPEN --> CLOSED : success >= threshold
    HALF_OPEN --> OPEN : any failure
    
    CLOSED : Normal Operation
    OPEN : Blocking Requests
    HALF_OPEN : Testing Recovery
```

**Configuração por Fonte:**
```yaml
circuit_breakers:
  yahoo_finance:
    failure_threshold: 5
    success_threshold: 3
    timeout: 60s
    half_open_max_calls: 3
    
  web_scraping:
    failure_threshold: 3  # Mais sensível
    success_threshold: 5  # Mais conservador
    timeout: 120s
    half_open_max_calls: 2
    
  websocket:
    failure_threshold: 10  # Menos sensível
    success_threshold: 2
    timeout: 30s
    half_open_max_calls: 5
```

## 3. Padrões de Implementação

### 3.1 Padrão de Coleta de Dados

```python
class DataCollectionPattern:
    """
    Padrão padrão para implementação de coletores.
    """
    
    async def collect(self, symbol: str, data_type: str) -> MarketData:
        # 1. Verificar cache primeiro
        cached_data = await self.cache.get(f"{symbol}:{data_type}")
        if cached_data and not self.is_stale(cached_data):
            return cached_data
        
        # 2. Aplicar rate limiting
        await self.rate_limiter.acquire()
        
        # 3. Usar circuit breaker
        async with self.circuit_breaker:
            # 4. Coletar dados
            raw_data = await self.fetch_data(symbol, data_type)
            
            # 5. Validar e normalizar
            validated_data = await self.validate_data(raw_data)
            normalized_data = await self.normalize_data(validated_data)
            
            # 6. Armazenar em cache
            await self.cache.set(f"{symbol}:{data_type}", normalized_data)
            
            # 7. Registrar métricas
            await self.metrics.record_success(self.name, symbol)
            
            return normalized_data
    
    async def fetch_data(self, symbol: str, data_type: str) -> dict:
        """Implementação específica de cada coletor."""
        raise NotImplementedError
    
    async def validate_data(self, data: dict) -> dict:
        """Validação de dados coletados."""
        required_fields = ['symbol', 'price', 'timestamp']
        for field in required_fields:
            if field not in data:
                raise ValidationError(f"Missing field: {field}")
        return data
    
    async def normalize_data(self, data: dict) -> MarketData:
        """Normalização para formato padrão."""
        return MarketData(
            symbol=data['symbol'],
            price=float(data['price']),
            volume=data.get('volume', 0),
            timestamp=datetime.fromisoformat(data['timestamp']),
            source=self.name
        )
```

### 3.2 Padrão de Error Handling

```python
class ErrorHandlingPattern:
    """
    Padrão para tratamento de erros em coletores.
    """
    
    async def safe_collect(self, symbol: str) -> Optional[MarketData]:
        try:
            return await self.collect(symbol)
        except RateLimitError as e:
            logger.warning(f"Rate limit hit for {symbol}: {e}")
            await self.handle_rate_limit(symbol)
            return None
        except ValidationError as e:
            logger.error(f"Data validation failed for {symbol}: {e}")
            await self.metrics.record_validation_error(symbol)
            return None
        except NetworkError as e:
            logger.error(f"Network error for {symbol}: {e}")
            await self.handle_network_error(symbol)
            return None
        except Exception as e:
            logger.exception(f"Unexpected error for {symbol}: {e}")
            await self.metrics.record_unexpected_error(symbol)
            return None
    
    async def handle_rate_limit(self, symbol: str):
        """Estratégia para lidar com rate limiting."""
        # Aumentar delay para próximas requisições
        self.rate_limiter.increase_delay()
        
        # Tentar fonte alternativa
        alternative_data = await self.try_alternative_source(symbol)
        if alternative_data:
            await self.cache.set(symbol, alternative_data)
    
    async def handle_network_error(self, symbol: str):
        """Estratégia para erros de rede."""
        # Marcar fonte como instável
        await self.health_monitor.report_failure(self.name)
        
        # Tentar com proxy diferente (se aplicável)
        if hasattr(self, 'proxy_rotator'):
            await self.proxy_rotator.rotate()
```

### 3.3 Padrão de Observabilidade

```python
class ObservabilityPattern:
    """
    Padrão para instrumentação e observabilidade.
    """
    
    def __init__(self):
        self.metrics = MetricsCollector()
        self.tracer = get_tracer(__name__)
        
    async def instrumented_collect(self, symbol: str) -> MarketData:
        # Criar span para tracing
        with self.tracer.start_as_current_span("collect_data") as span:
            span.set_attribute("symbol", symbol)
            span.set_attribute("source", self.name)
            
            start_time = time.time()
            
            try:
                # Executar coleta
                data = await self.collect(symbol)
                
                # Registrar sucesso
                duration = time.time() - start_time
                await self.metrics.record_success(
                    source=self.name,
                    symbol=symbol,
                    duration=duration
                )
                
                span.set_attribute("success", True)
                span.set_attribute("duration", duration)
                
                return data
                
            except Exception as e:
                # Registrar falha
                duration = time.time() - start_time
                await self.metrics.record_failure(
                    source=self.name,
                    symbol=symbol,
                    error=str(e),
                    duration=duration
                )
                
                span.set_attribute("success", False)
                span.set_attribute("error", str(e))
                span.record_exception(e)
                
                raise
```

## 4. Configuração de Infraestrutura

### 4.1 Docker Compose para Desenvolvimento

```yaml
version: '3.8'

services:
  # Aplicação principal
  collector-manager:
    build: .
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=postgresql://postgres:password@timescaledb:5432/nacao_trader
      - LOG_LEVEL=INFO
    depends_on:
      - redis
      - timescaledb
    volumes:
      - ./cache:/app/cache
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
  
  # Cache Redis
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes --maxmemory 1gb --maxmemory-policy allkeys-lru
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3
  
  # Banco de dados TimescaleDB
  timescaledb:
    image: timescale/timescaledb:latest-pg14
    ports:
      - "5432:5432"
    environment:
      - POSTGRES_DB=nacao_trader
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - timescaledb_data:/var/lib/postgresql/data
      - ./sql/init.sql:/docker-entrypoint-initdb.d/init.sql
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 30s
      timeout: 10s
      retries: 3
  
  # Monitoramento
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--web.enable-lifecycle'
    restart: unless-stopped
  
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./monitoring/grafana/datasources:/etc/grafana/provisioning/datasources
    restart: unless-stopped
    depends_on:
      - prometheus
  
  # Nginx para load balancing
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - collector-manager
    restart: unless-stopped

volumes:
  redis_data:
  timescaledb_data:
  prometheus_data:
  grafana_data:

networks:
  default:
    driver: bridge
```

### 4.2 Configuração Kubernetes para Produção

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: collector-manager
  labels:
    app: collector-manager
spec:
  replicas: 3
  selector:
    matchLabels:
      app: collector-manager
  template:
    metadata:
      labels:
        app: collector-manager
    spec:
      containers:
      - name: collector-manager
        image: nacao-trader/collector-manager:latest
        ports:
        - containerPort: 8000
        env:
        - name: REDIS_URL
          value: "redis://redis-service:6379"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: database-url
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: collector-manager-service
spec:
  selector:
    app: collector-manager
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

### 4.3 Configuração de Monitoramento

```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

scrape_configs:
  - job_name: 'collector-manager'
    static_configs:
      - targets: ['collector-manager:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s
    scrape_timeout: 10s
    
  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']
    
  - job_name: 'timescaledb'
    static_configs:
      - targets: ['timescaledb:5432']

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

```yaml
# monitoring/alert_rules.yml
groups:
- name: collector_alerts
  rules:
  - alert: HighErrorRate
    expr: rate(data_collection_errors_total[5m]) > 0.1
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "High error rate in data collection"
      description: "Error rate is {{ $value }} errors per second"
  
  - alert: SlowResponseTime
    expr: histogram_quantile(0.95, rate(data_collection_duration_seconds_bucket[5m])) > 5
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Slow response time in data collection"
      description: "95th percentile response time is {{ $value }} seconds"
  
  - alert: CollectorDown
    expr: up{job="collector-manager"} == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Collector manager is down"
      description: "Collector manager has been down for more than 1 minute"
```

## 5. Testes e Validação

### 5.1 Estratégia de Testes

```python
# tests/test_integration.py
import pytest
import asyncio
from unittest.mock import patch, AsyncMock

class TestDataCollectionIntegration:
    """
    Testes de integração para o sistema de coleta.
    """
    
    @pytest.fixture
    async def collector_manager(self):
        """Fixture para CollectorManager configurado para testes."""
        manager = CollectorManager()
        await manager.initialize()
        yield manager
        await manager.cleanup()
    
    @pytest.mark.asyncio
    async def test_multi_source_collection(self, collector_manager):
        """Testa coleta de dados de múltiplas fontes."""
        symbols = ['AAPL', 'MSFT', 'GOOGL']
        
        # Coletar dados de todas as fontes
        results = await collector_manager.collect_bulk_data(symbols)
        
        # Verificar que todos os símbolos foram coletados
        assert len(results) == len(symbols)
        
        # Verificar que pelo menos 2 fontes foram usadas
        sources_used = set(data.source for data in results.values())
        assert len(sources_used) >= 2
    
    @pytest.mark.asyncio
    async def test_failover_mechanism(self, collector_manager):
        """Testa mecanismo de failover entre fontes."""
        # Simular falha na fonte primária
        with patch.object(collector_manager.collectors['yahoo_finance'], 'collect') as mock_yahoo:
            mock_yahoo.side_effect = Exception("API Error")
            
            # Deve usar fonte secundária
            data = await collector_manager.collect_data('AAPL')
            
            assert data is not None
            assert data.source != 'yahoo_finance'
    
    @pytest.mark.asyncio
    async def test_cache_performance(self, collector_manager):
        """Testa performance do sistema de cache."""
        symbol = 'AAPL'
        
        # Primeira coleta (cache miss)
        start_time = time.time()
        data1 = await collector_manager.collect_data(symbol)
        first_duration = time.time() - start_time
        
        # Segunda coleta (cache hit)
        start_time = time.time()
        data2 = await collector_manager.collect_data(symbol)
        second_duration = time.time() - start_time
        
        # Cache hit deve ser significativamente mais rápido
        assert second_duration < first_duration * 0.1
        assert data1.price == data2.price
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_behavior(self, collector_manager):
        """Testa comportamento do circuit breaker."""
        collector = collector_manager.collectors['yahoo_finance']
        
        # Simular falhas consecutivas
        with patch.object(collector, 'fetch_data') as mock_fetch:
            mock_fetch.side_effect = Exception("Simulated failure")
            
            # Tentar coletar dados até circuit breaker abrir
            for _ in range(6):  # Threshold é 5
                try:
                    await collector.collect('AAPL')
                except:
                    pass
            
            # Circuit breaker deve estar aberto
            assert collector.circuit_breaker.state == CircuitState.OPEN
            
            # Próxima tentativa deve falhar imediatamente
            with pytest.raises(CircuitBreakerOpenException):
                await collector.collect('AAPL')
```

### 5.2 Testes de Performance

```python
# tests/test_performance.py
import asyncio
import time
import pytest
from concurrent.futures import ThreadPoolExecutor

class TestPerformance:
    """
    Testes de performance e carga.
    """
    
    @pytest.mark.asyncio
    async def test_concurrent_collection_performance(self):
        """Testa performance com coleta concorrente."""
        symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA'] * 20  # 100 símbolos
        
        collector_manager = CollectorManager()
        
        start_time = time.time()
        
        # Executar coletas concorrentes
        tasks = [collector_manager.collect_data(symbol) for symbol in symbols]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Verificar performance
        successful_results = [r for r in results if not isinstance(r, Exception)]
        success_rate = len(successful_results) / len(results)
        
        # Assertions
        assert duration < 30  # Deve completar em menos de 30 segundos
        assert success_rate >= 0.9  # Pelo menos 90% de sucesso
        
        # Calcular throughput
        throughput = len(successful_results) / duration
        assert throughput >= 10  # Pelo menos 10 req/s
    
    @pytest.mark.asyncio
    async def test_cache_hit_performance(self):
        """Testa performance de cache hits."""
        cache = IntelligentCache()
        
        # Pré-popular cache
        test_data = {'symbol': 'AAPL', 'price': 150.0, 'timestamp': time.time()}
        await cache.set('AAPL', test_data)
        
        # Testar velocidade de acesso
        iterations = 1000
        start_time = time.time()
        
        for _ in range(iterations):
            data = await cache.get('AAPL')
            assert data is not None
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Deve acessar 1000 itens em menos de 100ms
        assert duration < 0.1
        
        # Calcular ops por segundo
        ops_per_second = iterations / duration
        assert ops_per_second >= 10000  # Pelo menos 10k ops/s
    
    @pytest.mark.asyncio
    async def test_memory_usage(self):
        """Testa uso de memória sob carga."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        collector_manager = CollectorManager()
        
        # Simular carga pesada
        symbols = ['SYMBOL_' + str(i) for i in range(1000)]
        
        for batch in [symbols[i:i+100] for i in range(0, len(symbols), 100)]:
            tasks = [collector_manager.collect_data(symbol) for symbol in batch]
            await asyncio.gather(*tasks, return_exceptions=True)
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Aumento de memória deve ser razoável (< 500MB)
        assert memory_increase < 500 * 1024 * 1024
```

## 6. Deployment e Operação

### 6.1 Checklist de Deploy

**Pré-Deploy:**
- [ ] Testes unitários passando (100%)
- [ ] Testes de integração passando (100%)
- [ ] Testes de performance dentro dos targets
- [ ] Code review aprovado
- [ ] Documentação atualizada
- [ ] Configurações de produção validadas
- [ ] Backup do banco de dados realizado
- [ ] Plano de rollback preparado

**Durante o Deploy:**
- [ ] Deploy em ambiente de staging
- [ ] Smoke tests em staging
- [ ] Deploy gradual em produção (5% → 25% → 50% → 100%)
- [ ] Monitoramento de métricas em tempo real
- [ ] Verificação de logs de erro
- [ ] Teste de funcionalidades críticas

**Pós-Deploy:**
- [ ] Verificação de todas as métricas
- [ ] Teste de alertas
- [ ] Documentação de deployment atualizada
- [ ] Comunicação para stakeholders
- [ ] Monitoramento estendido por 24h

### 6.2 Runbook Operacional

**Procedimentos de Emergência:**

1. **Sistema Completamente Indisponível:**
   ```bash
   # Verificar status dos serviços
   kubectl get pods -n nacao-trader
   
   # Verificar logs
   kubectl logs -f deployment/collector-manager -n nacao-trader
   
   # Rollback se necessário
   kubectl rollout undo deployment/collector-manager -n nacao-trader
   ```

2. **Alta Taxa de Erro:**
   ```bash
   # Verificar métricas no Grafana
   # URL: http://grafana.nacao-trader.com/d/collector-dashboard
   
   # Verificar circuit breakers
   curl http://collector-manager/health/circuit-breakers
   
   # Forçar reset de circuit breakers se necessário
   curl -X POST http://collector-manager/admin/reset-circuit-breakers
   ```

3. **Performance Degradada:**
   ```bash
   # Verificar uso de recursos
   kubectl top pods -n nacao-trader
   
   # Escalar horizontalmente se necessário
   kubectl scale deployment collector-manager --replicas=5 -n nacao-trader
   
   # Limpar cache se necessário
   redis-cli -h redis.nacao-trader.com FLUSHDB
   ```

**Monitoramento Contínuo:**

- **Métricas Críticas:**
  - Taxa de sucesso > 98%
  - Latência P95 < 500ms
  - Disponibilidade > 99.5%
  - Uso de CPU < 70%
  - Uso de memória < 80%

- **Alertas Configurados:**
  - Taxa de erro > 2% por 5 minutos
  - Latência P95 > 1s por 5 minutos
  - Serviço indisponível por 1 minuto
  - Uso de recursos > 90% por 10 minutos

## 7. Conclusão

Esta arquitetura de referência fornece um blueprint completo para implementar um sistema robusto e independente de coleta de dados financeiros. Os principais benefícios incluem:

**Benefícios Técnicos:**
- 🔄 **Redundância**: Múltiplas fontes com failover automático
- ⚡ **Performance**: Cache inteligente e otimizações
- 🛡️ **Resiliência**: Circuit breakers e recuperação automática
- 📊 **Observabilidade**: Monitoramento completo e alertas
- 🔧 **Manutenibilidade**: Código modular e bem documentado

**Benefícios de Negócio:**
- 💰 **Redução de custos**: Menos dependência de APIs pagas
- 📈 **Maior disponibilidade**: Sistema mais confiável
- 🚀 **Escalabilidade**: Suporte a crescimento futuro
- 🎯 **Flexibilidade**: Fácil adição de novas fontes

**Próximos Passos:**
1. Revisar e aprovar a arquitetura proposta
2. Iniciar implementação seguindo o roadmap
3. Configurar ambiente de desenvolvimento
4. Implementar componentes core (cache, circuit breakers)
5. Adicionar coletores específicos gradualmente
6. Realizar testes extensivos antes do deploy
7. Executar deploy gradual em produção

Esta arquitetura posicionará o Nação Trader como uma plataforma de trading mais robusta, independente e escalável, capaz de fornecer dados financeiros confiáveis mesmo em cenários de instabilidade de provedores externos.