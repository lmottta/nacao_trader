# Motor de Sinais ML - Nação Trader

Motor de processamento de sinais baseado em análise técnica e machine learning para o projeto Nação Trader.

## Requisitos

- Python 3.10 ou superior
- PostgreSQL com TimescaleDB (provisionado pelo Supabase)
- Node.js 18+ (para funções edge do Supabase)

## Instalação

O processo de instalação foi simplificado para facilitar o início do trabalho com o projeto:

### 1. Clone o repositório

```bash
git clone https://github.com/nacaotrader/nt_bolt.git
cd nt_bolt/motor
```

### 2. Instale as dependências

Escolha uma das opções abaixo:

**Opção 1 - Usar o script de instalação automática (Recomendado):**

```bash
python install_deps.py
```

O script oferecerá diferentes opções de instalação e instalará automaticamente as dependências essenciais.

**Opção 2 - Instalar apenas as dependências essenciais:**

```bash
python install_deps.py --core
```

**Opção 3 - Instalar todas as dependências:**

```bash
python install_deps.py --all
```

**Opção 4 - Instalar manualmente todas as dependências:**

```bash
pip install -r requirements.txt
```

### 3. Configure as variáveis de ambiente

Crie um arquivo `.env` na pasta `motor/` baseado no arquivo `.env.example`:

```bash
cp .env.example .env
```

Edite o arquivo `.env` com suas configurações:

```
# Supabase
SUPABASE_URL=https://seu-projeto.supabase.co
SUPABASE_ANON_KEY=sua-chave-anonima-do-supabase
SUPABASE_SERVICE_KEY=sua-chave-de-servico-do-supabase

# Configurações de API
API_KEY=chave-api-secreta
```

## Configuração e Verificação

Execute o script de configuração:

```bash
python run_setup.py
```

Este script realizará as seguintes tarefas:
- Verificar as variáveis de ambiente necessárias
- Configurar o TimescaleDB no Supabase
- Verificar as funções edge
- Executar testes de integração básicos
- Inserir dados de teste para validação

O script também verificará e instalará automaticamente dependências faltantes se necessário.

### Opções do script de configuração

```bash
python run_setup.py --help
```

Opções disponíveis:
- `--skip-db`: Pular configuração do banco de dados
- `--skip-edge`: Pular verificação de funções edge
- `--skip-data`: Pular inserção de dados de teste
- `--skip-tests`: Pular testes de performance
- `--env-only`: Verificar apenas as variáveis de ambiente

## Execução da API

Após a configuração, inicie a API com:

```bash
python -m src.api.main
```

A API estará disponível em http://localhost:8000 por padrão.

## Resolução de Problemas Comuns

### Problema: Erro de importação de módulos

Mensagem de erro:
```
ModuleNotFoundError: No module named 'loguru' (ou outra dependência)
```

**Solução**: Execute o instalador de dependências:
```bash
python install_deps.py
```

### Problema: Erro com módulos que iniciam com números

Se encontrar erros ao importar módulos cujos nomes começam com números (como 002_setup_timescaledb.py):

**Solução**: 
Utilize o importador dinâmico conforme implementado no script run_setup.py, que resolve automaticamente este problema.

### Problema: Erro com TimescaleDB

Se você encontrar erros relacionados ao TimescaleDB:

**Solução**: 
1. Verifique se seu projeto Supabase tem a extensão TimescaleDB habilitada
2. Execute novamente o script de configuração com logs avançados:
```bash
LOG_LEVEL=DEBUG python run_setup.py --skip-edge --skip-data
```

### Problema: Incompatibilidade com Pydantic v2

Se encontrar erros relacionados ao Pydantic, como mensagens sobre model_config ou settings:

**Solução**:
O projeto agora é compatível com Pydantic v1 e v2, mas recomendamos usar a v2:
```bash
pip install "pydantic>=2.0.0" pydantic-settings
```

### Problema: Variáveis de ambiente não encontradas

**Solução**: 
1. Verifique se o arquivo `.env` foi criado corretamente no diretório `motor/`
2. Execute `python run_setup.py --env-only` para verificar as variáveis de ambiente

### Problema: Erro ao executar testes de integração

**Solução**:
1. Verifique se o Supabase está corretamente configurado
2. Execute a configuração novamente com opções reduzidas:
```bash
python run_setup.py --skip-tests
```

## Estrutura do Projeto

```
motor/
├── src/                    # Código fonte principal
│   ├── api/                # API FastAPI
│   ├── db/                 # Integração com banco de dados
│   │   ├── migrations/     # Migrações do banco de dados
│   │   └── client.py       # Cliente de conexão ao Supabase
│   ├── models/             # Modelos de dados
│   ├── processors/         # Processadores de sinais e ML
│   └── utils/              # Utilitários
│       └── config.py       # Configurações com suporte a Pydantic v1 e v2
├── tests/                  # Testes unitários
├── .env                    # Variáveis de ambiente (criar localmente)
├── .env.example            # Exemplo de variáveis de ambiente
├── run_setup.py            # Script de configuração
├── install_deps.py         # Script de instalação de dependências
└── requirements.txt        # Dependências do projeto
```

## Compatibilidade

O projeto foi projetado para ser compatível com:

- **Pydantic v1 e v2**: Suporte automático para ambas as versões
- **Python 3.10+**: Testado com Python 3.10 e 3.11
- **Supabase**: Compatível com a API mais recente do Supabase

## Documentação Adicional

Para mais informações sobre o projeto, consulte:

- [Documento de Implementação](implementacao_sprint1.md) - Detalhes sobre as implementações realizadas
- [Análise de Implementação](analise_implementacao.md) - Análise técnica e próximos passos
- [Documentação Geral](../doc/doc.md) - Documentação geral do projeto

## Visão Geral

Este subprojeto implementa o "motor" de processamento de sinais para a plataforma Nação Trader. O motor é responsável por:

1. Coletar dados de mercado de diversas fontes
2. Processar esses dados usando modelos de Machine Learning
3. Gerar sinais de trading com métricas de confiança
4. Fornecer uma API para integração com o frontend

## Recursos Implementados

### Coletores de Dados

O projeto implementa coletores para as seguintes fontes de dados:

- **Yahoo Finance**: Dados de ações, forex e índices de mercado
- **CoinGecko**: Dados de criptomoedas
- **Finnhub**: Dados de ações com API key (opcional)

### Modelos de Machine Learning

O sistema suporta diversos tipos de modelos:

- Random Forest
- Gradient Boosting
- Logistic Regression
- Ensemble (combinação ponderada dos modelos acima)

Cada modelo é configurável e pode ser treinado com diferentes conjuntos de features.

### Features Técnicas

Os modelos usam uma variedade de features técnicas:

- Retornos (1, 2, 5, 10 dias)
- Médias móveis (5, 10, 20, 50 períodos)
- RSI (Relative Strength Index)
- MACD (Moving Average Convergence Divergence)
- Bandas de Bollinger
- Indicadores de volume
- Volatilidade (ATR)

### API REST

A API fornece endpoints para:

- Geração de sinais sob demanda
- Consulta de sinais existentes
- Gerenciamento de modelos (treinar, avaliar, registrar)
- Visualização de dados históricos

## Integração com Supabase

O motor usa Supabase como backend para armazenamento e autenticação:

- **Auth**: Autenticação e autorização
- **Database**: Armazenamento de dados de mercado e sinais
- **Edge Functions**: Processamento sob demanda

### Tabelas do Banco de Dados

- **assets**: Informações sobre ativos financeiros
- **price_history**: Dados históricos de preços (OHLCV)
- **signals**: Sinais gerados pelo motor
- **model_registry**: Registro de modelos ML treinados
- **user_operations**: Registro de operações do usuário

## Exemplos de Uso

### Treinamento de um Modelo

```python
from motor.src.processors.ml_processor import train_model

# Treinar modelo para um ativo específico
performance = train_model(
    asset_id="AAPL",
    timeframe="1d",
    force_retrain=True
)

print(f"Modelo treinado com accuracy: {performance.accuracy:.4f}")
```

### Geração de um Sinal

```python
import asyncio
from motor.src.processors.ml_processor import generate_ml_signal

async def generate_signal():
    signal = await generate_ml_signal(
        asset_id="AAPL",
        asset_symbol="AAPL",
        timeframe="1d"
    )
    
    print(f"Sinal gerado: {signal['direction']} com confiança {signal['confidence']:.2f}")
    print(f"Preço alvo: {signal['price_target']}")

# Executar de forma assíncrona
asyncio.run(generate_signal())
```

## Próximos Passos

- [ ] Implementar mais fontes de dados (Alpha Vantage, Twelve Data)
- [ ] Adicionar modelos de rede neural (LSTM, Transformer)
- [ ] Implementar sistema de notificação de sinais em tempo real
- [ ] Adicionar backtesting mais robusto
- [ ] Implementar dashboard de administração
- [ ] Melhorar a integração com frontend via WebSockets

## Contribuição

Contribuições são bem-vindas! Por favor, siga estas etapas:

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/amazing-feature`)
3. Commit suas mudanças (`git commit -m 'Add some amazing feature'`)
4. Push para a branch (`git push origin feature/amazing-feature`)
5. Abra um Pull Request

## Licença

Distribuído sob a licença MIT. Veja `LICENSE` para mais informações.

## Contato

Nação Trader - [contato@nacaotrader.com.br](mailto:contato@nacaotrader.com.br)

Link do Projeto: [https://github.com/seu-usuario/nacao-trader](https://github.com/seu-usuario/nacao-trader)

## Novidades Recentes

### Filtro por Status de Mercado no Frontend

A listagem de ativos agora permite filtrar por status de mercado diretamente na interface:
- **Opções disponíveis:** Aberto, Fechado, Pré-Abertura, Pós-Fechamento, OTC, Estendido, Todos
- O filtro pode ser combinado com busca por nome/símbolo e tipo de ativo.
- O número de ativos exibidos reflete o filtro aplicado.

**Exemplo de uso:**
- Acesse a tela de "Ativos Disponíveis" no frontend.
- Use o seletor "Status de Mercado" para visualizar apenas ativos abertos, fechados, etc.

### Execução Automática do Coletor de Ativos

Agora o script de coleta de ativos do Yahoo Finance (`fetch_yahoo_assets.py`) pode ser executado automaticamente a cada 5 minutos usando o agendador `fetch_yahoo_assets_scheduler.py`.

**Como funciona:**
- Utiliza APScheduler para agendamento periódico.
- Garante que apenas uma instância rode por vez (lock em arquivo).
- Logs detalhados são salvos em `motor/logs/collector.log`.
- O lock é removido automaticamente se travado por mais de 1 hora.

**Como rodar:**
```bash
cd motor/scripts
python fetch_yahoo_assets_scheduler.py
```
O coletor será executado a cada 5 minutos automaticamente.

**Logs:**
- Todos os eventos, erros e execuções são registrados em `motor/logs/collector.log`.

**Exemplo de lock:**
- Se o job anterior ainda estiver rodando, a execução é pulada e um aviso é logado. 