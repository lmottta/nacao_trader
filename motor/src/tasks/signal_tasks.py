"""
Tarefas Celery para geração e processamento de sinais.
"""
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union

from celery import Task
from loguru import logger

from src.models.signal import (
    SignalDirection,
    SignalTimeframe,
    SignalSource,
    SignalStatus,
)
from src.processors.signal_generator import generate_signal
from src.tasks.worker import celery_app
from src.utils.config import settings
from src.utils.supabase_client import SupabaseHelper


class BaseTask(Task):
    """Classe base para tarefas Celery com suporte a retry."""
    
    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3, "countdown": 60}
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True


@celery_app.task(base=BaseTask, name="generate_signals_for_assets")
def generate_signals_for_assets(
    asset_ids: Optional[List[str]] = None,
    timeframe: str = "1d",
    use_ml: bool = True,
) -> Dict[str, Any]:
    """
    Tarefa para gerar sinais para múltiplos ativos.
    
    Args:
        asset_ids: Lista de IDs de ativos (opcional, se não for fornecido, gera para todos)
        timeframe: Timeframe para os sinais
        use_ml: Se deve usar modelos de ML ou apenas análise técnica
        
    Returns:
        Dict com resultados da geração de sinais
    """
    try:
        logger.info(f"Iniciando geração de sinais para {len(asset_ids) if asset_ids else 'todos'} ativos")
        
        # Se asset_ids não for fornecido, buscar todos os ativos do banco
        # Para demonstração, usaremos uma lista fixa de IDs
        if not asset_ids:
            asset_ids = [f"{i}" for i in range(1, 11)]  # 10 ativos para demonstração
        
        signals_generated = []
        errors = []
        
        # Gerar sinais para cada ativo
        for asset_id in asset_ids:
            try:
                # Em uma implementação real, buscaríamos mais dados sobre o ativo
                # e personalizaríamos a geração de sinais
                
                signal = generate_signal(
                    asset_id=asset_id,
                    timeframe=timeframe,
                    lookback_periods=100,
                )
                
                # Em uma implementação real, armazenaríamos o sinal no Supabase
                signals_generated.append(signal)
                
                logger.info(f"Sinal gerado para ativo {asset_id}: {signal['direction']} com confiança {signal['confidence']}")
            except Exception as e:
                logger.error(f"Erro ao gerar sinal para ativo {asset_id}: {e}")
                errors.append({
                    "asset_id": asset_id,
                    "error": str(e)
                })
        
        result = {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "signals_generated_count": len(signals_generated),
            "errors_count": len(errors),
            "signals": signals_generated,
            "errors": errors,
        }
        
        logger.success(f"Geração de sinais concluída: {len(signals_generated)} sinais gerados, {len(errors)} erros")
        return result
    except Exception as e:
        logger.error(f"Erro na tarefa generate_signals_for_assets: {e}")
        raise


@celery_app.task(base=BaseTask, name="process_expired_signals")
def process_expired_signals() -> Dict[str, Any]:
    """
    Tarefa para processar sinais expirados e atualizar seus status.
    
    Returns:
        Dict com resultados do processamento
    """
    try:
        logger.info("Iniciando processamento de sinais expirados")
        
        # Na implementação real, buscaríamos sinais ativos no Supabase
        # e verificaríamos quais já expiraram
        
        # Para demonstração, simulamos o processamento
        now = datetime.now()
        
        # Configurar conexão com Supabase
        supabase = SupabaseHelper()
        
        # Buscar sinais ativos que já expiraram
        # Em uma implementação real, usaríamos uma consulta SQL mais eficiente
        import asyncio
        signals_response = asyncio.run(supabase.get_signals(
            signal_type=None, 
            min_confidence=0.0
        ))
        
        signals = signals_response.get("data", [])
        
        # Filtrar sinais expirados mas ainda ativos
        expired_signals = []
        for signal in signals:
            if signal.get("status") == SignalStatus.ACTIVE.value:
                valid_until = datetime.fromisoformat(signal.get("valid_until").replace("Z", "+00:00"))
                if valid_until < now:
                    expired_signals.append(signal)
        
        # Atualizar sinais expirados
        updated_signals = []
        for signal in expired_signals:
            try:
                # Atualizar status no Supabase
                updated = asyncio.run(supabase.update_signal(
                    signal_id=signal["id"],
                    signal_data={"status": SignalStatus.EXPIRED.value}
                ))
                updated_signals.append(updated)
                
                logger.info(f"Sinal {signal['id']} marcado como expirado")
            except Exception as update_error:
                logger.error(f"Erro ao atualizar sinal {signal['id']}: {update_error}")
        
        result = {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "expired_signals_count": len(expired_signals),
            "updated_signals_count": len(updated_signals),
        }
        
        logger.success(f"Processamento de sinais expirados concluído: {len(updated_signals)} sinais atualizados")
        return result
    except Exception as e:
        logger.error(f"Erro na tarefa process_expired_signals: {e}")
        raise


@celery_app.task(base=BaseTask, name="evaluate_signal_performance")
def evaluate_signal_performance(
    days_back: int = 7
) -> Dict[str, Any]:
    """
    Tarefa para avaliar o desempenho histórico dos sinais.
    
    Args:
        days_back: Número de dias para avaliar
        
    Returns:
        Dict com resultados da avaliação
    """
    try:
        logger.info(f"Iniciando avaliação de desempenho de sinais dos últimos {days_back} dias")
        
        # Na implementação real, buscaríamos sinais completos/expirados no Supabase
        # e verificaríamos se acertaram a direção do mercado
        
        # Para demonstração, geramos resultados simulados
        
        # Estatísticas gerais
        signals_count = 100  # Simulação
        hit_rate = 0.62  # 62% de acerto
        
        # Estatísticas por tipo de sinal
        call_signals = 55
        call_hits = int(call_signals * 0.65)  # 65% de acerto em CALL
        
        put_signals = 45
        put_hits = int(put_signals * 0.58)  # 58% de acerto em PUT
        
        # Estatísticas por fonte
        sources = {
            SignalSource.TECHNICAL.value: {"count": 40, "hits": 22},
            SignalSource.ML_BASIC.value: {"count": 30, "hits": 18},
            SignalSource.ML_ADVANCED.value: {"count": 20, "hits": 14},
            SignalSource.ENSEMBLE.value: {"count": 10, "hits": 8},
        }
        
        # Estatísticas por faixa de confiança
        confidence_ranges = {
            "0.5-0.6": {"count": 20, "hits": 10},
            "0.6-0.7": {"count": 30, "hits": 16},
            "0.7-0.8": {"count": 30, "hits": 20},
            "0.8-0.9": {"count": 15, "hits": 12},
            "0.9-1.0": {"count": 5, "hits": 4},
        }
        
        # Calcular tendências
        # Em uma implementação real, calcularíamos baseado em dados históricos reais
        trend = {
            "daily_hit_rates": [
                {"date": (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d"), 
                 "hit_rate": round(0.5 + 0.02 * i, 2)}
                for i in range(days_back)
            ],
            "weekly_moving_avg": round(0.5 + 0.02 * (days_back // 2), 2),
            "monthly_moving_avg": 0.61,
        }
        
        result = {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "period": f"últimos {days_back} dias",
            "overview": {
                "signals_count": signals_count,
                "hit_rate": hit_rate,
                "hits": int(signals_count * hit_rate),
                "misses": int(signals_count * (1 - hit_rate)),
            },
            "by_direction": {
                "call": {
                    "count": call_signals,
                    "hits": call_hits,
                    "hit_rate": call_hits / call_signals,
                },
                "put": {
                    "count": put_signals,
                    "hits": put_hits,
                    "hit_rate": put_hits / put_signals,
                },
            },
            "by_source": {
                source: {
                    "count": data["count"],
                    "hits": data["hits"],
                    "hit_rate": data["hits"] / data["count"] if data["count"] > 0 else 0,
                }
                for source, data in sources.items()
            },
            "by_confidence": {
                range_: {
                    "count": data["count"],
                    "hits": data["hits"],
                    "hit_rate": data["hits"] / data["count"] if data["count"] > 0 else 0,
                }
                for range_, data in confidence_ranges.items()
            },
            "trends": trend,
        }
        
        # Em uma implementação real, armazenaríamos esta avaliação no Supabase
        
        logger.success(f"Avaliação de desempenho de sinais concluída: {hit_rate*100:.1f}% de acerto geral")
        return result
    except Exception as e:
        logger.error(f"Erro na tarefa evaluate_signal_performance: {e}")
        raise 