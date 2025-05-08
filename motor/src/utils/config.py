"""
Utilitário de configuração para o Motor de Sinais ML.

Carrega configurações de variáveis de ambiente ou arquivo .env.
"""
import os
from typing import Dict, Any, Optional, List
from pathlib import Path

# Verificar qual versão do Pydantic está disponível
try:
    # Pydantic v2
    from pydantic_settings import BaseSettings as PydanticBaseSettings
    from pydantic import model_validator, Field
    PYDANTIC_V2 = True
except ImportError:
    try:
        # Talvez pydantic_settings não esteja instalado, mas pydantic v2 sim
        from pydantic import BaseSettings as PydanticBaseSettings, model_validator, Field
        # Instalar pydantic-settings automaticamente se pydantic v2 estiver disponível
        import subprocess
        import sys
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "pydantic-settings"], check=True)
            # Tentar importar novamente após instalação
            from pydantic_settings import BaseSettings as PydanticBaseSettings
        except Exception:
            # Se falhar, continuar com a classe base do pydantic
            pass
        PYDANTIC_V2 = True
    except ImportError:
        # Pydantic v1
        from pydantic import BaseSettings as PydanticBaseSettings, validator, Field
        PYDANTIC_V2 = False

# Encontrar diretório raiz do projeto
motor_root = Path(__file__).parent.parent.parent  # src/utils -> src -> motor

# Configuração da aplicação
if PYDANTIC_V2:
    class Settings(PydanticBaseSettings):
        # URLs e chaves de API
        SUPABASE_URL: str = ""
        SUPABASE_ANON_KEY: str = ""
        SUPABASE_SERVICE_KEY: str = ""
        DATABASE_URL: Optional[str] = None
        REDIS_URL: Optional[str] = None
        FINNHUB_API_KEY: Optional[str] = None
        ALPHA_VANTAGE_API_KEY: Optional[str] = None
        TWELVEDATA_API_KEY: Optional[str] = None
        
        # Configurações do servidor
        HOST: str = "0.0.0.0"
        PORT: int = 8000
        DEBUG: bool = False
        LOG_LEVEL: str = "INFO"
        
        # Intervalos de atualização (em segundos)
        DATA_COLLECTION_INTERVAL: int = 3600
        ASSETS_REFRESH_INTERVAL: int = 86400  # 1 dia
        ML_MODEL_UPDATE_INTERVAL: int = 604800  # 7 dias
        
        # Parâmetros do modelo ML
        ML_CONFIDENCE_THRESHOLD: float = 0.65
        SIGNAL_STRENGTH_THRESHOLD: float = 0.75
        
        # Cache e notificações
        CACHE_EXPIRY: int = 300  # 5 minutos
        ENABLE_NOTIFICATIONS: bool = True
        
        # Armazenamento de dados
        DATA_DIR: str = "./data"
        MODEL_DIR: str = "./models"
        
        model_config = {
            "env_file": str(motor_root / ".env"),
            "env_file_encoding": "utf-8",
            "extra": "allow"  # Permitir campos extras
        }
        
        @model_validator(mode="before")
        @classmethod
        def transform_booleans(cls, data: Any) -> Any:
            """Converte strings 'True'/'False' em booleanos."""
            if isinstance(data, dict):
                for key in data:
                    if isinstance(data[key], str):
                        if data[key].lower() == 'true':
                            data[key] = True
                        elif data[key].lower() == 'false':
                            data[key] = False
            return data
else:
    class Settings(PydanticBaseSettings):
        # URLs e chaves de API
        SUPABASE_URL: str = ""
        SUPABASE_ANON_KEY: str = ""
        SUPABASE_SERVICE_KEY: str = ""
        DATABASE_URL: Optional[str] = None
        REDIS_URL: Optional[str] = None
        FINNHUB_API_KEY: Optional[str] = None
        ALPHA_VANTAGE_API_KEY: Optional[str] = None
        TWELVEDATA_API_KEY: Optional[str] = None
        
        # Configurações do servidor
        HOST: str = "0.0.0.0"
        PORT: int = 8000
        DEBUG: bool = False
        LOG_LEVEL: str = "INFO"
        
        # Intervalos de atualização (em segundos)
        DATA_COLLECTION_INTERVAL: int = 3600
        ASSETS_REFRESH_INTERVAL: int = 86400  # 1 dia
        ML_MODEL_UPDATE_INTERVAL: int = 604800  # 7 dias
        
        # Parâmetros do modelo ML
        ML_CONFIDENCE_THRESHOLD: float = 0.65
        SIGNAL_STRENGTH_THRESHOLD: float = 0.75
        
        # Cache e notificações
        CACHE_EXPIRY: int = 300  # 5 minutos
        ENABLE_NOTIFICATIONS: bool = True
        
        # Armazenamento de dados
        DATA_DIR: str = "./data"
        MODEL_DIR: str = "./models"
        
        class Config:
            env_file = str(motor_root / ".env")
            env_file_encoding = "utf-8"
            extra = "allow"  # Permitir campos extras
        
        @validator('DEBUG', 'ENABLE_NOTIFICATIONS', pre=True)
        def parse_bool(cls, v):
            """Converte strings em booleanos."""
            if isinstance(v, str):
                return v.lower() == 'true'
            return v

# Carregar configurações
try:
    settings = Settings()
except Exception as e:
    import logging
    logging.warning(f"Erro ao carregar configurações: {e}. Usando valores padrão.")
    
    # Implementar um fallback se a configuração falhar
    class DefaultSettings:
        def __init__(self):
            # Obter valores do ambiente diretamente
            self.SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
            self.SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "")
            self.SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")
            self.DATABASE_URL = os.environ.get("DATABASE_URL")
            self.REDIS_URL = os.environ.get("REDIS_URL")
            self.HOST = os.environ.get("HOST", "0.0.0.0")
            self.PORT = int(os.environ.get("PORT", "8000"))
            self.DEBUG = os.environ.get("DEBUG", "").lower() == "true"
            self.LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
            self.DATA_DIR = os.environ.get("DATA_DIR", "./data")
            self.MODEL_DIR = os.environ.get("MODEL_DIR", "./models")
    
    settings = DefaultSettings()

# Verificar se configurações essenciais estão presentes
def verify_settings():
    """Verifica se as configurações essenciais estão presentes."""
    required_settings = ['SUPABASE_URL', 'SUPABASE_ANON_KEY', 'SUPABASE_SERVICE_KEY']
    missing = []
    
    for setting in required_settings:
        value = getattr(settings, setting, None)
        if not value:
            missing.append(setting)
    
    if missing:
        raise ValueError(f"Configurações ausentes: {', '.join(missing)}")

# Executar verificação se este módulo for executado diretamente
if __name__ == "__main__":
    try:
        verify_settings()
        print("Configurações válidas!")
        
        # Mostrar configurações sem expor chaves sensíveis
        for key, value in settings.__dict__.items():
            if "KEY" in key or "URL" in key:
                masked_value = value[:5] + "..." + value[-5:] if value and len(value) > 10 else "[vazio]"
                print(f"{key}: {masked_value}")
            else:
                print(f"{key}: {value}")
                
    except Exception as e:
        print(f"Erro na configuração: {e}") 