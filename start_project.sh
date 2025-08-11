#!/bin/bash

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}    NACAO TRADER - INICIANDO PROJETO${NC}"
echo -e "${BLUE}========================================${NC}"
echo

# Função para cleanup ao sair
cleanup() {
    echo -e "\n${YELLOW}[INFO] Encerrando serviços...${NC}"
    
    # Encerrar processos em background
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
        echo -e "${GREEN}[INFO] Backend encerrado.${NC}"
    fi
    
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
        echo -e "${GREEN}[INFO] Frontend encerrado.${NC}"
    fi
    
    echo -e "${GREEN}[INFO] Projeto encerrado.${NC}"
    exit 0
}

# Configurar trap para cleanup
trap cleanup SIGINT SIGTERM

# Verificar se Node.js está instalado
if ! command -v node &> /dev/null; then
    echo -e "${RED}ERRO: Node.js não encontrado. Instale o Node.js primeiro.${NC}"
    exit 1
fi

# Verificar se Python está instalado
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo -e "${RED}ERRO: Python não encontrado. Instale o Python primeiro.${NC}"
    exit 1
fi

# Definir comando Python
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

echo -e "${BLUE}[INFO] Verificando dependências...${NC}"

# Instalar dependências do frontend se necessário
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}[INFO] Instalando dependências do frontend...${NC}"
    npm install
    if [ $? -ne 0 ]; then
        echo -e "${RED}ERRO: Falha ao instalar dependências do frontend.${NC}"
        exit 1
    fi
fi

# Verificar se o diretório do motor existe
if [ ! -d "motor/src" ]; then
    echo -e "${RED}ERRO: Diretório do motor não encontrado.${NC}"
    exit 1
fi

# Instalar dependências do backend se necessário
cd motor
if [ ! -f "requirements_installed.flag" ]; then
    echo -e "${YELLOW}[INFO] Instalando dependências do backend...${NC}"
    $PYTHON_CMD -m pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo -e "${RED}ERRO: Falha ao instalar dependências do backend.${NC}"
        exit 1
    fi
    touch requirements_installed.flag
fi
cd ..

# Verificar arquivos .env
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}[INFO] Criando arquivo .env do frontend...${NC}"
    cp ".env.example" ".env" 2>/dev/null || true
fi

if [ ! -f "motor/.env" ]; then
    echo -e "${YELLOW}[INFO] Criando arquivo .env do backend...${NC}"
    cp "motor/.env.example" "motor/.env" 2>/dev/null || true
fi

echo
echo -e "${GREEN}[INFO] Iniciando serviços...${NC}"
echo
echo -e "${BLUE}Frontend: http://localhost:5173${NC}"
echo -e "${BLUE}Backend:  http://localhost:8000${NC}"
echo
echo -e "${YELLOW}Pressione Ctrl+C para parar os serviços.${NC}"
echo

# Iniciar backend em segundo plano
echo -e "${BLUE}[INFO] Iniciando backend (Motor ML)...${NC}"
cd motor
$PYTHON_CMD -m src.api.main > ../backend.log 2>&1 &
BACKEND_PID=$!
cd ..

# Aguardar um pouco para o backend inicializar
sleep 3

# Verificar se o backend está rodando
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo -e "${RED}ERRO: Falha ao iniciar o backend. Verifique o arquivo backend.log${NC}"
    exit 1
fi

echo -e "${GREEN}[INFO] Backend iniciado com sucesso (PID: $BACKEND_PID)${NC}"

# Iniciar frontend
echo -e "${BLUE}[INFO] Iniciando frontend...${NC}"
npm run dev &
FRONTEND_PID=$!

# Aguardar os processos
wait $FRONTEND_PID

# Se chegou aqui, o frontend foi fechado
cleanup