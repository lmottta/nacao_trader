# Gerador Diário de Sinais para Operações Binárias

Este módulo garante que a plataforma Nação Trader sempre tenha sinais disponíveis diariamente para todos os tipos de ativos, incluindo operações em mercados fechados (OTC - Over The Counter).

## Funcionalidades Principais

- **Geração Automática de Sinais:** Produz entre 10-25 sinais diários para operações binárias (opções digitais)
- **Suporte a Mercados OTC:** Garante sinais mesmo quando os mercados estão fechados
- **Distribuição Equilibrada de Ativos:** Distribuição adequada entre ações, forex e criptomoedas
- **Análise Técnica Contextualizada:** Gera análises relevantes baseadas no tipo de ativo
- **Atualização de Preços:** Mantém preços de ativos atualizados diariamente

## Arquivos Principais

- `scripts/daily_signal_generator.py` - Gerador principal de sinais diários
- `scripts/generate_otc_signals.py` - Script específico para geração de sinais OTC
- `setup_cron_jobs.sh` - Script para configurar jobs cron (Linux/Mac)
- `setup_windows_tasks.bat` - Script para configurar tarefas agendadas (Windows)

## Configuração

### Pré-requisitos

- Python 3.8+
- Supabase configurado com tabelas `assets` e `signals`
- Variáveis de ambiente definidas no arquivo `.env`:
  - `SUPABASE_URL`
  - `SUPABASE_SERVICE_KEY`

### Execução Manual

Para gerar sinais manualmente:

```bash
# A partir do diretório motor/
python scripts/daily_signal_generator.py
```

Para forçar geração de sinais OTC:

```bash
# A partir do diretório motor/
python scripts/daily_signal_generator.py --force-otc

# Para especificar mínimo e máximo de sinais
python scripts/daily_signal_generator.py --min 15 --max 25 --force-otc
```

Para gerar apenas sinais OTC:

```bash
python scripts/generate_otc_signals.py

# Para especificar mínimo e máximo de sinais OTC
python scripts/generate_otc_signals.py 10 15
```

Para atualizar preços de ativos:

```bash
python scripts/daily_signal_generator.py --update-prices
```

### Configuração Automática

#### Linux/Mac (Cron)

Para garantir a geração automática de sinais, configure os jobs cron:

```bash
# A partir do diretório motor/
bash setup_cron_jobs.sh
```

Este script configurará três jobs:
1. **00:05 diariamente** - Geração principal de sinais (`daily_signal_generator.py`)
2. **01:00 diariamente** - Atualização de ativos (`fetch_yahoo_assets.py`)
3. **12:00 diariamente** - Geração de backup de sinais OTC (`generate_otc_signals.py`)

Configuração manual via crontab (`crontab -e`):

```
# Geração principal de sinais (00:05)
5 0 * * * cd /caminho/para/motor && python scripts/daily_signal_generator.py >> logs/cron_signals.log 2>&1

# Atualização de ativos (01:00)
0 1 * * * cd /caminho/para/motor && python scripts/fetch_yahoo_assets.py >> logs/cron_assets.log 2>&1

# Backup de sinais OTC (12:00) - garante sinais mesmo que o job principal falhe
0 12 * * * cd /caminho/para/motor && python scripts/generate_otc_signals.py >> logs/cron_backup.log 2>&1
```

#### Windows (Agendador de Tarefas)

Para configurar no Windows, execute o script batch como administrador:

```
# Clique com botão direito e selecione "Executar como administrador"
setup_windows_tasks.bat
```

Este script usa o Agendador de Tarefas do Windows para configurar as mesmas três tarefas:
1. **00:05 diariamente** - `NacaoTrader_GeracaoSinais`
2. **01:00 diariamente** - `NacaoTrader_AtualizacaoAtivos`
3. **12:00 diariamente** - `NacaoTrader_BackupSinais`

Para verificar as tarefas configuradas:
1. Abra o Agendador de Tarefas (Task Scheduler)
2. Procure por tarefas com o prefixo "NacaoTrader"

Ou execute no Prompt de Comando:
```
schtasks /query /tn "NacaoTrader*"
```

## Lógica de Geração de Sinais

### Processo de Geração

1. **Verificação de Sinais Existentes:**
   - Verifica se já existem sinais suficientes para o dia atual
   - Calcula quantos sinais ainda precisam ser gerados

2. **Seleção de Ativos:**
   - Obtém ativos da tabela `assets` no Supabase
   - Distribui entre diferentes tipos (40% ações, 30% forex, 30% cripto)
   - Garante diversidade de ativos nos sinais gerados

3. **Geração de Sinais:**
   - Cada sinal inclui:
     - Direção (CALL/PUT)
     - Confiança (60-95%)
     - Horários de entrada recomendados
     - Análise técnica contextual baseada no tipo de ativo
     - Validade de 24 horas
     - Preços recomendados e alvos

4. **Persistência:**
   - Os sinais são armazenados na tabela `signals` do Supabase
   - Disponíveis imediatamente para visualização no frontend

### Tipos de Sinais

1. **Sinais de Mercado Regular:**
   - Gerados para ativos com mercado aberto
   - Baseados em indicadores técnicos como RSI, MACD, Bollinger

2. **Sinais OTC (Over The Counter):**
   - Gerados para períodos de mercado fechado
   - Incluem análises contextualizadas específicas para OTC
   - Marcados com `is_otc: true` nos metadados
   - Relevantes para operações em corretoras que oferecem ativos OTC

## Monitoramento

Os logs são gerados em:

- `logs/daily_signals.log` - Logs do gerador principal
- `logs/otc_signals.log` - Logs específicos da geração OTC
- `logs/cron_signals.log` - Logs do job cron principal
- `logs/cron_assets.log` - Logs da atualização de ativos
- `logs/cron_backup.log` - Logs do job de backup

Para monitorar a geração de sinais em tempo real:

```bash
# Para ver os logs do gerador principal
tail -f logs/daily_signals.log

# Para ver os logs dos jobs cron
tail -f logs/cron_*.log
```

## Estrutura dos Sinais (tabela `signals`)

Campos obrigatórios:
- `asset_id` - ID do ativo
- `asset_symbol` - Símbolo do ativo (ex: BTCUSD, EURUSD, AAPL)
- `direction` - Direção do sinal: `CALL` ou `PUT`
- `confidence` - Confiança/probabilidade de sucesso (0.60 - 0.95)
- `accuracy` - Precisão histórica (campo obrigatório)
- `generated_at` - Data/hora de geração
- `valid_until` - Data/hora de validade
- `status` - Status do sinal (`active`, `expired`, `successful`, `failed`)
- `timeframe` - Período do sinal (normalmente `1d` para diário)
- `source` - Fonte do sinal (`OTC_ANALYSIS`, `TECHNICAL_ANALYSIS`, etc.)

Campos opcionais/metadados:
- `indicators` - Indicadores técnicos usados (RSI, MACD, etc.)
- `notes` - Análise textual do sinal
- `metadata` - JSON com informações adicionais:
  - `is_otc` - Se é um sinal OTC
  - `entry_times` - Horários recomendados para entrada
  - `recommended_price` - Preço recomendado para entrada
  - `target_price` - Preço-alvo esperado
  - `market_status` - Status do mercado

## Solução de Problemas

### Sinais não estão aparecendo

Verifique:
1. Se os jobs cron/tarefas agendadas estão ativos: `crontab -l` (Linux) ou `schtasks /query /tn "NacaoTrader*"` (Windows)
2. Os logs em `logs/` para erros específicos
3. Conexão com Supabase funcionando (teste com uma query simples)
4. Se a estrutura das tabelas está correta:
   - `direction` em `signals` deve aceitar apenas valores `CALL` e `PUT`
   - `accuracy` não pode ser nulo
   - `metadata` deve ser do tipo JSONB
5. Variáveis de ambiente `.env` corretamente configuradas

### Corrigindo o campo `direction`

Se encontrar erros relacionados ao campo `direction`, pode ser necessário atualizar sinais existentes:

```sql
-- Executar no SQL Editor do Supabase para corrigir
UPDATE signals SET direction = 'CALL' WHERE direction = 'BUY';
UPDATE signals SET direction = 'PUT' WHERE direction = 'SELL';
```

### Corrigindo problemas de conexão Supabase

```bash
# Teste a conexão com o Supabase
cd motor
python -c "from dotenv import load_dotenv; import os; from supabase import create_client; load_dotenv(); supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_KEY')); print(supabase.table('assets').select('count(*)', count='exact').execute())"
```

### Forçando geração de sinais manualmente

Se precisar gerar sinais imediatamente:

```bash
cd /caminho/para/motor
python scripts/generate_otc_signals.py
```

## Próximos Passos

- **Integração com Análise Técnica Real:**
  - Implementar indicadores técnicos reais usando bibliotecas como TA-Lib
  - Adicionar análise de padrões de candlestick reais

- **Modelo de Machine Learning:**
  - Desenvolver modelo preditivo para direção de preços
  - Implementar sistema de feedback baseado no sucesso dos sinais

- **Melhoria na Qualidade dos Sinais:**
  - Identificação de suportes e resistências reais
  - Detecção de tendências usando séries temporais
  - Análise de correlação entre ativos

- **Alertas e Notificações:**
  - Notificações push para sinais de alta confiança
  - Alertas de sucesso/falha de geração automática

## Atualizações Recentes

- Corrigido uso consistente de `CALL`/`PUT` em vez de `BUY`/`SELL`
- Melhorada distribuição de ativos por tipo
- Adicionada análise técnica mais contextualizada
- Implementada geração de logs estruturados
- Adicionado suporte a parâmetros de linha de comando
- Melhorada compatibilidade entre scripts 