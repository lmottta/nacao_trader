# Guia de Deployment - Fase 2: Sistema Avançado de Coleta

## Visão Geral

Este guia fornece instruções completas para deploy e configuração do Motor de Sinais ML Fase 2 em diferentes ambientes.

## Pré-requisitos

### Sistema Operacional
- Linux (Ubuntu 20.04+ recomendado)
- Windows 10/11 (para desenvolvimento)
- macOS 10.15+ (para desenvolvimento)

### Software Necessário
- Python 3.9+
- pip 21.0+
- Git
- Docker (opcional, mas recomendado)
- Redis (para cache distribuído)
- PostgreSQL 13+ (para persistência)

### Hardware Mínimo
- **Desenvolvimento:** 4GB RAM, 2 CPU cores, 10GB storage
- **Produção:** 8GB RAM, 4 CPU cores, 50GB storage
- **Alta Performance:** 16GB RAM, 8 CPU cores, 100GB SSD

## Instalação

### 1. Clone do Repositório

```bash
git clone <repository-url>
cd nacao_trader/motor
```

### 2. Ambiente Virtual

```bash
# Criar ambiente virtual
python -m venv venv

# Ativar (Linux/macOS)
source venv/bin/activate

# Ativar (Windows)
venv\Scripts\activate
```

### 3. Instalação de Dependências

```bash
# Instalar dependências básicas
pip install -r requirements.txt

# Instalar dependências de desenvolvimento (opcional)
pip install -r requirements-dev.txt
```

### 4. Configuração de Banco de Dados

#### PostgreSQL

```bash
# Instalar PostgreSQL (Ubuntu)
sudo apt update
sudo apt install postgresql postgresql-contrib

# Criar banco de dados
sudo -u postgres createdb motor_signals
sudo -u postgres createuser motor_user
sudo -u postgres psql -c "ALTER USER motor_user PASSWORD 'your_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE motor_signals TO motor_user;"
```

#### Redis

```bash
# Instalar Redis (Ubuntu)
sudo apt install redis-server

# Iniciar Redis
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

## Configuração

### 1. Variáveis de Ambiente

Crie um arquivo `.env` na raiz do projeto:

```env
# Configurações Básicas
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Banco de Dados
DATABASE_URL=postgresql://motor_user:your_password@localhost:5432/motor_signals
REDIS_URL=redis://localhost:6379/0

# APIs Externas
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key
FRED_API_KEY=your_fred_key
WORLD_BANK_API_KEY=your_world_bank_key
YAHOO_FINANCE_API_KEY=your_yahoo_key

# Rate Limiting
DEFAULT_RATE_LIMIT=100
BURST_SIZE=200
ADAPTIVE_RATE_LIMITING=true

# Cache
CACHE_MAX_SIZE=10000
DEFAULT_CACHE_TTL=300
CACHE_CLEANUP_INTERVAL=3600

# Monitoramento
METRICS_ENABLED=true
METRICS_PORT=8081
HEALTH_CHECK_INTERVAL=30

# Segurança
API_SECRET_KEY=your_secret_key_here
JWT_SECRET_KEY=your_jwt_secret_here
ENCRYPTION_KEY=your_encryption_key_here

# Proxy e User Agents
USE_PROXY_ROTATION=true
PROXY_LIST_URL=your_proxy_list_url
USER_AGENT_ROTATION=true

# WebSocket
WS_MAX_CONNECTIONS=1000
WS_HEARTBEAT_INTERVAL=30
WS_RECONNECT_ATTEMPTS=5

# Fallback
FALLBACK_ENABLED=true
FALLBACK_TIMEOUT=10
MAX_FALLBACK_ATTEMPTS=3

# Circuit Breaker
CIRCUIT_BREAKER_ENABLED=true
FAILURE_THRESHOLD=5
RECOVERY_TIMEOUT=60
```

### 2. Configuração de Logging

Crie `config/logging.yaml`:

```yaml
version: 1
disable_existing_loggers: false

formatters:
  standard:
    format: '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
  detailed:
    format: '%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s'
  json:
    format: '%(asctime)s'
    class: pythonjsonlogger.jsonlogger.JsonFormatter

handlers:
  console:
    class: logging.StreamHandler
    level: INFO
    formatter: standard
    stream: ext://sys.stdout
  
  file:
    class: logging.handlers.RotatingFileHandler
    level: DEBUG
    formatter: detailed
    filename: logs/motor.log
    maxBytes: 10485760  # 10MB
    backupCount: 5
  
  error_file:
    class: logging.handlers.RotatingFileHandler
    level: ERROR
    formatter: detailed
    filename: logs/error.log
    maxBytes: 10485760
    backupCount: 5

loggers:
  motor:
    level: DEBUG
    handlers: [console, file, error_file]
    propagate: false
  
  uvicorn:
    level: INFO
    handlers: [console, file]
    propagate: false

root:
  level: INFO
  handlers: [console, file]
```

### 3. Configuração de Coletores

Crie `config/collectors.yaml`:

```yaml
collectors:
  yahoo_finance:
    type: market_data
    enabled: true
    interval: 60
    rate_limit: 100
    timeout: 30
    max_retries: 3
    cache_ttl: 300
    priority: 1
    
  alpha_vantage:
    type: market_data
    enabled: true
    interval: 300
    rate_limit: 5
    timeout: 30
    max_retries: 3
    cache_ttl: 600
    priority: 2
    
  fred:
    type: economic_data
    enabled: true
    interval: 3600
    rate_limit: 120
    timeout: 30
    max_retries: 3
    cache_ttl: 3600
    priority: 1
    
  world_bank:
    type: economic_data
    enabled: true
    interval: 86400
    rate_limit: 100
    timeout: 60
    max_retries: 3
    cache_ttl: 86400
    priority: 2
    
  websocket_binance:
    type: market_data
    enabled: true
    url: "wss://stream.binance.com:9443/ws"
    reconnect_attempts: 5
    heartbeat_interval: 30
    priority: 1
    
  web_scraping:
    type: market_data
    enabled: true
    interval: 120
    rate_limit: 30
    timeout: 45
    max_retries: 3
    user_agent_rotation: true
    proxy_rotation: true
    priority: 3

fallback_chains:
  market_data:
    - yahoo_finance
    - alpha_vantage
    - web_scraping
    
  economic_data:
    - fred
    - world_bank
    
  realtime_data:
    - websocket_binance
    - yahoo_finance
```

## Deploy com Docker

### 1. Dockerfile

```dockerfile
FROM python:3.11-slim

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Criar usuário não-root
RUN useradd --create-home --shell /bin/bash motor

# Definir diretório de trabalho
WORKDIR /app

# Copiar requirements
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY . .

# Criar diretórios necessários
RUN mkdir -p logs data cache

# Definir permissões
RUN chown -R motor:motor /app
USER motor

# Expor portas
EXPOSE 8000 8081

# Comando padrão
CMD ["python", "main.py"]
```

### 2. Docker Compose

```yaml
version: '3.8'

services:
  motor:
    build: .
    ports:
      - "8000:8000"
      - "8081:8081"
    environment:
      - DATABASE_URL=postgresql://motor_user:password@postgres:5432/motor_signals
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
    restart: unless-stopped
    
  postgres:
    image: postgres:13
    environment:
      - POSTGRES_DB=motor_signals
      - POSTGRES_USER=motor_user
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped
    
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - motor
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

### 3. Executar com Docker

```bash
# Build e start
docker-compose up -d

# Verificar logs
docker-compose logs -f motor

# Parar serviços
docker-compose down
```

## Deploy Manual

### 1. Configuração do Systemd

Crie `/etc/systemd/system/motor-signals.service`:

```ini
[Unit]
Description=Motor de Sinais ML
After=network.target postgresql.service redis.service
Requires=postgresql.service redis.service

[Service]
Type=simple
User=motor
Group=motor
WorkingDirectory=/opt/motor-signals
Environment=PATH=/opt/motor-signals/venv/bin
ExecStart=/opt/motor-signals/venv/bin/python main.py
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=10

# Limites de recursos
LimitNOFILE=65536
LimitNPROC=4096

# Variáveis de ambiente
EnvironmentFile=/opt/motor-signals/.env

[Install]
WantedBy=multi-user.target
```

### 2. Configuração do Nginx

Crie `/etc/nginx/sites-available/motor-signals`:

```nginx
upstream motor_backend {
    server 127.0.0.1:8000;
    keepalive 32;
}

upstream motor_metrics {
    server 127.0.0.1:8081;
    keepalive 16;
}

server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;
    
    # SSL Configuration
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;
    
    # Security Headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";
    
    # API Routes
    location /api/ {
        proxy_pass http://motor_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Metrics Dashboard
    location /metrics/ {
        proxy_pass http://motor_metrics/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Autenticação básica (opcional)
        auth_basic "Metrics Dashboard";
        auth_basic_user_file /etc/nginx/.htpasswd;
    }
    
    # Health Check
    location /health {
        proxy_pass http://motor_backend/health;
        access_log off;
    }
    
    # Rate Limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;
}
```

### 3. Inicialização dos Serviços

```bash
# Habilitar e iniciar serviços
sudo systemctl enable motor-signals
sudo systemctl start motor-signals

# Verificar status
sudo systemctl status motor-signals

# Habilitar nginx
sudo systemctl enable nginx
sudo systemctl start nginx
```

## Monitoramento e Logs

### 1. Configuração de Logs

```bash
# Criar diretório de logs
sudo mkdir -p /var/log/motor-signals
sudo chown motor:motor /var/log/motor-signals

# Configurar logrotate
sudo tee /etc/logrotate.d/motor-signals << EOF
/var/log/motor-signals/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 motor motor
    postrotate
        systemctl reload motor-signals
    endscript
}
EOF
```

### 2. Monitoramento com Prometheus

Crie `config/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'motor-signals'
    static_configs:
      - targets: ['localhost:8081']
    scrape_interval: 10s
    metrics_path: '/metrics'
    
  - job_name: 'system'
    static_configs:
      - targets: ['localhost:9100']
```

### 3. Alertas com Grafana

Configure dashboards para monitorar:
- Taxa de sucesso dos coletores
- Latência das requisições
- Uso de recursos (CPU, memória)
- Taxa de cache hit/miss
- Número de fallbacks ativados
- Status dos circuit breakers

## Backup e Recuperação

### 1. Backup do Banco de Dados

```bash
#!/bin/bash
# backup_db.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/opt/backups/motor-signals"
DB_NAME="motor_signals"

mkdir -p $BACKUP_DIR

# Backup PostgreSQL
pg_dump -h localhost -U motor_user $DB_NAME | gzip > $BACKUP_DIR/db_backup_$DATE.sql.gz

# Backup Redis
redis-cli --rdb $BACKUP_DIR/redis_backup_$DATE.rdb

# Limpar backups antigos (manter 30 dias)
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete
find $BACKUP_DIR -name "*.rdb" -mtime +30 -delete

echo "Backup concluído: $DATE"
```

### 2. Restauração

```bash
#!/bin/bash
# restore_db.sh

BACKUP_FILE=$1
DB_NAME="motor_signals"

if [ -z "$BACKUP_FILE" ]; then
    echo "Uso: $0 <arquivo_backup>"
    exit 1
fi

# Parar serviço
sudo systemctl stop motor-signals

# Restaurar PostgreSQL
zcat $BACKUP_FILE | psql -h localhost -U motor_user $DB_NAME

# Iniciar serviço
sudo systemctl start motor-signals

echo "Restauração concluída"
```

## Troubleshooting

### Problemas Comuns

#### 1. Erro de Conexão com Banco

```bash
# Verificar status do PostgreSQL
sudo systemctl status postgresql

# Verificar conectividade
psql -h localhost -U motor_user -d motor_signals -c "SELECT 1;"

# Verificar logs
sudo tail -f /var/log/postgresql/postgresql-13-main.log
```

#### 2. Rate Limit Excedido

```bash
# Verificar configuração
grep -i rate /opt/motor-signals/.env

# Verificar logs de rate limiting
grep "rate limit" /var/log/motor-signals/motor.log

# Ajustar limites temporariamente
export DEFAULT_RATE_LIMIT=200
sudo systemctl restart motor-signals
```

#### 3. Cache Redis Indisponível

```bash
# Verificar status do Redis
sudo systemctl status redis-server

# Testar conectividade
redis-cli ping

# Verificar uso de memória
redis-cli info memory

# Limpar cache se necessário
redis-cli flushall
```

#### 4. WebSocket Desconectando

```bash
# Verificar configuração de proxy
nginx -t

# Verificar logs do WebSocket
grep "websocket" /var/log/motor-signals/motor.log

# Testar conexão direta
wscat -c ws://localhost:8000/ws
```

### Comandos Úteis

```bash
# Status geral do sistema
sudo systemctl status motor-signals postgresql redis-server nginx

# Logs em tempo real
sudo journalctl -f -u motor-signals

# Verificar portas em uso
sudo netstat -tlnp | grep -E ':(8000|8081|5432|6379)'

# Verificar uso de recursos
top -p $(pgrep -f "python main.py")

# Testar APIs
curl -X GET http://localhost:8000/health
curl -X GET http://localhost:8081/metrics

# Verificar configuração
python -c "from src.config import settings; print(settings.dict())"
```

## Segurança

### 1. Firewall

```bash
# Configurar UFW
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw deny 8000/tcp  # Bloquear acesso direto
sudo ufw deny 8081/tcp  # Bloquear acesso direto
```

### 2. SSL/TLS

```bash
# Gerar certificado Let's Encrypt
sudo certbot --nginx -d your-domain.com

# Renovação automática
sudo crontab -e
# Adicionar: 0 12 * * * /usr/bin/certbot renew --quiet
```

### 3. Autenticação

```bash
# Criar usuário para dashboard de métricas
sudo htpasswd -c /etc/nginx/.htpasswd admin
```

## Performance

### Otimizações Recomendadas

1. **Banco de Dados:**
   - Configurar connection pooling
   - Criar índices apropriados
   - Configurar autovacuum

2. **Cache:**
   - Ajustar TTL baseado no tipo de dados
   - Implementar cache warming
   - Monitorar hit rate

3. **Rate Limiting:**
   - Usar rate limiting adaptativo
   - Configurar burst adequado
   - Implementar backoff exponencial

4. **WebSocket:**
   - Configurar keep-alive
   - Implementar reconnect automático
   - Usar compression quando possível

Este guia fornece uma base sólida para deploy em produção. Ajuste as configurações conforme suas necessidades específicas e ambiente de infraestrutura.