#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script para forçar a geração de novos sinais com o formato correto de indicadores técnicos.
"""

import os
import sys
import asyncio
import random
from datetime import datetime
from typing import List, Dict, Any

from dotenv import load_dotenv
from supabase import create_client, Client
from loguru import logger

# Configurar logger
logger.remove()
logger.add(sys.stdout, level="INFO", colorize=True)

# Carregar variáveis de ambiente
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
dotenv_path = os.path.join(ROOT_DIR, '.env')
load_dotenv(dotenv_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    logger.error("Variáveis de ambiente SUPABASE_URL e SUPABASE_SERVICE_KEY não encontradas")
    sys.exit(1)

# Conectar ao Supabase
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    logger.info("Conectado ao Supabase com sucesso")
except Exception as e:
    logger.error(f"Erro ao conectar ao Supabase: {e}")
    sys.exit(1)

async def get_assets() -> List[Dict[str, Any]]:
    """Obtém ativos do Supabase para gerar sinais."""
    try:
        response = supabase.table("assets").select("*").limit(5).execute()
        assets = response.data
        if not assets:
            # Criar ativos de fallback se não existirem
            assets = [
                {"id": "fallback1", "symbol": "EURUSD", "name": "Euro/USD", "asset_type": "forex", "last_price": 1.08},
                {"id": "fallback2", "symbol": "BTCUSD", "name": "Bitcoin/USD", "asset_type": "crypto", "last_price": 62500},
                {"id": "fallback3", "symbol": "AAPL", "name": "Apple Inc.", "asset_type": "stock", "last_price": 175.50},
            ]
        logger.info(f"Obtidos {len(assets)} ativos para geração de sinais")
        return assets
    except Exception as e:
        logger.error(f"Erro ao obter ativos: {e}")
        return []

async def create_signal_with_format(asset: Dict[str, Any]) -> Dict[str, Any]:
    """Cria um sinal com o formato correto de indicadores técnicos."""
    try:
        now = datetime.now()
        asset_id = asset.get("id")
        asset_symbol = asset.get("symbol")
        asset_type = asset.get("asset_type", "stock")
        last_price = asset.get("last_price", 100.0)
        
        # Gerar direção aleatória
        direction = random.choice(["CALL", "PUT"])
        
        # Gerar valores de indicadores técnicos
        rsi_value = random.uniform(20, 80)
        macd_value = random.uniform(-2, 2)
        macd_signal = random.uniform(-2, 2)
        macd_histogram = random.uniform(-1, 1)
        
        bollinger_middle = float(last_price)
        bollinger_upper = float(last_price) * 1.02
        bollinger_lower = float(last_price) * 0.98
        
        # Estruturar indicadores no formato correto
        indicators = {
            "rsi": rsi_value,
            "macd": {
                "value": macd_value,
                "signal": macd_signal,
                "histogram": macd_histogram
            },
            "bollinger": {
                "upper": bollinger_upper,
                "middle": bollinger_middle,
                "lower": bollinger_lower
            }
        }
        
        # Criar objeto do sinal
        signal_data = {
            "asset_id": asset_id,
            "asset_symbol": asset_symbol,
            "direction": direction,
            "confidence": random.uniform(0.60, 0.95),
            "accuracy": random.uniform(0.60, 0.95),
            "generated_at": now.isoformat(),
            "valid_until": datetime.fromtimestamp(now.timestamp() + 86400).isoformat(),  # 24h
            "status": "active",
            "timeframe": "1d",
            "source": "TECHNICAL_ANALYSIS",
            "indicators": indicators,
            "notes": f"Sinal de teste com formato padronizado de indicadores. RSI: {rsi_value:.2f}, MACD: {macd_value:.2f}/{macd_signal:.2f}",
            "metadata": {
                "is_otc": False,
                "entry_times": [
                    datetime.fromtimestamp(now.timestamp() + 3600).isoformat(),
                    datetime.fromtimestamp(now.timestamp() + 7200).isoformat(),
                ],
                "recommended_price": last_price,
                "target_price": last_price * (1.01 if direction == "CALL" else 0.99),
                "created_by": "force_new_signal.py"
            }
        }
        
        # Inserir no Supabase
        response = supabase.table("signals").insert(signal_data).execute()
        
        if response.data:
            logger.success(f"Sinal criado para {asset_symbol}: {direction}")
            return {"success": True, "signal": response.data[0]}
        else:
            logger.error(f"Erro ao criar sinal para {asset_symbol}")
            return {"success": False, "error": "Sem dados retornados"}
    
    except Exception as e:
        logger.error(f"Erro ao criar sinal: {e}")
        return {"success": False, "error": str(e)}

async def main():
    """Função principal do script."""
    logger.info("=== Iniciando geração forçada de sinais ===")
    
    try:
        # Obter ativos
        assets = await get_assets()
        
        if not assets:
            logger.error("Nenhum ativo encontrado para gerar sinais")
            return {"status": "error", "message": "Nenhum ativo disponível"}
        
        # Criar 3 sinais
        results = []
        
        for i in range(min(3, len(assets))):
            asset = assets[i]
            result = await create_signal_with_format(asset)
            results.append(result)
        
        successful = len([r for r in results if r.get("success", False)])
        failed = len(results) - successful
        
        logger.info(f"Geração concluída: {successful} sinais gerados, {failed} falhas")
        logger.info("=== Geração forçada de sinais concluída ===")
        
        return {
            "status": "success",
            "total": len(results),
            "successful": successful,
            "failed": failed,
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Erro não tratado: {e}")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    result = asyncio.run(main())
    print(result) 