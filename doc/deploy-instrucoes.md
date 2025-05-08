# Configuração de Deploy no Railway

Este documento resume todas as configurações feitas para o deploy do projeto Nação Trader no Railway.

## Arquivos Criados

1. **Arquivos de Configuração do Railway:**
   - `railway.json` - Configuração principal do serviço frontend
   - `motor/railway.json` - Configuração específica para o serviço de backend (motor)

2. **Scripts GitFlow:**
   - `scripts/setup-gitflow.sh` - Configura o ambiente GitFlow com branches main, develop e staging
   - `scripts/create-feature.sh` - Cria uma nova feature branch a partir da develop
   - `scripts/create-hotfix.sh` - Cria uma nova hotfix branch a partir da main

3. **Documentação:**
   - `doc/deploy_railway.md` - Guia detalhado para deploy no Railway
   - Estrutura de diretórios `doc/features/` e `doc/hotfixes/` para documentação de alterações

4. **Configuração CI/CD:**
   - `.github/workflows/ci-cd.yml` - Pipeline de CI/CD para deploy automático no Railway

## Configurações Realizadas

1. **Configuração do package.json:**
   - Adicionado comando `start` para execução em produção

2. **Atualização do README.md:**
   - Adicionadas instruções detalhadas sobre o fluxo de trabalho GitFlow
   - Seção sobre deploy no Railway
   - Ajuste da estrutura do projeto para refletir os novos diretórios e arquivos
   - Removidas referências a uma autoria genérica, tornando o tom mais pessoal e profissional

3. **Estrutura de Diretórios:**
   - Criado diretório `scripts/` para os scripts de automação
   - Organização da documentação em `doc/` com subdiretórios específicos

## Como Implementar o Deploy

Para implementar o deploy no Railway, siga estes passos:

1. **Inicialização do GitFlow:**
   ```bash
   ./scripts/setup-gitflow.sh
   ```
   Isso configurará a estrutura de branches necessária para o GitFlow.

2. **Configuração do Railway:**
   - Crie uma conta no Railway caso ainda não tenha
   - Instale a CLI do Railway: `npm i -g @railway/cli`
   - Faça login: `railway login`

3. **Primeiro Deploy:**
   - Configure o projeto no Railway conforme descrito em `doc/deploy_railway.md`
   - Configure as variáveis de ambiente necessárias para cada ambiente
   - Conecte o repositório do GitHub ao Railway

4. **Workflow Contínuo:**
   - Desenvolvimento de features: `./scripts/create-feature.sh nome-da-feature`
   - Correções urgentes: `./scripts/create-hotfix.sh nome-do-hotfix`
   - Acompanhe o fluxo GitFlow para promover alterações entre os ambientes

## Ambientes Configurados

1. **Desenvolvimento (develop):**
   - URL: dev.nacaotrader.com.br
   - Variáveis específicas: `VITE_APP_ENV=development`, `LOG_LEVEL=DEBUG`

2. **Homologação (staging):**
   - URL: staging.nacaotrader.com.br
   - Variáveis específicas: `VITE_APP_ENV=staging`, `LOG_LEVEL=DEBUG`

3. **Produção (main):**
   - URL: app.nacaotrader.com.br
   - Variáveis específicas: `VITE_APP_ENV=production`, `LOG_LEVEL=INFO`

## Próximos Passos

1. **Configuração do DNS:**
   - Configure os domínios personalizados no Railway
   - Aponte os registros DNS para os URLs fornecidos pelo Railway

2. **Monitoramento:**
   - Configure alertas para falhas de deploy ou erros em produção
   - Implemente ferramentas adicionais de monitoramento conforme necessário

3. **Segurança:**
   - Revise as permissões de acesso ao Railway
   - Assegure-se de que as chaves sensíveis estão armazenadas como variáveis secretas 