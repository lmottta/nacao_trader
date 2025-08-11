@echo off
echo ========================================
echo    NACAO TRADER - INICIANDO PROJETO
echo ========================================
echo.

:: Verificar se Node.js está instalado
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERRO: Node.js não encontrado. Instale o Node.js primeiro.
    pause
    exit /b 1
)

:: Verificar se Python está instalado
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERRO: Python não encontrado. Instale o Python primeiro.
    pause
    exit /b 1
)

echo [INFO] Verificando dependências...

:: Instalar dependências do frontend se necessário
if not exist "node_modules" (
    echo [INFO] Instalando dependências do frontend...
    npm install
    if %errorlevel% neq 0 (
        echo ERRO: Falha ao instalar dependências do frontend.
        pause
        exit /b 1
    )
)

:: Instalar dependências do backend se necessário
if not exist "motor\src" (
    echo ERRO: Diretório do motor não encontrado.
    pause
    exit /b 1
)

cd motor
if not exist "__pycache__" (
    echo [INFO] Instalando dependências do backend...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo ERRO: Falha ao instalar dependências do backend.
        pause
        exit /b 1
    )
)
cd ..

:: Verificar arquivos .env
if not exist ".env" (
    echo [INFO] Criando arquivo .env do frontend...
    copy ".env.example" ".env" >nul 2>&1
)

if not exist "motor\.env" (
    echo [INFO] Criando arquivo .env do backend...
    copy "motor\.env.example" "motor\.env" >nul 2>&1
)

echo.
echo [INFO] Iniciando serviços...
echo.
echo Frontend: http://localhost:5173
echo Backend:  http://localhost:8000
echo.
echo Pressione Ctrl+C para parar os serviços.
echo.

:: Iniciar backend em segundo plano
echo [INFO] Iniciando backend (Motor ML)...
start /b cmd /c "cd motor && python -m src.api.main > ..\backend.log 2>&1"

:: Aguardar um pouco para o backend inicializar
timeout /t 3 /nobreak >nul

:: Iniciar frontend
echo [INFO] Iniciando frontend...
npm run dev

:: Se chegou aqui, o frontend foi fechado
echo.
echo [INFO] Frontend encerrado. Encerrando backend...

:: Encerrar processos Python relacionados ao projeto
taskkill /f /im python.exe >nul 2>&1

echo.
echo [INFO] Projeto encerrado.
pause