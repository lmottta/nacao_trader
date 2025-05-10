#!/usr/bin/env python3
"""
Script para testar diferentes formatos de indicadores técnicos no frontend.
Este script gera sinais com vários formatos de indicadores e os insere no Supabase
para verificar se o frontend está tratando-os corretamente.
"""

import os
import asyncio
import random
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# Ajustar caminhos de importação
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.utils.supabase_client import SupabaseHelper
from src.utils.logger import setup_logger

logger = setup_logger("test_indicator_formats")

# Formatos de indicadores a serem testados
INDICATOR_FORMATS = {
    "format1": {
        "rsi": 32.5,
        "macd": {
            "value": 0.32,
            "signal": 0.28,
            "histogram": 0.04
        },
        "bollinger": {
            "upper": 152.34,
            "middle": 150.21,
            "lower": 148.08
        }
    },
    "format2": {
        "rsi": 68.7,
        "macd": {
            "MACD": -0.15,
            "signal": -0.05,
            "histogram": -0.10,
            "trend": "bearish"
        },
        "bbands": {  # Nome alternativo para Bollinger
            "upper": 112.45,
            "middle": 110.20,
            "lower": 107.95,
            "width": 0.0408,
            "percentB": 0.85
        }
    },
    "format3": {
        "rsi": 49.5,
        "macd": {
            "value": 0.05,
            "signal": 0.12,
            "histogram": -0.07,
            "crossover": "none"
        },
        "bollinger": {
            "upper": 78.50,
            "middle": 75.20,
            "lower": 71.90,
        }
    },
    "missingData": {
        "rsi": None,
        "macd": {
            "value": 0.18,
            # signal está propositalmente ausente
            "histogram": 0.08
        },
        "bollinger": {
            "upper": 45.80,
            # middle está propositalmente ausente
            "lower": 40.20
        }
    },
    "edgeCases": {
        "rsi": "32.4",  # String em vez de número
        "macd": {
            "MACD": "N/A",  # Valor não numérico
            "signal": 0,     # Zero
            "histogram": -0  # Negative zero
        },
        "bollinger": None    # Indicador inteiro como None
    }
}

# Exemplo de dados de ativo para associar ao sinal
ASSET_SAMPLE = {
    "id": "aapl-stock",
    "symbol": "AAPL",
    "name": "Apple Inc.",
    "asset_type": "stock",
    "last_price": 175.45,
    "change_percent": 1.2,
    "market_status": "open"
}

async def create_test_signal(format_name: str, indicators: Dict[str, Any]) -> Dict[str, Any]:
    """Cria um sinal de teste com o formato de indicador especificado."""
    now = datetime.now()
    
    # Gerar direção e notas com base nos indicadores
    direction = "CALL" if random.random() > 0.5 else "PUT"
    
    notes = f"Sinal de teste para formato de indicadores '{format_name}'."
    if "rsi" in indicators and indicators["rsi"] is not None:
        rsi_value = indicators["rsi"]
        if isinstance(rsi_value, str):
            try:
                rsi_value = float(rsi_value)
            except ValueError:
                rsi_value = 50.0
        
        if rsi_value < 30:
            notes += " RSI em sobrevenda."
        elif rsi_value > 70:
            notes += " RSI em sobrecompra."
    
    # Estruturar dados do sinal
    signal_data = {
        "asset_id": ASSET_SAMPLE["id"],
        "direction": direction,
        "accuracy": random.randint(65, 95),
        "generated_at": now.isoformat(),
        "valid_until": (now + timedelta(hours=24)).isoformat(),
        "timeframe": "1d",
        "source": "INDICATOR_TEST",
        "notes": notes,
        "indicators": indicators,
        "details": {
            "reason": f"Sinal gerado para teste do formato '{format_name}' de indicadores técnicos.",
            "asset_name": ASSET_SAMPLE["name"],
            "asset_type": ASSET_SAMPLE["asset_type"]
        }
    }
    
    return signal_data

async def main():
    """Função principal que gera e insere sinais de teste no Supabase."""
    logger.info("Iniciando geração de sinais de teste para formatos de indicadores")
    
    # Inicializar cliente Supabase
    supabase = SupabaseHelper()
    
    # Tentar criar o ativo de exemplo se não existir
    logger.info(f"Verificando existência do ativo de teste {ASSET_SAMPLE['id']}")
    existing_asset = await supabase.get_asset_by_id(ASSET_SAMPLE["id"])
    
    if not existing_asset:
        logger.info(f"Criando ativo de teste: {ASSET_SAMPLE['symbol']}")
        await supabase.create_asset(ASSET_SAMPLE)
    else:
        logger.info(f"Ativo de teste já existe: {ASSET_SAMPLE['symbol']}")
    
    # Criar um sinal para cada formato
    for format_name, indicators in INDICATOR_FORMATS.items():
        logger.info(f"Gerando sinal para o formato: {format_name}")
        signal_data = await create_test_signal(format_name, indicators)
        
        # Inserir no Supabase
        result = await supabase.create_signal(signal_data)
        
        if result and "id" in result:
            logger.info(f"Sinal de teste criado com sucesso: {result['id']} (formato: {format_name})")
        else:
            logger.error(f"Falha ao criar sinal para formato: {format_name}")
            logger.error(f"Erro: {result}")
    
    logger.info("Finalizado teste de formatos de indicadores")

if __name__ == "__main__":
    asyncio.run(main()) 