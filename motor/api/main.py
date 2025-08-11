import sys
import os

# Adiciona o diretório raiz do projeto ao sys.path para resolver o ModuleNotFoundError
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fastapi import FastAPI
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()
from motor.api.v1.endpoints import signals

app = FastAPI(
    title="Nação Trader - Motor ML",
    description="API para o motor de análise e predição de mercado.",
    version="2.0.0"
)

app.include_router(signals.router, prefix="/api/v1", tags=["signals"])

@app.get("/")
def read_root():
    return {"message": "Bem-vindo ao Motor ML da Nação Trader"}