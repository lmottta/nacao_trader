#!/usr/bin/env python
"""
Script para executar o coletor de dados em tempo real.

Este script inicia o coletor de dados de mercado em tempo real, que monitora
continuamente todos os ativos configurados, obtendo e armazenando dados
do Yahoo Finance.
"""
import os
import sys
import asyncio
import logging
from pathlib import Path

# Adicionar diretório raiz ao PYTHONPATH para importação relativa
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

try:
    from src.collectors.realtime_market_data import run_realtime_collector
    from src.utils.config import settings
    from src.utils.logger import setup_logger
except ImportError as e:
    print(f"Erro ao importar módulos: {e}")
    print("Verifique se está executando o script do diretório correto.")
    sys.exit(1)

def main():
    """
    Função principal para iniciar o coletor de dados em tempo real.
    """
    # Configurar logging
    log_dir = ROOT_DIR / "data" / "realtime" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / "realtime_collector.log"
    logger = setup_logger("realtime_collector", log_file, level=settings.LOG_LEVEL)
    logger.info("--- INICIANDO TESTE DE LOGGING ---")
    
    # Banner
    print("=" * 80)
    print("Iniciando Coletor de Dados em Tempo Real - Nação Trader")
    print(f"Log Level: {settings.LOG_LEVEL}")
    print(f"Intervalo de Coleta: 60 segundos")
    print("=" * 80)
    
    # Criar diretório de dados
    data_dir = ROOT_DIR / "data" / "realtime"
    data_dir.mkdir(exist_ok=True, parents=True)
    
    # Executar coletor assíncrono
    try:
        asyncio.run(run_realtime_collector())
    except KeyboardInterrupt:
        print("\nProcesso interrompido pelo usuário.")
        print("Coletor encerrado com sucesso.")
    except Exception as e:
        print(f"\nERRO FATAL: {e}")
        logging.critical(f"Erro fatal: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()