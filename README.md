# Nação Trader

Plataforma de trading com análise técnica e sinais automatizados usando Machine Learning.

## 🚀 Estrutura do Projeto

```
nacao_trader/
├── src/                    # Frontend React
├── motor/                  # Backend Python (API + ML)
├── public/                 # Arquivos estáticos
├── start_project.bat       # Script Windows
├── start_project.sh        # Script Unix/Linux/Mac
└── run_backend.bat         # Script apenas backend
```

## 🛠️ Tecnologias

### Frontend
- **React 18** com TypeScript
- **Vite** para build e desenvolvimento
- **Tailwind CSS** para estilização
- **Zustand** para gerenciamento de estado
- **Recharts** para gráficos
- **Supabase** para autenticação e dados

### Backend
- **Python 3.8+** com FastAPI
- **Machine Learning** para análise de sinais
- **APIs financeiras** (Finnhub, Alpha Vantage)
- **Supabase** para banco de dados

## 📋 Pré-requisitos

- **Node.js** 18+ ([Download](https://nodejs.org/))
- **Python** 3.8+ ([Download](https://python.org/))
- **Git** ([Download](https://git-scm.com/))

## 🚀 Instalação e Execução

### Método 1: Script Automático (Recomendado)

#### Windows
```bash
# Execute o script
.\start_project.bat
```

#### Linux/Mac
```bash
# Torne o script executável (primeira vez)
chmod +x start_project.sh

# Execute o script
./start_project.sh
```

### Método 2: Manual

#### 1. Instalar dependências
```bash
# Frontend
npm install

# Backend
cd motor
pip install -r requirements.txt
cd ..
```

#### 2. Configurar variáveis de ambiente
```bash
# Copiar arquivos de exemplo
cp .env.example .env
cp motor/.env.example motor/.env

# Editar os arquivos .env com suas chaves de API
```

#### 3. Executar serviços

**Terminal 1 - Backend:**
```bash
cd motor
python -m src.api.main
```

**Terminal 2 - Frontend:**
```bash
npm run dev
```

## 🌐 URLs de Acesso

- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8000
- **Documentação API:** http://localhost:8000/docs

## 🔧 Configuração de Ambiente

### Frontend (.env)
```env
VITE_SUPABASE_URL=sua_url_supabase
VITE_SUPABASE_ANON_KEY=sua_chave_anon
VITE_FINNHUB_API_KEY=sua_chave_finnhub
VITE_ALPHA_VANTAGE_API_KEY=sua_chave_alpha_vantage
```

### Backend (motor/.env)
```env
SUPABASE_URL=sua_url_supabase
SUPABASE_SERVICE_ROLE_KEY=sua_chave_service_role
FINNHUB_API_KEY=sua_chave_finnhub
ALPHA_VANTAGE_API_KEY=sua_chave_alpha_vantage
```

## 🚀 Deploy

### Railway (Backend + Frontend)

1. Conecte seu repositório ao Railway
2. Configure as variáveis de ambiente no painel
3. O deploy será automático usando `railway.json`

### Vercel (Frontend apenas)

1. Conecte seu repositório ao Vercel
2. Configure as variáveis de ambiente
3. O deploy será automático usando `vercel.json`

## 📁 Scripts Disponíveis

### Frontend
```bash
npm run dev      # Servidor de desenvolvimento
npm run build    # Build para produção
npm run preview  # Preview do build
npm run lint     # Verificar código
```

### Backend
```bash
python -m src.api.main  # Iniciar servidor
```

### Scripts do Projeto
```bash
# Windows
start_project.bat       # Inicia frontend + backend
run_backend.bat         # Inicia apenas backend

# Unix/Linux/Mac
./start_project.sh      # Inicia frontend + backend
```

## 🔍 Solução de Problemas

### Erro de Importação no Backend
```bash
# Certifique-se de estar no diretório correto
cd motor
python -m src.api.main
```

### Porta já em uso
```bash
# Verificar processos na porta 8000
netstat -ano | findstr :8000  # Windows
lsof -i :8000                 # Linux/Mac

# Matar processo
taskkill /PID <PID> /F        # Windows
kill -9 <PID>                 # Linux/Mac
```

### Dependências não instaladas
```bash
# Limpar cache e reinstalar
npm cache clean --force
rm -rf node_modules package-lock.json
npm install

# Backend
pip cache purge
pip install -r motor/requirements.txt --force-reinstall
```

## 📊 Funcionalidades

- ✅ **Dashboard** com métricas em tempo real
- ✅ **Análise Técnica** automatizada
- ✅ **Sinais de Trading** com ML
- ✅ **Backtesting** de estratégias
- ✅ **Gestão de Portfólio**
- ✅ **Alertas** personalizados
- ✅ **Histórico** de operações

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/nova-funcionalidade`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/nova-funcionalidade`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo [LICENSE](LICENSE) para detalhes.

## 📞 Suporte

Se encontrar problemas:

1. Verifique os logs em `backend.log`
2. Consulte a seção de solução de problemas
3. Abra uma issue no GitHub

---

**Desenvolvido com ❤️ para traders brasileiros**