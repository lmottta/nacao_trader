import os
import sys
import time
from apscheduler.schedulers.blocking import BlockingScheduler
from loguru import logger
from datetime import datetime

# Importa a função main do coletor
from fetch_yahoo_assets import main as fetch_assets_main

# Configuração do loguru (garante que logs vão para o mesmo arquivo do coletor)
LOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
logger.remove()
logger.add(sys.stdout, level="INFO", colorize=True, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
logger.add(os.path.join(LOG_DIR, "collector.log"), rotation="10 MB", retention="10 days", level="INFO", encoding="utf-8")

LOCK_FILE = os.path.join(LOG_DIR, "fetch_yahoo_assets.lock")


def is_locked():
    if os.path.exists(LOCK_FILE):
        # Se o lock tem mais de 1h, remove (proteção contra travamento)
        mtime = os.path.getmtime(LOCK_FILE)
        if time.time() - mtime > 3600:
            logger.warning("Lock antigo detectado. Removendo lock...")
            os.remove(LOCK_FILE)
            return False
        return True
    return False

def acquire_lock():
    with open(LOCK_FILE, 'w') as f:
        f.write(str(datetime.now()))

def release_lock():
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)

def scheduled_job():
    if is_locked():
        logger.warning("Job anterior ainda em execução. Pulando esta execução.")
        return
    try:
        acquire_lock()
        logger.info("Iniciando execução agendada do coletor de ativos...")
        fetch_assets_main()
        logger.info("Execução agendada do coletor finalizada.")
    except Exception as e:
        logger.error(f"Erro durante execução agendada: {e}")
    finally:
        release_lock()

if __name__ == "__main__":
    scheduler = BlockingScheduler()
    scheduler.add_job(scheduled_job, 'interval', minutes=5, next_run_time=datetime.now())
    logger.info("Agendador iniciado. O coletor será executado a cada 5 minutos.")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Agendador finalizado pelo usuário.") 