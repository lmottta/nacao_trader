#!/bin/bash

# Script para configurar jobs cron para geração de sinais e atualização de ativos
# Executar como: bash setup_cron_jobs.sh

# Obter o diretório atual (onde o motor está instalado)
MOTOR_DIR=$(pwd)
PYTHON_PATH=$(which python || which python3)

echo "Configurando jobs cron para o Motor de Sinais Nação Trader..."
echo "Diretório do motor: $MOTOR_DIR"
echo "Python: $PYTHON_PATH"

# Verificar se os scripts existem
DAILY_SCRIPT="$MOTOR_DIR/scripts/daily_signal_generator.py"
OTC_SCRIPT="$MOTOR_DIR/scripts/generate_otc_signals.py"
ASSETS_SCRIPT="$MOTOR_DIR/scripts/fetch_yahoo_assets.py"

if [ ! -f "$DAILY_SCRIPT" ]; then
    echo "Erro: Script $DAILY_SCRIPT não encontrado!"
    exit 1
fi

if [ ! -f "$OTC_SCRIPT" ]; then
    echo "Erro: Script $OTC_SCRIPT não encontrado!"
    exit 1
fi

if [ ! -f "$ASSETS_SCRIPT" ]; then
    echo "Erro: Script $ASSETS_SCRIPT não encontrado!"
    exit 1
fi

# Criar diretório de logs se não existir
mkdir -p "$MOTOR_DIR/logs"
echo "Diretório de logs verificado: $MOTOR_DIR/logs"

# Criar arquivo temporário para o crontab
TEMP_CRON=$(mktemp)

# Obter o crontab atual
crontab -l > $TEMP_CRON 2>/dev/null || echo "# Crontab para Nação Trader Motor" > $TEMP_CRON

# Verificar se os jobs já existem para evitar duplicação
if ! grep -q "daily_signal_generator.py" $TEMP_CRON; then
    # Adicionar job diário para gerar sinais (00:05)
    echo "# Geração diária de sinais (00:05)" >> $TEMP_CRON
    echo "5 0 * * * cd $MOTOR_DIR && $PYTHON_PATH scripts/daily_signal_generator.py >> $MOTOR_DIR/logs/cron_signals.log 2>&1" >> $TEMP_CRON
    
    # Adicionar job para atualizar ativos (01:00)
    echo "# Atualização diária de ativos (01:00)" >> $TEMP_CRON
    echo "0 1 * * * cd $MOTOR_DIR && $PYTHON_PATH scripts/fetch_yahoo_assets.py >> $MOTOR_DIR/logs/cron_assets.log 2>&1" >> $TEMP_CRON
    
    # Adicionar job de backup para garantir que existam sinais mesmo se o principal falhar (12:00)
    echo "# Backup de sinais OTC ao meio-dia (12:00)" >> $TEMP_CRON
    echo "0 12 * * * cd $MOTOR_DIR && $PYTHON_PATH scripts/generate_otc_signals.py >> $MOTOR_DIR/logs/cron_backup.log 2>&1" >> $TEMP_CRON
    
    # Instalar o novo crontab
    crontab $TEMP_CRON
    echo "Jobs cron configurados com sucesso!"
else
    echo "Jobs cron já estão configurados. Nenhuma alteração realizada."
fi

# Remover arquivo temporário
rm $TEMP_CRON

echo "Verificando permissões dos scripts..."
chmod +x "$MOTOR_DIR/scripts/daily_signal_generator.py"
chmod +x "$MOTOR_DIR/scripts/generate_otc_signals.py"
chmod +x "$MOTOR_DIR/scripts/fetch_yahoo_assets.py"

echo "Testando geração de sinais..."
cd "$MOTOR_DIR" && $PYTHON_PATH scripts/daily_signal_generator.py

echo "Configuração concluída!"
echo "Os seguintes jobs foram configurados:"
echo "1. Geração diária de sinais às 00:05 (daily_signal_generator.py)"
echo "2. Atualização diária de ativos às 01:00 (fetch_yahoo_assets.py)"
echo "3. Backup de sinais OTC ao meio-dia (12:00) (generate_otc_signals.py)"
echo
echo "Logs serão salvos em: $MOTOR_DIR/logs/"
echo
echo "Lembre-se: A geração de sinais requer conexão com o Supabase e variáveis"
echo "de ambiente corretamente configuradas no arquivo .env" 