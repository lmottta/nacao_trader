# Nação Trader - Plataforma de Sinais de Trading

Plataforma completa para geração, análise e acompanhamento de sinais de trading baseados em análise técnica e machine learning.

![Licença](https://img.shields.io/badge/licença-MIT-blue)
![Versão](https://img.shields.io/badge/versão-1.0.0-green)

## Visão Geral

Desenvolvi a plataforma Nação Trader para fornecer uma solução integrada para traders que combina:

- **Sala de Sinais:** Interface moderna com múltiplos modos de visualização (Compacto, Detalhado, Lista)
- **Análise de Ativos:** Acompanhamento de ativos de diferentes mercados (Ações, Forex, Cripto)
- **Registro de Operações:** Acompanhamento de resultados e estatísticas de performance
- **Motor ML:** Backend Python para geração de sinais usando análise técnica e machine learning

## Recursos Principais

### Sala de Sinais
- **Três modos de visualização:**
  - **Modo Compacto:** Cards pequenos com informações essenciais (4 por linha)
  - **Modo Detalhado:** Cards tradicionais com mais informações (3 por linha)
  - **Modo Lista:** Formato tabular para máxima eficiência (15 itens por página)
- **Modal de detalhes** para visualização completa das informações
- **Exportação para CSV** de sinais filtrados ou completos
- **Filtros** por tipo de ativo e outros parâmetros
- **Design responsivo** adaptado para desktop e mobile

### Painel de Ativos
- Lista completa de ativos disponíveis para análise
- Filtro por tipo (Ações, Forex, Cripto)
- Status do mercado em tempo real
- Função de favoritar para acesso rápido

### Registro de Operações
- Cadastro de resultados de operações (Ganho/Perda)
- Estatísticas de performance (taxa de acerto)
- Histórico de operações com detalhes
- Anotações personalizadas

### Motor de Sinais (Backend)
- Coleta de dados de múltiplas fontes (Yahoo Finance, CoinGecko)
- Análise técnica com indicadores avançados
- Modelos ML para previsão de direção
- API REST para integração

## Tecnologias

Escolhi as seguintes tecnologias para o desenvolvimento:

### Frontend
- React + TypeScript
- Tailwind CSS para estilização
- Supabase para autenticação e banco de dados
- React Router para navegação
- Vite como build tool

### Backend (Motor ML)
- Python 3.10+
- FastAPI para API REST
- Scikit-learn, Pandas para análise de dados
- TimescaleDB (Supabase) para séries temporais
- APScheduler para tarefas agendadas

## Instalação e Execução

### Frontend

```bash
# Clone o repositório
git clone https://github.com/leomotta/nacao-trader.git
cd nacao-trader

# Instale as dependências
npm install

# Configure as variáveis de ambiente
cp .env.example .env
# Edite o arquivo .env com suas configurações

# Execute o servidor de desenvolvimento
npm run dev

# Build para produção
npm run build
```

### Backend (Motor ML)

```bash
# Navegue até a pasta do motor
cd motor

# Instale as dependências
python install_deps.py

# Configure as variáveis de ambiente
cp .env.example .env
# Edite o arquivo .env com suas configurações

# Execute a configuração inicial
python run_setup.py

# Inicie a API
python -m src.api.main
```

Para mais detalhes sobre o motor ML, consulte o [README do Motor](motor/README.md).

## Fluxo de Trabalho e Colaboração

Este projeto segue o padrão GitFlow para organização do código e colaboração. Implementei scripts para facilitar o trabalho com este fluxo:

### Configuração Inicial do GitFlow

Para configurar o ambiente de desenvolvimento com GitFlow:

```bash
# Configure o GitFlow (cria branches main, develop e staging)
./scripts/setup-gitflow.sh
```

### Desenvolvimento de Novas Features

Para começar a desenvolver uma nova funcionalidade:

```bash
# Cria uma nova branch de feature a partir da develop
./scripts/create-feature.sh nome-da-feature
```

O script criará uma branch `feature/nome-da-feature` e um arquivo de documentação em `doc/features/nome-da-feature.md`.

### Correções Urgentes (Hotfixes)

Para correções urgentes que precisam ir direto para produção:

```bash
# Cria uma nova branch de hotfix a partir da main
./scripts/create-hotfix.sh nome-do-hotfix
```

O script criará uma branch `hotfix/nome-do-hotfix` e um arquivo de documentação em `doc/hotfixes/nome-do-hotfix.md`.

### Fluxo Completo (GitFlow)

1. **Desenvolvimento:**
   - Trabalhe em features na branch `develop`
   - Crie branches `feature/*` para novas funcionalidades
   - Merge das features de volta para `develop`

2. **Homologação:**
   - Merge da `develop` para `staging`
   - Testes de integração e QA na `staging`

3. **Produção:**
   - Merge da `staging` para `main`
   - A branch `main` sempre reflete o código em produção

## Deploy no Railway

O projeto está configurado para deploy automatizado no Railway. Usei a seguinte estrutura:

1. **Ambientes de Deploy:**
   - `production`: Branch principal (main)
   - `staging`: Branch de homologação (staging)
   - `development`: Branch de desenvolvimento (develop)

2. **Variáveis de Ambiente:**
   - Configuradas diretamente no Railway para cada ambiente
   - Secrets armazenados de forma segura

3. **CI/CD Pipeline:**
   - Testes automatizados antes do deploy
   - Build otimizado para produção
   - Logs e monitoramento

Para mais detalhes sobre o deploy, consulte o [Guia de Deploy](doc/deploy_railway.md).

## Estrutura do Projeto

```
nacao-trader/
├── src/                       # Código fonte do frontend
│   ├── components/            # Componentes React reutilizáveis
│   ├── contexts/              # Contextos React (Auth, Assets, etc.)
│   ├── pages/                 # Páginas da aplicação
│   ├── lib/                   # Bibliotecas e utilitários
│   └── utils/                 # Funções utilitárias
├── motor/                     # Motor ML (backend)
│   ├── src/                   # Código fonte Python
│   ├── scripts/               # Scripts de utilidade
│   └── README.md              # Documentação específica do motor
├── scripts/                   # Scripts de automação e DevOps
│   ├── setup-gitflow.sh       # Configuração do GitFlow
│   ├── create-feature.sh      # Criação de features
│   └── create-hotfix.sh       # Criação de hotfixes
├── public/                    # Arquivos estáticos
├── doc/                       # Documentação do projeto
│   ├── doc.md                 # Histórico de desenvolvimento
│   ├── sala_sinais.md         # Detalhes da Sala de Sinais 
│   ├── deploy_railway.md      # Guia de deploy no Railway
│   ├── features/              # Documentação de features
│   └── hotfixes/              # Documentação de hotfixes
├── .env                       # Variáveis de ambiente (local)
└── README.md                  # Este arquivo
```

## Documentação

- [Histórico de Desenvolvimento](doc/doc.md) - Documentação detalhada do processo de desenvolvimento
- [README do Motor](motor/README.md) - Documentação específica do motor ML
- [Sala de Sinais](doc/sala_sinais.md) - Detalhes da implementação da Sala de Sinais
- [Guia de Deploy](doc/deploy_railway.md) - Instruções detalhadas para deploy no Railway

## Roadmap

Estou trabalhando nas seguintes funcionalidades para as próximas versões:

- [ ] Implementação de notificações push para novos sinais
- [ ] Dashboard administrativo para monitoramento global
- [ ] Integração com corretoras para execução automática
- [ ] App móvel nativo (iOS/Android)
- [ ] Backtesting avançado de estratégias

## Contribuição

Este é um projeto que desenvolvi pessoalmente, mas contribuições são bem-vindas. Se quiser colaborar, siga estas etapas:

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/nova-funcionalidade`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/nova-funcionalidade`)
5. Abra um Pull Request

## Licença

Distribuído sob a licença MIT. Veja `LICENSE` para mais informações.

## Sobre o Autor

**Leonardo A. Mota** - Desenvolvedor Python/React FullStack, apaixonado por trading algorítmico e análise técnica. Com mais de 5 anos de experiência em desenvolvimento de sistemas para o mercado financeiro.

- Email: [leomotta@gmail.com](mailto:leomotta@gmail.com)
- LinkedIn: [in/leomotta](https://linkedin.com/in/leomotta)
- GitHub: [github.com/leomotta](https://github.com/leomotta) 