# 🚀 Guia de Deploy - Nação Trader

## 📋 Visão Geral

Este projeto pode ser deployado de diferentes formas:

1. **Railway** - Backend + Frontend (Recomendado)
2. **Vercel** - Frontend apenas
3. **Docker** - Desenvolvimento local
4. **Separado** - Backend no Railway, Frontend no Vercel

## 🚂 Deploy no Railway

### Opção 1: Projeto Completo (Frontend + Backend)

1. **Conectar Repositório**
   ```bash
   # No Railway Dashboard
   - New Project → Deploy from GitHub
   - Selecione o repositório nacao_trader
   ```

2. **Configurar Variáveis de Ambiente**
   ```env
   # Frontend
   VITE_SUPABASE_URL=sua_url_supabase
   VITE_SUPABASE_ANON_KEY=sua_chave_anon
   VITE_FINNHUB_API_KEY=sua_chave_finnhub
   VITE_ALPHA_VANTAGE_API_KEY=sua_chave_alpha_vantage
   
   # Backend
   SUPABASE_URL=sua_url_supabase
   SUPABASE_SERVICE_ROLE_KEY=sua_chave_service_role
   FINNHUB_API_KEY=sua_chave_finnhub
   ALPHA_VANTAGE_API_KEY=sua_chave_alpha_vantage
   PYTHON_VERSION=3.11
   PORT=8000
   ```

3. **Deploy Automático**
   - O Railway usará `railway.json` automaticamente
   - Build: `npm run build`
   - Start: `npm run start`

### Opção 2: Backend Separado

1. **Criar Novo Serviço**
   ```bash
   # No Railway Dashboard
   - New Project → Deploy from GitHub
   - Selecione o repositório
   - Configure para usar railway.backend.json
   ```

2. **Configurar Build**
   ```json
   {
     "build": {
       "builder": "NIXPACKS",
       "buildCommand": "cd motor && pip install -r requirements.txt"
     },
     "deploy": {
       "startCommand": "cd motor && python -m src.api.main"
     }
   }
   ```

## ▲ Deploy no Vercel (Frontend)

### 1. Conectar Repositório
```bash
# No Vercel Dashboard
- New Project → Import Git Repository
- Selecione nacao_trader
```

### 2. Configurar Build
```bash
# Build Command
npm run build

# Output Directory
dist

# Install Command
npm install
```

### 3. Variáveis de Ambiente
```env
VITE_SUPABASE_URL=sua_url_supabase
VITE_SUPABASE_ANON_KEY=sua_chave_anon
VITE_FINNHUB_API_KEY=sua_chave_finnhub
VITE_ALPHA_VANTAGE_API_KEY=sua_chave_alpha_vantage
```

### 4. Configurar API Routes (vercel.json)
```json
{
  "rewrites": [
    {
      "source": "/api/(.*)",
      "destination": "https://seu-backend.railway.app/api/$1"
    }
  ]
}
```

## 🐳 Deploy com Docker

### Desenvolvimento Local
```bash
# Iniciar todos os serviços
docker-compose up -d

# Ver logs
docker-compose logs -f

# Parar serviços
docker-compose down
```

### Produção
```bash
# Build das imagens
docker-compose -f docker-compose.prod.yml build

# Deploy
docker-compose -f docker-compose.prod.yml up -d
```

## 🔧 Configurações Específicas

### Railway - Variáveis de Ambiente
```env
# Sistema
PYTHON_VERSION=3.11
NODE_VERSION=18
PORT=8000
ENVIRONMENT=production

# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
VITE_SUPABASE_URL=https://xxx.supabase.co
VITE_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# APIs Financeiras
FINNHUB_API_KEY=xxx
ALPHA_VANTAGE_API_KEY=xxx
VITE_FINNHUB_API_KEY=xxx
VITE_ALPHA_VANTAGE_API_KEY=xxx
```

### Vercel - Configuração de Build
```json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "framework": "vite",
  "installCommand": "npm install"
}
```

## 🔍 Troubleshooting

### Erro de Build no Railway
```bash
# Verificar logs de build
railway logs --deployment

# Problemas comuns:
# 1. Python version - definir PYTHON_VERSION=3.11
# 2. Dependências - verificar requirements.txt
# 3. Comando start - verificar railway.json
```

### Erro de CORS
```javascript
// Configurar no backend (main.py)
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Erro de Variáveis de Ambiente
```bash
# Verificar se todas as variáveis estão definidas
# Frontend: VITE_*
# Backend: sem prefixo
```

## 📊 Monitoramento

### Railway
- **Logs**: Railway Dashboard → Deployments → Logs
- **Métricas**: CPU, RAM, Network
- **Alertas**: Configure webhooks

### Vercel
- **Analytics**: Vercel Dashboard → Analytics
- **Functions**: Logs de API routes
- **Performance**: Core Web Vitals

## 🔄 CI/CD

### GitHub Actions (Opcional)
```yaml
# .github/workflows/deploy.yml
name: Deploy
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to Railway
        run: |
          # Comandos de deploy
```

## 📝 Checklist de Deploy

### Antes do Deploy
- [ ] Todas as variáveis de ambiente configuradas
- [ ] Testes passando localmente
- [ ] Build funcionando
- [ ] Dependências atualizadas

### Após o Deploy
- [ ] Frontend carregando
- [ ] Backend respondendo
- [ ] APIs funcionando
- [ ] Banco de dados conectado
- [ ] Logs sem erros

### Produção
- [ ] HTTPS configurado
- [ ] Domínio personalizado
- [ ] Monitoramento ativo
- [ ] Backup configurado

---

**🚀 Deploy realizado com sucesso!**