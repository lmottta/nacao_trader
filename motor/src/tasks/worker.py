"""
Configuração do worker Celery para processamento assíncrono de tarefas.
"""
import os
from typing import Any, Dict, List, Optional

from celery import Celery
from loguru import logger

from src.utils.config import settings

# Configuração do Celery
celery_app = Celery(
    "nacao_trader_motor",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

# Configurações do Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Sao_Paulo",
    enable_utc=True,
    task_track_started=True,
    worker_hijack_root_logger=False,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "src.tasks.asset_tasks.*": {"queue": "assets"},
        "src.tasks.signal_tasks.*": {"queue": "signals"},
        "src.tasks.ml_tasks.*": {"queue": "ml"},
    },
)

# Configurar filas específicas
QUEUE_NAMES = ["assets", "signals", "ml", "celery"]

# Importar tarefas
from src.tasks import asset_tasks, signal_tasks, ml_tasks  # noqa

# Registrar tarefas
celery_app.tasks.register(asset_tasks.fetch_and_store_assets)
celery_app.tasks.register(asset_tasks.update_asset_prices)
celery_app.tasks.register(signal_tasks.generate_signals_for_assets)
celery_app.tasks.register(ml_tasks.train_models)
celery_app.tasks.register(ml_tasks.evaluate_models)

# Configurar inicialização
@celery_app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    """
    Configura tarefas periódicas para execução automática.
    
    Args:
        sender: Instância do Celery
        **kwargs: Argumentos adicionais
    """
    # Atualização de ativos - diariamente às 01:00
    sender.add_periodic_task(
        settings.ASSETS_REFRESH_INTERVAL,
        asset_tasks.fetch_and_store_assets.s(),
        name="fetch_assets_daily",
    )
    
    # Atualização de preços - a cada 1 hora
    sender.add_periodic_task(
        settings.DATA_COLLECTION_INTERVAL,
        asset_tasks.update_asset_prices.s(),
        name="update_prices_hourly",
    )
    
    # Geração de sinais - a cada 2 horas
    sender.add_periodic_task(
        settings.DATA_COLLECTION_INTERVAL * 2,
        signal_tasks.generate_signals_for_assets.s(),
        name="generate_signals",
    )
    
    # Treinamento de modelos - semanalmente aos domingos às 03:00
    sender.add_periodic_task(
        settings.ML_MODEL_UPDATE_INTERVAL,
        ml_tasks.train_models.s(),
        name="train_models_weekly",
    )
    
    # Avaliação de modelos - diariamente às 04:00
    sender.add_periodic_task(
        settings.ASSETS_REFRESH_INTERVAL,
        ml_tasks.evaluate_models.s(),
        name="evaluate_models_daily",
    )


@celery_app.task
def debug_task() -> Dict[str, Any]:
    """
    Tarefa de debug para testar o funcionamento do Celery.
    
    Returns:
        Dict com informações de status
    """
    logger.info("Debug task executada com sucesso")
    return {
        "status": "success",
        "message": "Celery is working!",
        "worker_info": {
            "hostname": os.uname().nodename,
            "pid": os.getpid(),
        },
    }


if __name__ == "__main__":
    celery_app.start() 