# Manual de Geração de Sinais - Nação Trader

Este manual detalha o processo de configuração, execução e gerenciamento do sistema de geração automática de sinais para operações binárias da plataforma Nação Trader.

## Visão Geral do Sistema

O motor de geração de sinais resolve o problema da falta de sinais em períodos quando os mercados estão fechados (OTC - Over The Counter), garantindo que a plataforma sempre tenha sinais disponíveis para os usuários. O sistema foi projetado para:

1. Gerar sinais diários para operações binárias (CALL/PUT)
2. Oferecer análise técnica contextualizada por tipo de ativo
3. Manter histórico de sinais com metadados necessários
4. Atualizar preços de ativos regularmente
5. Distribuir sinais entre diferentes tipos de ativos (ações, forex, criptomoedas)

## Instalação e Configuração

### Pré-requisitos

- Python 3.8 ou superior
- Cliente Supabase configurado
- Arquivo `.env` com as seguintes variáveis:
  - `SUPABASE_URL`
  - `SUPABASE_SERVICE_KEY`

### Instalação

1. Clone o repositório (se ainda não o fez)
2. Configure o arquivo `.env` na pasta `motor/`

```bash
# Exemplo de conteúdo do .env
SUPABASE_URL=https://xxxxxxxxxxxxxxxxxxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

3. Instale as dependências:

```bash
cd motor
pip install -r requirements.txt
```

4. Verifique e configure a estrutura do banco de dados:

```bash
python scripts/ensure_signal_structure.py
```

## Estrutura de Arquivos

- `scripts/daily_signal_generator.py` - Gerador principal de sinais diários
- `scripts/generate_otc_signals.py` - Script para geração específica de sinais OTC
- `scripts/ensure_signal_structure.py` - Script para verificar e corrigir estrutura da base de dados
- `scripts/fetch_yahoo_assets.py` - Script para buscar dados de ativos do Yahoo Finance
- `setup_cron_jobs.sh` - Configurador de jobs cron para Linux/Mac
- `setup_windows_tasks.bat` - Configurador de tarefas agendadas para Windows
- `README_SIGNALS.md` - Documentação geral do sistema
- `logs/` - Diretório onde os logs são armazenados

## Execução Manual

### Verificação da Estrutura do Banco de Dados

Antes de iniciar a geração de sinais, verifique se a estrutura do banco de dados está correta:

```bash
python scripts/ensure_signal_structure.py
```

Este script:
- Verifica se as tabelas `assets` e `signals` existem
- Cria as tabelas se não existirem
- Corrige valores inconsistentes no campo `direction` (BUY → CALL, SELL → PUT)
- Garante que metadados necessários estejam presentes nos sinais existentes

### Geração de Sinais Diários

Para gerar sinais manualmente:

```bash
# Geração padrão (mínimo 15, máximo 25 sinais)
python scripts/daily_signal_generator.py

# Especificando mínimo/máximo de sinais
python scripts/daily_signal_generator.py --min 10 --max 20

# Forçando geração de sinais OTC (mesmo para mercados abertos)
python scripts/daily_signal_generator.py --force-otc

# Atualizando preços de ativos junto com geração de sinais
python scripts/daily_signal_generator.py --update-prices
```

### Geração de Sinais OTC

Para gerar apenas sinais OTC (útil como backup):

```bash
# Geração padrão (mínimo 10, máximo 15 sinais)
python scripts/generate_otc_signals.py

# Especificando mínimo/máximo de sinais
python scripts/generate_otc_signals.py 5 10
```

### Atualização de Ativos

Para atualizar os preços dos ativos no banco de dados:

```bash
# Usando simulação
python scripts/daily_signal_generator.py --update-prices

# Buscando do Yahoo Finance (pode ter rate limiting)
python scripts/fetch_yahoo_assets.py
```

## Configuração de Execução Automática

### Linux/Mac (via Cron)

Para configurar a execução automática via cron:

```bash
# Execute a partir da pasta motor/
bash setup_cron_jobs.sh
```

Este script configura:
1. Geração de sinais diariamente às 00:05 (daily_signal_generator.py)
2. Atualização de ativos diariamente às 01:00 (fetch_yahoo_assets.py)
3. Backup de sinais OTC ao meio-dia (12:00) (generate_otc_signals.py)

Para verificar os jobs configurados:
```bash
crontab -l
```

### Windows (via Agendador de Tarefas)

Para configurar a execução automática no Windows:

1. Abra um prompt de comando como Administrador
2. Navegue até a pasta motor/
3. Execute:
```
setup_windows_tasks.bat
```

Este script configura tarefas equivalentes às do Linux/Mac.

Para verificar as tarefas configuradas:
```
schtasks /query /tn "NacaoTrader*"
```

## Monitoramento

### Logs

Os logs são gerados na pasta `motor/logs/`:

- `daily_signals.log` - Logs do gerador principal
- `otc_signals.log` - Logs do gerador OTC
- `cron_signals.log` - Logs da execução via cron do gerador principal
- `cron_backup.log` - Logs da execução via cron do backup OTC
- `cron_assets.log` - Logs da atualização de ativos via cron
- `ensure_structure.log` - Logs da verificação da estrutura do banco

Para monitorar logs em tempo real:

```bash
# Linux/Mac
tail -f logs/daily_signals.log

# Windows PowerShell
Get-Content -Path logs\daily_signals.log -Wait
```

### Verificação de Sinais no Banco

Você pode verificar os sinais gerados diretamente no Supabase:

1. Acesse o Dashboard do Supabase
2. Vá para "Table Editor"
3. Selecione a tabela "signals"
4. Filtre por data em "generated_at"

## Solução de Problemas

### Nenhum Sinal Gerado

1. Verifique os logs para erros específicos
2. Confirme que as variáveis de ambiente estão corretas
3. Teste a conexão com o Supabase:

```bash
python -c "from dotenv import load_dotenv; import os; from supabase import create_client; load_dotenv(); supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_KEY')); print(supabase.table('assets').select('count(*)', count='exact').execute())"
```

4. Verifique se existem ativos na tabela `assets`:

```bash
python -c "from dotenv import load_dotenv; import os; from supabase import create_client; load_dotenv(); supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_KEY')); print(supabase.table('assets').select('count(*)', count='exact').execute())"
```

### Erros de Formato no Campo 'direction'

Se encontrar erros relacionados ao campo `direction`, execute o script de verificação da estrutura:

```bash
python scripts/ensure_signal_structure.py
```

### Jobs Cron/Tarefas Agendadas Não Executam

1. Verifique permissões de execução dos scripts (Linux/Mac):
```bash
chmod +x scripts/*.py
```

2. Verifique os logs do sistema:
```bash
# Linux/Mac
sudo grep CRON /var/log/syslog

# Windows
eventvwr # Abrir o Visualizador de Eventos
```

## Manutenção

### Limpeza de Logs

Para evitar arquivos de log muito grandes:

```bash
# Limpar logs com mais de 30 dias
find logs -name "*.log" -mtime +30 -delete
```

### Remoção de Sinais Expirados

Os sinais expirados podem ser marcados como tal, mas não são removidos automaticamente do banco. Para marcar sinais expirados:

```sql
-- Execute no SQL Editor do Supabase
UPDATE signals 
SET status = 'expired' 
WHERE valid_until < NOW() AND status = 'active';
```

## Próximas Melhorias Planejadas

1. **Integração com ML**: Implementação de modelos de machine learning para melhorar a qualidade dos sinais
2. **Análise Técnica Real**: Substituição da simulação por análise técnica baseada em dados reais
3. **Sistema de Feedback**: Rastreamento do sucesso dos sinais para aprimorar futuras previsões
4. **Dashboard de Monitoramento**: Interface web para acompanhar geração de sinais e estatísticas
5. **Notificações**: Sistema de alertas para falhas na geração de sinais

## Suporte

Se encontrar problemas ou tiver dúvidas:

1. Verifique os logs para mensagens de erro específicas
2. Teste os scripts com o parâmetro `--help` para ver todas as opções disponíveis
3. Execute os scripts manualmente para verificar comportamento
4. Contate a equipe de desenvolvimento com logs e detalhes do ambiente 