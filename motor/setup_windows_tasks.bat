@echo off
echo Configurando tarefas agendadas para o Motor de Sinais da Nacao Trader...

REM Obter diretório atual
set MOTOR_DIR=%CD%
echo Diretorio do motor: %MOTOR_DIR%

REM Verificar Python
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Python nao encontrado! Verifique se o Python esta instalado e no PATH.
    exit /b 1
)

REM Criar diretório de logs se não existir
if not exist "%MOTOR_DIR%\logs" mkdir "%MOTOR_DIR%\logs"
echo Diretorio de logs criado/verificado: %MOTOR_DIR%\logs

REM Definir os caminhos completos
set DAILY_SIGNALS_SCRIPT=%MOTOR_DIR%\scripts\daily_signal_generator.py
set OTC_SIGNALS_SCRIPT=%MOTOR_DIR%\scripts\generate_otc_signals.py
set ASSETS_SCRIPT=%MOTOR_DIR%\scripts\fetch_yahoo_assets.py
set LOG_DIR=%MOTOR_DIR%\logs

REM Verificar se os scripts existem
if not exist "%DAILY_SIGNALS_SCRIPT%" (
    echo Erro: Script %DAILY_SIGNALS_SCRIPT% nao encontrado!
    exit /b 1
)
if not exist "%OTC_SIGNALS_SCRIPT%" (
    echo Erro: Script %OTC_SIGNALS_SCRIPT% nao encontrado!
    exit /b 1
)
if not exist "%ASSETS_SCRIPT%" (
    echo Erro: Script %ASSETS_SCRIPT% nao encontrado!
    exit /b 1
)

echo Criando tarefas agendadas...

REM Tarefa 1: Geracao diaria de sinais (00:05)
echo Configurando tarefa de geracao de sinais (00:05)...
schtasks /create /tn "NacaoTrader_GeracaoSinais" /tr "cmd /c cd /d %MOTOR_DIR% && python scripts\daily_signal_generator.py >> logs\task_signals.log 2>&1" /sc DAILY /st 00:05 /f
if %ERRORLEVEL% NEQ 0 (
    echo Erro ao criar tarefa de geracao de sinais!
) else (
    echo Tarefa de geracao de sinais configurada com sucesso!
)

REM Tarefa 2: Atualizacao de ativos (01:00)
echo Configurando tarefa de atualizacao de ativos (01:00)...
schtasks /create /tn "NacaoTrader_AtualizacaoAtivos" /tr "cmd /c cd /d %MOTOR_DIR% && python scripts\fetch_yahoo_assets.py >> logs\task_assets.log 2>&1" /sc DAILY /st 01:00 /f
if %ERRORLEVEL% NEQ 0 (
    echo Erro ao criar tarefa de atualizacao de ativos!
) else (
    echo Tarefa de atualizacao de ativos configurada com sucesso!
)

REM Tarefa 3: Backup de sinais (12:00)
echo Configurando tarefa de backup de sinais (12:00)...
schtasks /create /tn "NacaoTrader_BackupSinais" /tr "cmd /c cd /d %MOTOR_DIR% && python scripts\generate_otc_signals.py >> logs\task_backup.log 2>&1" /sc DAILY /st 12:00 /f
if %ERRORLEVEL% NEQ 0 (
    echo Erro ao criar tarefa de backup de sinais!
) else (
    echo Tarefa de backup de sinais configurada com sucesso!
)

echo Testando geracao de sinais...
python "%DAILY_SIGNALS_SCRIPT%"

echo.
echo Configuracao concluida!
echo As seguintes tarefas foram configuradas:
echo 1. Geracao diaria de sinais as 00:05 (daily_signal_generator.py)
echo 2. Atualizacao diaria de ativos as 01:00 (fetch_yahoo_assets.py)
echo 3. Backup de sinais OTC ao meio-dia 12:00 (generate_otc_signals.py)
echo.
echo Para verificar as tarefas, abra o Agendador de Tarefas do Windows ou execute:
echo    schtasks /query /tn "NacaoTrader*"
echo.
echo Logs serao salvos em: %LOG_DIR%
echo.
echo Lembre-se: A geracao de sinais requer conexao com o Supabase e variaveis
echo de ambiente corretamente configuradas no arquivo .env

pause 