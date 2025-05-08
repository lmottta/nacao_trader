"""
Tarefas Celery para processamento de ativos.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

from celery import Task
from loguru import logger

from src.collectors.finnhub_collector import FinnhubCollector
from src.models.asset import AssetType
from src.tasks.worker import celery_app


class BaseTask(Task):
    """Classe base para tarefas Celery com suporte a retry."""
    
    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3, "countdown": 60}
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True


@celery_app.task(base=BaseTask, name="fetch_and_store_assets")
def fetch_and_store_assets() -> Dict[str, Any]:
    """
    Tarefa para buscar e armazenar ativos disponíveis.
    
    Returns:
        Dict com estatísticas da operação
    """
    try:
        logger.info("Iniciando tarefa fetch_and_store_assets")
        collector = FinnhubCollector()
        
        # Transformar em async/await com asyncio.run()
        import asyncio
        total, new, updated = asyncio.run(collector.fetch_and_store_assets())
        
        result = {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "stats": {
                "total_assets": total,
                "new_assets": new,
                "updated_assets": updated,
            }
        }
        
        logger.success(f"Tarefa fetch_and_store_assets concluída: {result}")
        return result
    except Exception as e:
        logger.error(f"Erro na tarefa fetch_and_store_assets: {e}")
        raise


@celery_app.task(base=BaseTask, name="update_asset_prices")
def update_asset_prices(asset_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Tarefa para atualizar preços dos ativos.
    
    Args:
        asset_type: Tipo de ativo para filtrar (opcional)
        
    Returns:
        Dict com estatísticas da operação
    """
    try:
        logger.info(f"Iniciando tarefa update_asset_prices para tipo: {asset_type}")
        collector = FinnhubCollector()
        
        # Converter string para enum se fornecido
        asset_type_enum = None
        if asset_type:
            try:
                asset_type_enum = AssetType(asset_type)
            except ValueError:
                logger.warning(f"Tipo de ativo inválido: {asset_type}")
        
        # Transformar em async/await com asyncio.run()
        import asyncio
        result = asyncio.run(collector.update_asset_prices(asset_type_enum))
        
        logger.success(f"Tarefa update_asset_prices concluída: {result}")
        return result
    except Exception as e:
        logger.error(f"Erro na tarefa update_asset_prices: {e}")
        raise


@celery_app.task(base=BaseTask, name="update_asset_details")
def update_asset_details(asset_id: str) -> Dict[str, Any]:
    """
    Tarefa para atualizar detalhes de um ativo específico.
    
    Args:
        asset_id: ID do ativo
        
    Returns:
        Dict com informações atualizadas
    """
    try:
        logger.info(f"Iniciando tarefa update_asset_details para asset_id: {asset_id}")
        
        # Implementação futura - buscar perfil da empresa, dados fundamentais, etc.
        # Por enquanto, apenas simula uma atualização
        
        result = {
            "status": "success",
            "asset_id": asset_id,
            "timestamp": datetime.now().isoformat(),
            "message": "Detalhes do ativo atualizados com sucesso",
        }
        
        logger.success(f"Tarefa update_asset_details concluída: {result}")
        return result
    except Exception as e:
        logger.error(f"Erro na tarefa update_asset_details: {e}")
        raise


@celery_app.task(base=BaseTask, name="fetch_historical_data")
def fetch_historical_data(
    asset_id: str,
    symbol: str,
    timeframe: str = "D",
    days: int = 365
) -> Dict[str, Any]:
    """
    Tarefa para buscar dados históricos de um ativo.
    
    Args:
        asset_id: ID do ativo
        symbol: Símbolo do ativo
        timeframe: Timeframe para os dados (1, 5, 15, 30, 60, D, W, M)
        days: Número de dias para buscar histórico
        
    Returns:
        Dict com dados históricos
    """
    try:
        logger.info(f"Iniciando tarefa fetch_historical_data para {symbol}, timeframe: {timeframe}")
        collector = FinnhubCollector()
        
        # Calcular timestamps
        import time
        from datetime import datetime, timedelta
        
        end_time = int(time.time())
        start_time = int((datetime.now() - timedelta(days=days)).timestamp())
        
        # Transformar em async/await com asyncio.run()
        import asyncio
        
        # Determinar o tipo de ativo e buscar candles adequados
        # Esta lógica seria mais robusta em uma implementação real
        candles = {}
        if symbol.startswith("BINANCE:"):
            candles = asyncio.run(collector.fetch_crypto_candles(
                symbol, timeframe, start_time, end_time
            ))
        elif ":" in symbol:  # Provavelmente forex
            candles = asyncio.run(collector.fetch_forex_candles(
                symbol, timeframe, start_time, end_time
            ))
        else:  # Provavelmente ação
            candles = asyncio.run(collector.fetch_stock_candles(
                symbol, timeframe, start_time, end_time
            ))
        
        # Se não houver dados ou erro
        if not candles or "s" in candles and candles["s"] != "ok":
            logger.warning(f"Sem dados históricos para {symbol}: {candles}")
            return {
                "status": "error",
                "asset_id": asset_id,
                "symbol": symbol,
                "timestamp": datetime.now().isoformat(),
                "message": f"Sem dados históricos disponíveis: {candles.get('s', 'unknown error')}",
            }
        
        # Armazenar dados no banco (implementação futura)
        # Por enquanto, apenas retorna estatísticas
        
        result = {
            "status": "success",
            "asset_id": asset_id,
            "symbol": symbol,
            "timeframe": timeframe,
            "days": days,
            "timestamp": datetime.now().isoformat(),
            "data_points": len(candles.get("c", [])),
            "date_range": {
                "start": datetime.fromtimestamp(start_time).isoformat(),
                "end": datetime.fromtimestamp(end_time).isoformat(),
            },
        }
        
        logger.success(f"Tarefa fetch_historical_data concluída para {symbol}")
        return result
    except Exception as e:
        logger.error(f"Erro na tarefa fetch_historical_data para {symbol}: {e}")
        raise 