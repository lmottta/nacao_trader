# Documentação Técnica - Fase 2 do Nação Trader

## Visão Geral

A Fase 2 do projeto Nação Trader implementa um sistema de orquestração integrado que combina múltiplas fontes de dados, sistemas de resiliência avançados e monitoramento em tempo real. Esta fase expande significativamente as capacidades do sistema original, adicionando:

- **Web Scraping Inteligente** com rotação de proxies e user agents
- **Coletores WebSocket** para dados em tempo real
- **Integração com Dados Públicos** (FRED, Banco Central do Brasil)
- **Sistema de Validação Cruzada** entre múltiplas fontes
- **Sistema de Fallback Automático** com estratégias adaptativas
- **Rate Limiting Inteligente** baseado em performance
- **Dashboard de Monitoramento** em tempo real

## Arquitetura do Sistema

### Componentes Principais

```
┌─────────────────────────────────────────────────────────────┐
│                    Sistema Integrado                        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ CollectorManager│  │ FallbackSystem  │  │ Dashboard    │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ WebScraping     │  │ WebSocket       │  │ PublicData   │ │
│  │ Collectors      │  │ Collectors      │  │ Collectors   │ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐ │
│  │ IntelligentCache│  │ MetricsCollector│  │ CrossValidator│ │
│  └─────────────────┘  └─────────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Módulos Implementados

### 1. Sistema Principal Integrado (`main_integrated.py`)

**Localização**: `src/main_integrated.py`

**Responsabilidades**:
- Coordenação de todos os componentes da Fase 2
- Orquestração da coleta de dados abrangente
- Gerenciamento do ciclo de vida do sistema
- Interface unificada para operações do sistema

**Classes Principais**:
- `IntegratedSystem`: Classe principal que coordena todos os componentes

**Funcionalidades**:
```python
# Inicialização do sistema
system = get_integrated_system()
await system.initialize()

# Coleta abrangente de dados
results = await system.collect_comprehensive_data(["AAPL", "MSFT"])

# Coleta de indicadores econômicos
indicators = await system.collect_economic_indicators()

# Coleta contínua
await system.start_continuous_collection(interval_minutes=60)

# Status do sistema
status = await system.get_system_status()
```

### 2. Gerenciador de Coletores Avançado (`collector_manager.py`)

**Localização**: `src/collectors/collector_manager.py`

**Melhorias da Fase 2**:
- Integração com sistema de fallback
- Rate limiting inteligente adaptativo
- Suporte para novos tipos de coletores
- Validação cruzada automática
- Rotação inteligente de fontes

**Novos Coletores Suportados**:
- `WEB_SCRAPING`: Coleta via web scraping
- `BINANCE_WEBSOCKET`: WebSocket da Binance
- `FRED`: Federal Reserve Economic Data
- `BANCO_CENTRAL`: Banco Central do Brasil

**Rate Limiting Inteligente**:
```python
# Atualização automática baseada em performance
await collector_manager.update_rate_limits(
    source_name="yahoo_finance",
    success_rate=0.95,
    avg_response_time=0.5,
    error_rate=0.05
)
```

### 3. Sistema de Fallback Automático (`fallback_system.py`)

**Localização**: `src/resilience/fallback_system.py`

**Estratégias de Fallback**:
- `ROUND_ROBIN`: Rotação circular entre fontes
- `PRIORITY_BASED`: Baseado em prioridade configurada
- `PERFORMANCE_BASED`: Baseado em métricas de performance
- `HYBRID`: Combinação de estratégias

**Gatilhos de Fallback**:
- `ERROR_RATE`: Taxa de erro elevada
- `TIMEOUT`: Timeout nas requisições
- `CIRCUIT_BREAKER`: Circuit breaker aberto
- `QUALITY_DEGRADATION`: Degradação da qualidade dos dados

**Uso**:
```python
# Configuração do fallback
fallback_config = FallbackConfig(
    strategy=FallbackStrategy.HYBRID,
    max_retries=3,
    timeout_seconds=30,
    error_threshold=0.1
)

# Execução com fallback
result = await fallback_system.execute_with_fallback(
    operation=collect_data_function,
    operation_args={"symbol": "AAPL"},
    config=fallback_config
)
```

### 4. Rate Limiting Inteligente (`intelligent_rate_limiter.py`)

**Localização**: `src/collectors/intelligent_rate_limiter.py`

**Estratégias Implementadas**:
- `FIXED`: Rate limit fixo
- `ADAPTIVE`: Adaptativo baseado em performance
- `AIMD`: Additive Increase Multiplicative Decrease
- `TOKEN_BUCKET`: Algoritmo token bucket
- `SLIDING_WINDOW`: Janela deslizante

**Características**:
- Adaptação automática baseada em métricas
- Integração com circuit breakers
- Histórico de performance
- Ajuste dinâmico de limites

### 5. Coletores Web Scraping (`web_scraping/`)

**Localização**: `src/web_scraping/`

**Componentes**:
- `WebScrapingCollector`: Coletor principal
- `ProxyRotator`: Rotação de proxies
- `UserAgentRotator`: Rotação de user agents
- `ScrapingResult`: Estrutura de resultados

**Funcionalidades**:
- Rotação automática de proxies
- Rotação de user agents
- Rate limiting por domínio
- Tratamento de erros robusto
- Cache de resultados

### 6. Coletores WebSocket (`websocket/`)

**Localização**: `src/websocket/`

**Implementações**:
- `WebSocketCollector`: Classe base
- `BinanceWebSocketCollector`: WebSocket da Binance
- `AlphaVantageWebSocketCollector`: WebSocket da Alpha Vantage

**Características**:
- Reconexão automática
- Heartbeat para manter conexão
- Buffer de mensagens
- Tratamento de desconexões

### 7. Coletores de Dados Públicos (`public_data/`)

**Localização**: `src/public_data/`

**Implementações**:
- `FREDCollector`: Federal Reserve Economic Data
- `WorldBankCollector`: Banco Mundial
- `BancoCentralCollector`: Banco Central do Brasil

**Indicadores Suportados**:

**FRED**:
- PIB (GDP)
- Taxa de desemprego (UNRATE)
- Taxa de juros federal (FEDFUNDS)
- Índice de preços (CPIAUCSL)
- Títulos do tesouro (DGS10)

**Banco Central**:
- Taxa Selic (432)
- IPCA (433)
- Taxa de câmbio USD/BRL (1)

### 8. Sistema de Validação Cruzada (`validation/`)

**Localização**: `src/validation/cross_validator.py`

**Funcionalidades**:
- Comparação entre múltiplas fontes
- Detecção de outliers
- Cálculo de confiabilidade
- Métricas de qualidade
- Alertas de inconsistência

### 9. Dashboard de Monitoramento (`dashboard/`)

**Localização**: `src/dashboard/monitoring_dashboard.py`

**Características**:
- Interface web responsiva
- Atualizações em tempo real via WebSocket
- Métricas de sistema e performance
- Status de coletores
- Controle de coletores (habilitar/desabilitar)

**Endpoints da API**:
- `GET /api/status`: Status completo do sistema
- `GET /api/collectors`: Status dos coletores
- `GET /api/metrics`: Métricas de performance
- `GET /api/cache`: Status do cache
- `GET /api/fallback`: Status do sistema de fallback
- `POST /api/collectors/{type}/enable`: Habilitar coletor
- `POST /api/collectors/{type}/disable`: Desabilitar coletor
- `WebSocket /ws`: Atualizações em tempo real

## Configuração e Uso

### Inicialização do Sistema

```python
from src.main_integrated import get_integrated_system

# Obter instância do sistema
system = get_integrated_system()

# Inicializar todos os componentes
await system.initialize()

# Verificar status
status = await system.get_system_status()
print(f"Sistema inicializado: {status['summary']}")
```

### Execução via Linha de Comando

```bash
# Mostrar status do sistema
python -m src.main_integrated status

# Executar coleta única
python -m src.main_integrated collect

# Coletar indicadores econômicos
python -m src.main_integrated economic

# Executar coleta contínua (60 minutos de intervalo)
python -m src.main_integrated continuous 60
```

### Iniciar Dashboard

```bash
# Iniciar dashboard na porta 8080
python -m src.dashboard.monitoring_dashboard

# Iniciar em porta específica
python -m src.dashboard.monitoring_dashboard 0.0.0.0 8090
```

### Configuração de Coletores

```python
# Habilitar coletores específicos
await collector_manager.enable_collector(CollectorType.WEB_SCRAPING)
await collector_manager.enable_collector(CollectorType.BINANCE_WEBSOCKET)
await collector_manager.enable_collector(CollectorType.FRED)

# Configurar validação cruzada
collector_manager.enable_validation()

# Configurar sistema de fallback
collector_manager.enable_fallback()
```

## Métricas e Monitoramento

### Métricas do Sistema

- **CPU Usage**: Uso de CPU em percentual
- **Memory Usage**: Uso de memória em percentual
- **Disk Usage**: Uso de disco
- **Network I/O**: Entrada/saída de rede

### Métricas de Coletores

- **Success Rate**: Taxa de sucesso das requisições
- **Average Response Time**: Tempo médio de resposta
- **Error Rate**: Taxa de erro
- **Requests per Minute**: Requisições por minuto
- **Circuit Breaker Status**: Status dos circuit breakers

### Métricas de Cache

- **Hit Rate**: Taxa de acerto do cache
- **Miss Rate**: Taxa de erro do cache
- **Total Entries**: Total de entradas
- **Memory Usage**: Uso de memória do cache
- **Evictions**: Número de evicções

### Métricas de Fallback

- **Total Executions**: Total de execuções
- **Fallback Triggers**: Gatilhos de fallback ativados
- **Success Rate**: Taxa de sucesso do fallback
- **Active Sources**: Fontes ativas

## Testes

### Estrutura de Testes

```
tests/
├── test_integration_phase2.py     # Testes de integração
├── test_collector_manager.py      # Testes do gerenciador
├── test_fallback_system.py        # Testes do fallback
├── test_web_scraping.py           # Testes de web scraping
├── test_websocket_collectors.py   # Testes de WebSocket
├── test_public_data_collectors.py # Testes de dados públicos
└── test_dashboard.py              # Testes do dashboard
```

### Executar Testes

```bash
# Executar todos os testes
pytest tests/

# Executar testes de integração
pytest tests/test_integration_phase2.py

# Executar testes com cobertura
pytest --cov=src tests/

# Executar teste básico
python tests/test_integration_phase2.py
```

### Tipos de Testes

1. **Testes Unitários**: Testam componentes individuais
2. **Testes de Integração**: Testam interação entre componentes
3. **Testes End-to-End**: Testam fluxos completos do sistema
4. **Testes de Performance**: Validam performance e escalabilidade
5. **Testes de Resiliência**: Testam recuperação de falhas

## Configurações

### Variáveis de Ambiente

```bash
# Configurações gerais
LOG_LEVEL=INFO
DATA_COLLECTION_INTERVAL=3600

# APIs externas
FINNHUB_API_KEY=your_finnhub_key
FRED_API_KEY=your_fred_key
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key

# Cache
REDIS_URL=redis://localhost:6379
CACHE_TTL=300

# Rate Limiting
DEFAULT_RATE_LIMIT=60
RATE_LIMIT_WINDOW=60

# Fallback
FALLBACK_ENABLED=true
FALLBACK_MAX_RETRIES=3
FALLBACK_TIMEOUT=30

# Dashboard
DASHBOARD_HOST=0.0.0.0
DASHBOARD_PORT=8080
```

### Configuração de Proxies

```python
# Configuração de proxies para web scraping
PROXY_LIST = [
    "http://proxy1:port",
    "http://proxy2:port",
    "socks5://proxy3:port"
]

# Rotação de user agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
]
```

## Troubleshooting

### Problemas Comuns

1. **Erro de Inicialização**
   - Verificar dependências instaladas
   - Verificar configurações de ambiente
   - Verificar conectividade de rede

2. **Rate Limiting**
   - Ajustar configurações de rate limit
   - Verificar quotas das APIs
   - Implementar delays adicionais

3. **Falhas de Conexão**
   - Verificar proxies configurados
   - Verificar firewall/antivírus
   - Verificar status das APIs externas

4. **Performance**
   - Monitorar uso de CPU/memória
   - Ajustar configurações de cache
   - Otimizar intervalos de coleta

### Logs

```bash
# Localização dos logs
logs/
├── integrated_system.log    # Sistema principal
├── collectors.log           # Coletores
├── fallback_system.log      # Sistema de fallback
├── web_scraping.log         # Web scraping
└── dashboard.log            # Dashboard
```

### Comandos de Diagnóstico

```bash
# Verificar status do sistema
python -m src.main_integrated status

# Testar conectividade
python -c "from src.main_integrated import get_integrated_system; import asyncio; asyncio.run(get_integrated_system().get_system_status())"

# Verificar cache
python -c "from src.cache.intelligent_cache import get_cache; import asyncio; print(asyncio.run(get_cache()).get_stats())"

# Verificar métricas
python -c "from src.monitoring.metrics_collector import get_metrics_collector; print(get_metrics_collector().get_system_metrics())"
```

## Roadmap Futuro

### Fase 3 (Planejada)

1. **Machine Learning Integrado**
   - Modelos de predição em tempo real
   - Análise de sentimento avançada
   - Detecção de anomalias

2. **Escalabilidade**
   - Distribuição em múltiplos nós
   - Load balancing automático
   - Sharding de dados

3. **Segurança Avançada**
   - Criptografia end-to-end
   - Autenticação multi-fator
   - Auditoria completa

4. **Interface Avançada**
   - Dashboard interativo
   - Alertas personalizáveis
   - Relatórios automatizados

## Conclusão

A Fase 2 do Nação Trader representa um avanço significativo na capacidade de coleta, processamento e monitoramento de dados financeiros. O sistema agora oferece:

- **Resiliência**: Múltiplas camadas de fallback e recuperação
- **Escalabilidade**: Arquitetura modular e extensível
- **Observabilidade**: Monitoramento completo e métricas detalhadas
- **Flexibilidade**: Suporte para múltiplas fontes e tipos de dados
- **Confiabilidade**: Validação cruzada e controle de qualidade

O sistema está preparado para suportar operações de trading em larga escala, fornecendo dados confiáveis e atualizados para tomada de decisões financeiras.