FROM python:3.10-slim

# Diretório de trabalho
WORKDIR /app

# Dependências do sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalar TA-Lib (biblioteca C/C++ para análise técnica)
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    ca-certificates \
    && wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz \
    && tar -xzf ta-lib-0.4.0-src.tar.gz \
    && cd ta-lib/ \
    && ./configure --prefix=/usr \
    && make \
    && make install \
    && cd .. \
    && rm -rf ta-lib ta-lib-0.4.0-src.tar.gz \
    && apt-get remove -y wget \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements.txt
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o código-fonte
COPY . .

# Criar diretório para logs
RUN mkdir -p logs

# Variáveis de ambiente
ENV PYTHONPATH=/app
ENV PORT=8000
ENV HOST=0.0.0.0

# Expor a porta
EXPOSE 8000

# Comando para iniciar a API
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Para executar os coletores em segundo plano, comente o CMD acima e descomente o seguinte:
# CMD ["python", "-m", "src.collectors.run_collectors", "continuous"] 