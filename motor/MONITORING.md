# Sistema de Monitoramento - Nação Trader

Este documento descreve como configurar e usar o sistema de monitoramento do Nação Trader, implementado na Fase 1 do roadmap de melhorias.

## 📋 Visão Geral

O sistema de monitoramento inclui:

- **Prometheus**: Coleta e armazenamento de métricas
- **Grafana**: Visualização de métricas e dashboards
- **Alertmanager**: Gerenciamento de alertas
- **Redis**: Cache distribuído
- **Node Exporter**: Métricas do sistema
- **Blackbox Exporter**: Monitoramento de endpoints
- **cAdvisor**: Métricas de containers

## 🚀 Configuração Rápida

### Pré-requisitos

- Docker e Docker Compose instalados
- Python 3.8+ (para o script de setup)
- Portas disponíveis: 3000, 9090, 9093, 9091, 6379, 9100, 9115, 8080

### Instalação Automática

```bash
# Navegar para o diretório do motor
cd motor

# Executar script de configuração
python scripts/setup_monitoring.py
```

### Instalação Manual

```bash
# Criar diretórios de dados
mkdir -p data/{prometheus,grafana,alertmanager,redis} logs

# Iniciar serviços
docker compose -f docker-compose.monitoring.yml up -d

# Verificar status
docker compose -f docker-compose.monitoring.yml ps
```

## 🔧 Configuração

### Variáveis de Ambiente

Crie um arquivo `.env` no diretório raiz:

```env
# Configurações do Grafana
GF_SECURITY_ADMIN_PASSWORD=admin123
GF_INSTALL_PLUGINS=grafana-piechart-panel

# Configurações do Alertmanager
ALERT_SMTP_HOST=smtp.gmail.com
ALERT_SMTP_PORT=587
ALERT_SMTP_USER=seu-email@gmail.com
ALERT_SMTP_PASS=sua-senha-app
ALERT_SLACK_WEBHOOK=https://hooks.slack.com/services/...

# Configurações do Redis
REDIS_PASSWORD=redis123
```

### Configuração de Alertas por Email

Edite `config/alertmanager.yml`:

```yaml
global:
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_from: 'seu-email@gmail.com'
  smtp_auth_username: 'seu-email@gmail.com'
  smtp_auth_password: 'sua-senha-app'
```

### Configuração de Alertas no Slack

Edite `config/alertmanager.yml`:

```yaml
receivers:
  - name: 'slack-critical'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/...'
        channel: '#alerts'
        title: 'Alerta Crítico - Nação Trader'
```

## 📊 Dashboards

### Grafana

**URL**: http://localhost:3000
**Usuário**: admin
**Senha**: admin123

#### Dashboards Disponíveis:

1. **Nação Trader - Overview**
   - Métricas gerais do sistema
   - Performance das APIs
   - Status dos coletores

2. **System Metrics**
   - CPU, Memória, Disco
   - Rede e I/O

3. **API Performance**
   - Tempo de resposta
   - Taxa de erro
   - Rate limiting

4. **Cache Performance**
   - Hit rate
   - Operações por segundo
   - Tamanho do cache

5. **Circuit Breakers**
   - Estados dos circuit breakers
   - Taxa de falhas
   - Tempo de recuperação

### Prometheus

**URL**: http://localhost:9090

#### Métricas Principais:

```promql
# Taxa de chamadas de API
rate(api_calls_total[5m])

# Tempo de resposta médio
rate(api_response_time_sum[5m]) / rate(api_response_time_count[5m])

# Taxa de acerto do cache
rate(cache_hits_total[5m]) / rate(cache_operations_total[5m])

# Circuit breakers abertos
circuit_breaker_state{state="open"}

# Uso de CPU
100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
```

## 🚨 Alertas

### Alertmanager

**URL**: http://localhost:9093

#### Categorias de Alertas:

1. **Sistema**
   - Alto uso de CPU (>80%)
   - Alto uso de memória (>85%)
   - Pouco espaço em disco (<10%)

2. **APIs**
   - Alta taxa de erro (>5%)
   - Tempo de resposta alto (>2s)
   - API indisponível

3. **Cache**
   - Baixa taxa de acerto (<70%)
   - Cache muito grande (>1GB)

4. **Circuit Breakers**
   - Circuit breaker aberto
   - Alta taxa de falhas (>10%)

5. **Coleta de Dados**
   - Falha na coleta
   - Dados desatualizados

### Configuração de Notificações

#### Email

```yaml
receivers:
  - name: 'email-alerts'
    email_configs:
      - to: 'admin@empresa.com'
        subject: '[ALERTA] {{ .GroupLabels.alertname }}'
        body: |
          {{ range .Alerts }}
          Alerta: {{ .Annotations.summary }}
          Descrição: {{ .Annotations.description }}
          Severidade: {{ .Labels.severity }}
          {{ end }}
```

#### Slack

```yaml
receivers:
  - name: 'slack-alerts'
    slack_configs:
      - api_url: 'https://hooks.slack.com/services/...'
        channel: '#monitoring'
        title: '{{ .GroupLabels.alertname }}'
        text: |
          {{ range .Alerts }}
          *{{ .Annotations.summary }}*
          {{ .Annotations.description }}
          Severidade: {{ .Labels.severity }}
          {{ end }}
```

## 🔍 Troubleshooting

### Problemas Comuns

#### Serviços não iniciam

```bash
# Verificar logs
docker compose -f docker-compose.monitoring.yml logs

# Verificar portas em uso
netstat -tulpn | grep -E ':(3000|9090|9093|6379)'

# Limpar e reiniciar
docker compose -f docker-compose.monitoring.yml down -v
docker compose -f docker-compose.monitoring.yml up -d
```

#### Prometheus não coleta métricas

1. Verificar targets no Prometheus: http://localhost:9090/targets
2. Verificar se a aplicação está expondo métricas: http://localhost:8000/metrics
3. Verificar configuração de rede do Docker

#### Grafana não mostra dados

1. Verificar datasource: Grafana → Configuration → Data Sources
2. Testar conexão com Prometheus
3. Verificar queries nos dashboards

#### Alertas não funcionam

1. Verificar configuração do Alertmanager
2. Testar regras de alerta no Prometheus
3. Verificar logs do Alertmanager

### Comandos Úteis

```bash
# Ver status dos serviços
docker compose -f docker-compose.monitoring.yml ps

# Ver logs em tempo real
docker compose -f docker-compose.monitoring.yml logs -f

# Reiniciar serviço específico
docker compose -f docker-compose.monitoring.yml restart prometheus

# Parar todos os serviços
docker compose -f docker-compose.monitoring.yml down

# Remover volumes (CUIDADO: apaga dados)
docker compose -f docker-compose.monitoring.yml down -v

# Verificar uso de recursos
docker stats
```

## 📈 Métricas Customizadas

### Adicionando Novas Métricas

```python
from motor.src.core.metrics import metrics_manager

# Contador
metrics_manager.increment_counter(
    'custom_operations_total',
    labels={'operation': 'data_processing'}
)

# Gauge
metrics_manager.set_gauge(
    'custom_queue_size',
    value=queue.size(),
    labels={'queue': 'processing'}
)

# Histograma
with metrics_manager.measure_time('custom_processing_duration'):
    # Sua operação aqui
    process_data()
```

### Configurando Alertas Customizados

Edite `config/alert_rules.yml`:

```yaml
groups:
  - name: custom_alerts
    rules:
      - alert: CustomHighLatency
        expr: custom_processing_duration > 5
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Processamento customizado lento"
          description: "Operação customizada levando mais de 5s"
```

## 🔒 Segurança

### Configurações Recomendadas

1. **Alterar senhas padrão**
2. **Configurar HTTPS** (produção)
3. **Restringir acesso por IP**
4. **Usar autenticação externa** (LDAP, OAuth)
5. **Configurar backup dos dados**

### Backup

```bash
# Backup dos dados do Prometheus
docker run --rm -v nacao_trader_prometheus_data:/data -v $(pwd):/backup alpine tar czf /backup/prometheus-backup.tar.gz /data

# Backup das configurações
tar czf monitoring-config-backup.tar.gz config/
```

## 📚 Recursos Adicionais

- [Documentação do Prometheus](https://prometheus.io/docs/)
- [Documentação do Grafana](https://grafana.com/docs/)
- [Guia de PromQL](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Templates de Dashboard](https://grafana.com/grafana/dashboards/)

## 🆘 Suporte

Para problemas ou dúvidas:

1. Verificar logs dos serviços
2. Consultar este documento
3. Verificar issues conhecidos no repositório
4. Contatar a equipe de desenvolvimento