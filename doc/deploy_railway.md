# Guia de Deploy no Railway com GitFlow

Este documento descreve o processo de deploy da aplicação Nação Trader no Railway usando o padrão GitFlow.

## Preparação do Ambiente

### 1. Configuração Inicial do Railway

1. Crie uma conta no [Railway](https://railway.app/) caso ainda não tenha
2. Instale a CLI do Railway:
   ```bash
   npm i -g @railway/cli
   ```
3. Faça login na CLI:
   ```bash
   railway login
   ```

### 2. Estrutura de Branches (GitFlow)

Sigo o padrão GitFlow para organização do código:

- `main`: Código em produção
- `staging`: Código em homologação
- `develop`: Código em desenvolvimento
- `feature/*`: Features em desenvolvimento
- `hotfix/*`: Correções urgentes

## Configuração do Projeto no Railway

### 1. Criação do Projeto

1. Acesse o [dashboard do Railway](https://railway.app/dashboard)
2. Clique em "New Project" > "Deploy from GitHub repo"
3. Selecione o repositório `nacaotrader/nt_bolt`
4. Configure os ambientes:

#### Ambiente de Produção (main)
- Nome: "Nação Trader - Production"
- Branch: main
- Domínio: app.nacaotrader.com.br

#### Ambiente de Homologação (staging)
- Nome: "Nação Trader - Staging"
- Branch: staging
- Domínio: staging.nacaotrader.com.br

#### Ambiente de Desenvolvimento (develop)
- Nome: "Nação Trader - Development"
- Branch: develop
- Domínio: dev.nacaotrader.com.br

### 2. Configuração dos Serviços

Para cada ambiente, crie dois serviços:

#### Frontend (React)
- Nome: nacao-trader-frontend
- Build Command: `npm run build`
- Start Command: `npm run start`

#### Backend (Motor ML)
- Nome: nacao-trader-motor
- Diretório raiz: `./motor`
- Build Command: `pip install -r requirements.txt`
- Start Command: `python -m src.api.main`

### 3. Variáveis de Ambiente

Configure as seguintes variáveis para cada ambiente:

#### Frontend (comum a todos os ambientes)
```
PORT=3000
NODE_ENV=${ambiente}
VITE_SUPABASE_URL=https://prcnldxsrpkhusanwffr.supabase.co
```

#### Frontend (específicas por ambiente)
```
# Production
VITE_API_URL=https://api.nacaotrader.com.br
VITE_APP_ENV=production

# Staging
VITE_API_URL=https://api-staging.nacaotrader.com.br
VITE_APP_ENV=staging

# Development
VITE_API_URL=https://api-dev.nacaotrader.com.br
VITE_APP_ENV=development
```

#### Backend (comum a todos os ambientes)
```
PYTHON_VERSION=3.10
SUPABASE_URL=https://prcnldxsrpkhusanwffr.supabase.co
```

#### Backend (específicas por ambiente)
```
# Production
APP_ENV=production
LOG_LEVEL=INFO

# Staging
APP_ENV=staging
LOG_LEVEL=DEBUG

# Development
APP_ENV=development
LOG_LEVEL=DEBUG
```

> **IMPORTANTE**: As chaves secretas (como SUPABASE_ANON_KEY, SUPABASE_SERVICE_KEY) devem ser adicionadas como variáveis de ambiente secretas no Railway.

## Fluxo de Trabalho

### 1. Desenvolvimento de Novas Features

```bash
# Cria uma nova branch de feature a partir da develop
git checkout develop
git pull
git checkout -b feature/nova-funcionalidade

# Implementa as alterações e commits
git add .
git commit -m "Implementação da nova funcionalidade"

# Envia para o repositório remoto
git push origin feature/nova-funcionalidade

# Quando concluído, crie um Pull Request para a branch develop
# Após aprovação e merge, a versão atualizada é automaticamente deployada no ambiente de desenvolvimento
```

### 2. Preparação para Homologação

```bash
# Merge da develop para staging
git checkout staging
git pull
git merge develop
git push origin staging

# O deploy para o ambiente de homologação será iniciado automaticamente
```

### 3. Deploy em Produção

```bash
# Merge da staging para main
git checkout main
git pull
git merge staging
git push origin main

# O deploy para o ambiente de produção será iniciado automaticamente
```

### 4. Hotfixes

```bash
# Cria uma branch de hotfix a partir da main
git checkout main
git pull
git checkout -b hotfix/correcao-urgente

# Implementa a correção e commits
git add .
git commit -m "Correção urgente: descrição do problema"

# Envia para o repositório remoto
git push origin hotfix/correcao-urgente

# Crie um Pull Request para a main
# Após aprovação e merge, a correção é deployada em produção

# Em seguida, aplique o mesmo hotfix na staging e develop
git checkout staging
git pull
git merge hotfix/correcao-urgente
git push origin staging

git checkout develop
git pull
git merge hotfix/correcao-urgente
git push origin develop
```

## Monitoramento e Logs

### Acesso aos Logs

1. Acesse o [dashboard do Railway](https://railway.app/dashboard)
2. Selecione o projeto e o ambiente desejado
3. Clique na aba "Deployments" para verificar os deploys recentes
4. Clique em um deployment para acessar os logs detalhados

### Monitoramento de Performance

O Railway oferece métricas básicas de uso de CPU, memória e rede. Para monitoramento mais avançado, configure uma das seguintes ferramentas:

- New Relic
- Sentry (para tracking de erros)
- Grafana + Prometheus (para métricas detalhadas)

## Procedimento de Rollback

Em caso de problemas após um deploy:

### Rollback via Railway Dashboard

1. Acesse o [dashboard do Railway](https://railway.app/dashboard)
2. Selecione o projeto e o ambiente com problemas
3. Clique na aba "Deployments"
4. Encontre o último deploy estável
5. Clique em "Redeploy" para reverter ao estado anterior

### Rollback via Git

```bash
# Identificar o commit estável anterior
git log --oneline

# Criar uma branch de rollback
git checkout -b rollback/YYYY-MM-DD
git reset --hard <commit-hash-estavel>
git push -f origin rollback/YYYY-MM-DD

# Fazer merge da branch de rollback para a branch afetada
git checkout main  # ou staging/develop
git merge rollback/YYYY-MM-DD
git push origin main
```

## Troubleshooting

### Problemas Comuns e Soluções

#### Build falha com erro de dependências
```
Verifique se todas as dependências estão listadas corretamente no package.json ou requirements.txt.
```

#### Erro de variáveis de ambiente
```
Confirme se todas as variáveis necessárias estão configuradas no dashboard do Railway.
```

#### Erro de porta em uso
```
O Railway gerencia automaticamente as portas. Certifique-se de que sua aplicação está usando a porta definida na variável de ambiente PORT.
```

#### Erro de permissão em arquivos
```
Verifique se os scripts executáveis têm permissão de execução (chmod +x).
```