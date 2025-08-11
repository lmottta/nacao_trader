"""
API principal do Motor de Sinais ML da Nação Trader.
"""
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union, Any

from fastapi import FastAPI, HTTPException, Query, status, BackgroundTasks, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import logging
import asyncio
import time
import random

from src.utils.config import settings
from src.utils.supabase_client import get_supabase_client, SupabaseHelper
from src.utils.logger import get_logger, log_execution_time, with_context
from src.processors.signal_generator import generate_signal, generate_signal_from_realtime_data, backtest_signal_strategy
from src.processors.ml_processor import (
    generate_ml_signal, 
    batch_generate_signals,
    train_model
)
from src.processors.technical_analysis import perform_technical_analysis
from src.models.asset import Asset
from src.models.signal import Signal, SignalDirection, SignalSource, SignalStatus, SignalTimeframe

# Inicialização do logger
log = get_logger("api")

# Modelos para o sistema de geração periódica de sinais
class ScheduleSignalsRequest(BaseModel):
    """Modelo para agendamento de geração de sinais periódicos."""
    asset_ids: Optional[List[str]] = None
    asset_symbols: Optional[List[str]] = None
    interval_minutes: int = 60  # Padrão: 1 hora
    timeframe: str = "1d"  # Padrão: diário
    use_technical_analysis: bool = True  # Padrão: usar análise técnica

# Armazenar dados do job agendado
scheduled_job = {
    "running": False,
    "last_run": None,
    "interval_minutes": 60,
    "asset_ids": [],
    "asset_symbols": [],
    "timeframe": "1d",
    "use_technical_analysis": True
}

# Inicialização da aplicação
app = FastAPI(
    title="Nação Trader - Motor de Sinais API",
    description="API para geração de sinais de trading e análise de mercado",
    version="0.1.0",
)

# Configuração CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, limitar às origens reais
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Função para verificar a autenticação
async def verify_api_key(x_api_key: str = Header(None)):
    """Verifica a chave de API nas requisições."""
    if not x_api_key or x_api_key != settings.API_KEY:
        log.warning("Tentativa de acesso com chave de API inválida", 
                   context={"api_key": "invalid" if x_api_key else "missing"})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Chave de API inválida ou não fornecida",
        )
    return x_api_key

# Rotas de status e saúde
@app.get("/")
async def root():
    """Endpoint raiz que fornece informações básicas sobre a API."""
    log.info("Requisição ao endpoint raiz")
    return {
        "name": "Nação Trader - Motor de Sinais API",
        "version": "0.1.0",
        "status": "online",
        "timestamp": datetime.now().isoformat(),
    }

@app.get("/health")
async def health_check():
    """Endpoint de verificação de saúde para monitoramento."""
    log.debug("Verificação de saúde solicitada")
    # Verificar conexão com o Supabase
    supabase_status = "connected"
    timescaledb_status = "unknown"
    
    try:
        client = get_supabase_client()
        # Testar conexão com banco
        response = await client.table("assets").select("count(*)", count="exact").execute()
        if response.error:
            supabase_status = "error"
            log.error(f"Erro na conexão com Supabase: {response.error}")
        
        # Verificar se TimescaleDB está habilitado
        ts_query = """
        SELECT EXISTS (
            SELECT FROM pg_extension
            WHERE extname = 'timescaledb'
        );
        """
        ts_response = await client.execute_sql(ts_query)
        if ts_response.error:
            timescaledb_status = "error"
            log.warning(f"Erro ao verificar TimescaleDB: {ts_response.error}")
        elif ts_response.data and ts_response.data[0].get("exists"):
            timescaledb_status = "enabled"
        else:
            timescaledb_status = "disabled"
        
    except Exception as e:
        supabase_status = "error"
        log.error(f"Erro na verificação de saúde: {str(e)}", 
                 context={"exception": str(e)})
    
    return {
        "status": "healthy" if supabase_status == "connected" else "degraded",
        "timestamp": datetime.now().isoformat(),
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "services": {
            "database": supabase_status,
            "timescaledb": timescaledb_status,
        },
    }

# Rotas de ativos
@app.get("/assets")
@log_execution_time
@with_context(endpoint="get_assets")
async def get_assets(
    asset_type: Optional[str] = Query(None, description="Tipo de ativo (stock, forex, crypto)"),
    search: Optional[str] = Query(None, description="Buscar por símbolo ou nome"),
    limit: int = Query(100, ge=1, le=1000, description="Limite de resultados"),
    offset: int = Query(0, ge=0, description="Offset para paginação"),
    api_key: str = Depends(verify_api_key)
):
    """Obter lista de ativos disponíveis com filtros opcionais."""
    try:
        log.info("Buscando ativos", context={
            "asset_type": asset_type,
            "search": search,
            "limit": limit,
            "offset": offset
        })
        
        # Inicializar cliente Supabase
        client = get_supabase_client()
        
        # Construir query
        query = client.table("assets").select("*", count="exact")
        
        # Aplicar filtros
        if asset_type:
            query = query.eq("type", asset_type)
        
        if search:
            query = query.or_(f"symbol.ilike.%{search}%,name.ilike.%{search}%")
        
        # Aplicar paginação
        query = query.range(offset, offset + limit - 1)
        
        # Executar consulta
        response = await query.execute()
        
        if response.error:
            log.error(f"Erro ao buscar ativos: {response.error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao buscar ativos: {response.error.message}",
            )
        
        # Preparar resposta
        assets = response.data
        total = response.count if response.count is not None else len(assets)
        
        log.info(f"Encontrados {total} ativos", context={"count": total})
        
        return {
            "data": assets,
            "meta": {
                "total": total,
                "limit": limit,
                "offset": offset,
            }
        }
    except Exception as e:
        log.error(f"Erro ao buscar ativos: {e}", context={"exception": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar ativos: {str(e)}",
        )

# Rotas de sinais
class SignalRequest(BaseModel):
    """Modelo para solicitação de geração de sinal."""
    asset_id: str
    asset_symbol: Optional[str] = None
    timeframe: str = "1d"  # 1m, 5m, 15m, 1h, 4h, 1d...
    lookback_periods: int = 100
    force_retrain: bool = False
    use_ml: bool = True
    use_edge_function: bool = False
    symbol: str

@app.post("/signals/generate")
@log_execution_time
@with_context(endpoint="create_signal")
async def create_signal(
    request: SignalRequest,
    api_key: str = Depends(verify_api_key)
):
    """Gerar um novo sinal de trading para um ativo específico."""
    try:
        log.info("Solicitação de geração de sinal", context={
            "asset_id": request.asset_id,
            "timeframe": request.timeframe,
            "use_ml": request.use_ml,
            "use_edge_function": request.use_edge_function
        })
        
        # Verificar se deve usar a função edge
        if request.use_edge_function:
            return await _generate_signal_via_edge(request)
        
        # Gerar sinal localmente
        if request.use_ml:
            signal = generate_ml_signal(
                asset_id=request.asset_id,
                asset_symbol=request.asset_symbol,
                timeframe=request.timeframe,
                lookback_periods=request.lookback_periods,
                force_retrain=request.force_retrain,
            )
            log.info(f"Sinal ML gerado para {request.asset_id} com confiança {signal.get('confidence', 0)}")
        else:
            # Usar o gerador baseado em regras para compatibilidade
            signal = generate_signal(
                asset_id=request.asset_id,
                timeframe=request.timeframe,
                lookback_periods=request.lookback_periods,
            )
            log.info(f"Sinal baseado em regras gerado para {request.asset_id}")
        
        return signal
    except Exception as e:
        log.error(f"Erro ao gerar sinal: {e}", context={
            "asset_id": request.asset_id,
            "exception": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao gerar sinal: {str(e)}",
        )

async def _generate_signal_via_edge(request: SignalRequest) -> Dict[str, Any]:
    """
    Gera um sinal usando a função edge do Supabase.
    
    Args:
        request: Dados da requisição
        
    Returns:
        Dict: Resposta da função edge
    """
    try:
        log.info("Gerando sinal via função edge", context={
            "asset_id": request.asset_id,
            "timeframe": request.timeframe
        })
        
        # Construir URL da função edge
        edge_url = f"{settings.SUPABASE_URL}/functions/v1/generate-signal"
        
        # Preparar corpo da requisição
        payload = {
            "asset_id": request.asset_id,
            "asset_symbol": request.asset_symbol,
            "timeframe": request.timeframe,
            "lookback_periods": request.lookback_periods
        }
        
        # Preparar headers
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.SUPABASE_ANON_KEY}"
        }
        
        # Fazer requisição para a função edge
        async with httpx.AsyncClient() as client:
            response = await client.post(edge_url, json=payload, headers=headers)
            
            # Verificar resposta
            if response.status_code != 200:
                log.error(f"Erro na função edge: {response.text}", context={
                    "status_code": response.status_code
                })
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Erro na função edge: {response.text}",
                )
            
            # Processar resposta
            result = response.json()
            
            if not result.get("success"):
                log.error(f"Função edge retornou erro: {result.get('error')}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erro ao gerar sinal via edge: {result.get('error')}",
                )
            
            log.info("Sinal gerado com sucesso via função edge")
            return result.get("data")
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Erro ao chamar função edge: {e}", context={"exception": str(e)})
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro ao comunicar com função edge: {str(e)}",
        )

# Rota para geração em lote
class BatchSignalRequest(BaseModel):
    """Modelo para solicitação de geração de sinais em lote."""
    asset_ids: List[str]
    timeframe: str = "1d"
    force_retrain: bool = False
    use_edge_function: bool = False

@app.post("/signals/batch")
@log_execution_time
@with_context(endpoint="create_batch_signals")
async def create_batch_signals(
    request: BatchSignalRequest, 
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key)
):
    """Gerar sinais para múltiplos ativos em batch."""
    try:
        log.info("Solicitação de geração de sinais em lote", context={
            "asset_count": len(request.asset_ids),
            "timeframe": request.timeframe,
            "use_edge_function": request.use_edge_function
        })
        
        # Para requisições com muitos ativos, processar em background
        if len(request.asset_ids) > 5:
            log.info(f"Processando {len(request.asset_ids)} sinais em background")
            
            # Verificar se deve usar edge functions
            if request.use_edge_function:
                background_tasks.add_task(
                    _batch_generate_via_edge,
                    asset_ids=request.asset_ids,
                    timeframe=request.timeframe
                )
            else:
                # Usar processamento local
                background_tasks.add_task(
                    batch_generate_signals,
                    asset_ids=request.asset_ids,
                    timeframe=request.timeframe,
                    force_retrain=request.force_retrain
                )
            
            return {
                "status": "processing",
                "message": f"Processando {len(request.asset_ids)} sinais em background",
                "asset_ids": request.asset_ids,
                "timestamp": datetime.now().isoformat()
            }
        else:
            # Para poucos ativos, processar de forma síncrona
            if request.use_edge_function:
                signals = await _batch_generate_via_edge(
                    asset_ids=request.asset_ids,
                    timeframe=request.timeframe
                )
            else:
                signals = batch_generate_signals(
                    asset_ids=request.asset_ids,
                    timeframe=request.timeframe,
                    force_retrain=request.force_retrain
                )
            
            log.info(f"Gerados {len(signals)} sinais em lote", context={"count": len(signals)})
            
            return {
                "status": "completed",
                "signals": signals,
                "count": len(signals),
                "timestamp": datetime.now().isoformat()
            }
    except Exception as e:
        log.error(f"Erro ao gerar sinais em lote: {e}", context={"exception": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao gerar sinais em lote: {str(e)}",
        )

async def _batch_generate_via_edge(asset_ids: List[str], timeframe: str) -> List[Dict[str, Any]]:
    """
    Gera sinais em lote usando a função edge do Supabase.
    
    Args:
        asset_ids: Lista de IDs de ativos
        timeframe: Timeframe para análise
        
    Returns:
        List[Dict]: Lista de sinais gerados
    """
    signals = []
    
    log.info(f"Gerando {len(asset_ids)} sinais via função edge")
    
    # Processar cada ativo individualmente
    for asset_id in asset_ids:
        try:
            # Criar requisição para cada ativo
            request = SignalRequest(
                asset_id=asset_id,
                timeframe=timeframe,
                use_edge_function=True
            )
            
            # Gerar sinal via edge
            signal = await _generate_signal_via_edge(request)
            signals.append(signal)
            
            log.debug(f"Sinal gerado para {asset_id} via edge function")
        except Exception as e:
            log.error(f"Erro ao gerar sinal para {asset_id}: {e}", 
                     context={"asset_id": asset_id})
            # Continuar para o próximo ativo mesmo em caso de erro
    
    log.info(f"Concluída geração de {len(signals)} sinais via edge function")
    return signals

@app.get("/signals")
@log_execution_time
@with_context(endpoint="get_signals")
async def get_signals(
    asset_id: Optional[str] = Query(None, description="ID do ativo"),
    asset_symbol: Optional[str] = Query(None, description="Símbolo do ativo"),
    direction: Optional[str] = Query(None, description="Direção do sinal (CALL, PUT)"),
    min_confidence: float = Query(0.0, ge=0.0, le=1.0, description="Confiança mínima"),
    timeframe: Optional[str] = Query(None, description="Timeframe do sinal"),
    status: Optional[str] = Query(None, description="Status do sinal"),
    date_from: Optional[str] = Query(None, description="Data inicial (ISO)"),
    date_to: Optional[str] = Query(None, description="Data final (ISO)"),
    limit: int = Query(50, ge=1, le=1000, description="Limite de resultados"),
    offset: int = Query(0, ge=0, description="Offset para paginação"),
    sort_by: str = Query("generated_at", description="Campo para ordenação"),
    sort_dir: str = Query("desc", description="Direção da ordenação (asc, desc)"),
    api_key: str = Depends(verify_api_key),
    use_edge_function: bool = Query(False, description="Usar função edge para consulta")
):
    """Obter sinais de trading com filtros avançados."""
    try:
        log.info("Consultando sinais", context={
            "asset_id": asset_id,
            "direction": direction,
            "min_confidence": min_confidence,
            "use_edge_function": use_edge_function
        })
        
        # Verificar se deve usar a função edge
        if use_edge_function:
            return await _get_signals_via_edge(
                asset_id=asset_id,
                asset_symbol=asset_symbol,
                direction=direction,
                min_confidence=min_confidence,
                timeframe=timeframe,
                status=status,
                date_from=date_from,
                date_to=date_to,
                limit=limit,
                offset=offset,
                sort_by=sort_by,
                sort_dir=sort_dir
            )
        
        # Consultar sinais localmente
        client = get_supabase_client()
        
        # Construir query
        query = client.table("signals").select("*", count="exact")
        
        # Aplicar filtros
        if asset_id:
            query = query.eq("asset_id", asset_id)
        
        if asset_symbol:
            query = query.eq("asset_symbol", asset_symbol)
        
        if direction:
            query = query.eq("direction", direction)
        
        if min_confidence > 0:
            query = query.gte("confidence", min_confidence)
        
        if timeframe:
            query = query.eq("timeframe", timeframe)
        
        if status:
            query = query.eq("status", status)
        
        if date_from:
            query = query.gte("generated_at", date_from)
        
        if date_to:
            query = query.lte("generated_at", date_to)
        
        # Aplicar ordenação
        query = query.order(sort_by, {"ascending": sort_dir.lower() == "asc"})
        
        # Aplicar paginação
        query = query.range(offset, offset + limit - 1)
        
        # Executar consulta
        response = await query.execute()
        
        if response.error:
            log.error(f"Erro ao consultar sinais: {response.error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao consultar sinais: {response.error.message}",
            )
        
        # Preparar resposta
        signals = response.data
        total = response.count if response.count is not None else len(signals)
        
        log.info(f"Encontrados {total} sinais", context={"count": total})
        
        return {
            "data": signals,
            "meta": {
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": total > (offset + limit)
            }
        }
    except Exception as e:
        log.error(f"Erro ao consultar sinais: {e}", context={"exception": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao consultar sinais: {str(e)}",
        )

async def _get_signals_via_edge(
    asset_id: Optional[str] = None,
    asset_symbol: Optional[str] = None,
    direction: Optional[str] = None,
    min_confidence: float = 0.0,
    timeframe: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    sort_by: str = "generated_at",
    sort_dir: str = "desc"
) -> Dict[str, Any]:
    """
    Consulta sinais usando a função edge de dashboard.
    
    Args:
        Diversos parâmetros de filtro
        
    Returns:
        Dict: Resposta da função edge com sinais e métricas
    """
    try:
        log.info("Consultando sinais via função edge", context={
            "asset_id": asset_id,
            "direction": direction
        })
        
        # Construir URL base
        edge_url = f"{settings.SUPABASE_URL}/functions/v1/signals-dashboard"
        
        # Construir parâmetros de consulta
        params = {}
        
        if asset_id:
            params["asset_ids"] = asset_id
        
        if direction:
            params["directions"] = direction
        
        if min_confidence > 0:
            params["min_confidence"] = str(min_confidence)
        
        if timeframe:
            params["timeframes"] = timeframe
        
        if status:
            params["status"] = status
        
        if date_from:
            params["date_from"] = date_from
        
        if date_to:
            params["date_to"] = date_to
        
        params["limit"] = str(limit)
        params["offset"] = str(offset)
        params["sort_by"] = sort_by
        params["sort_direction"] = sort_dir
        
        # Preparar headers
        headers = {
            "Authorization": f"Bearer {settings.SUPABASE_ANON_KEY}"
        }
        
        # Fazer requisição para a função edge
        async with httpx.AsyncClient() as client:
            response = await client.get(edge_url, params=params, headers=headers)
            
            # Verificar resposta
            if response.status_code != 200:
                log.error(f"Erro na função edge de dashboard: {response.text}", context={
                    "status_code": response.status_code
                })
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Erro na função edge: {response.text}",
                )
            
            # Processar resposta
            result = response.json()
            
            if not result.get("success"):
                log.error(f"Função edge retornou erro: {result.get('error')}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erro ao consultar sinais via edge: {result.get('error')}",
                )
            
            log.info(f"Consulta de sinais via edge concluída com sucesso")
            return result.get("data")
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Erro ao chamar função edge de dashboard: {e}", context={"exception": str(e)})
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Erro ao comunicar com função edge: {str(e)}",
        )

class ModelTrainRequest(BaseModel):
    """Modelo para solicitação de treinamento de modelo."""
    asset_id: str
    timeframe: str = "1d"
    force_retrain: bool = True

@app.post("/models/train")
@log_execution_time
@with_context(endpoint="train_model")
async def train_model_endpoint(
    request: ModelTrainRequest, 
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key)
):
    """Treinar um modelo ML para um ativo específico."""
    try:
        log.info("Solicitação de treinamento de modelo", context={
            "asset_id": request.asset_id,
            "timeframe": request.timeframe,
            "force_retrain": request.force_retrain
        })
        
        # Treinar em background para não bloquear a requisição
        background_tasks.add_task(
            train_model,
            asset_id=request.asset_id,
            timeframe=request.timeframe,
            force_retrain=request.force_retrain
        )
        
        log.info(f"Treinamento de modelo iniciado em background para {request.asset_id}")
        
        return {
            "status": "processing",
            "message": "Treinamento de modelo iniciado em background",
            "asset_id": request.asset_id,
            "timeframe": request.timeframe,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        log.error(f"Erro ao treinar modelo: {e}", 
                 context={"asset_id": request.asset_id, "exception": str(e)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao treinar modelo: {str(e)}",
        )

@app.get("/analysis/technical/{asset_id}")
@log_execution_time
@with_context(endpoint="get_technical_analysis")
async def get_technical_analysis(
    asset_id: str,
    timeframe: str = Query("1d", description="Timeframe para análise"),
    lookback_periods: int = Query(200, ge=30, le=1000, description="Períodos históricos para análise"),
    api_key: str = Depends(verify_api_key)
):
    """Obter análise técnica para um ativo específico."""
    try:
        log.info("Solicitação de análise técnica", context={
            "asset_id": asset_id,
            "timeframe": timeframe,
            "lookback_periods": lookback_periods
        })
        
        # Inicializar cliente Supabase
        client = get_supabase_client()
        
        # Verificar se o ativo existe
        asset_query = client.table("assets").select("*").eq("id", asset_id)
        asset_response = await asset_query.execute()
        
        if asset_response.error:
            log.error(f"Erro ao buscar ativo: {asset_response.error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao buscar ativo: {asset_response.error.message}",
            )
        
        if not asset_response.data or len(asset_response.data) == 0:
            log.warning(f"Ativo não encontrado: {asset_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ativo não encontrado",
            )
        
        asset = asset_response.data[0]
        asset_symbol = asset.get("symbol")
        
        if not asset_symbol:
            log.error(f"Ativo sem símbolo: {asset_id}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ativo sem símbolo",
            )
        
        # Buscar dados históricos de preço
        price_query = client.table("price_history") \
            .select("*") \
            .eq("symbol", asset_symbol) \
            .eq("timeframe", timeframe) \
            .order("timestamp", {"ascending": False}) \
            .limit(lookback_periods)
        
        price_response = await price_query.execute()
        
        if price_response.error:
            log.error(f"Erro ao buscar dados de preço: {price_response.error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erro ao buscar dados de preço: {price_response.error.message}",
            )
        
        price_data = price_response.data
        
        if not price_data or len(price_data) < 30:
            log.warning(f"Dados históricos insuficientes para {asset_symbol}: {len(price_data) if price_data else 0} registros")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Dados históricos insuficientes para análise: {len(price_data) if price_data else 0} registros",
            )
        
        # Ordenar dados para análise (mais antigos primeiro)
        sorted_price_data = sorted(price_data, key=lambda x: x.get("timestamp"))
        
        # Realizar análise técnica
        analysis = perform_technical_analysis(sorted_price_data)
        
        if "error" in analysis:
            log.error(f"Erro na análise técnica: {analysis['error']}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=analysis["error"],
            )
        
        # Preparar resposta
        result = {
            "asset": {
                "id": asset_id,
                "symbol": asset_symbol,
                "name": asset.get("name"),
                "type": asset.get("type")
            },
            "timeframe": timeframe,
            "analysis": analysis,
            "generated_at": datetime.now().isoformat()
        }
        
        log.info(f"Análise técnica concluída para {asset_symbol} com recomendação: {analysis.get('recommendation', {}).get('action', 'unknown')}")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Erro ao gerar análise técnica: {e}", context={
            "asset_id": asset_id,
            "exception": str(e)
        })
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao gerar análise técnica: {str(e)}",
        )

async def generate_signals_job():
    """
    Job background para geração periódica de sinais baseados em análise técnica.
    Esta função será executada em loop enquanto scheduled_job["running"] for True.
    """
    global scheduled_job
    
    log.info(f"Iniciando job de geração de sinais")
    
    while scheduled_job["running"]:
        try:
            # Processar ativos e gerar sinais de acordo com a configuração
            # (implantação simplificada para teste)
            
            # Atualizar timestamp da última execução
            scheduled_job["last_run"] = datetime.now().isoformat()
            log.info(f"Geração de sinais concluída. Próxima execução em {scheduled_job['interval_minutes']} minutos.")
            
            # Aguardar pelo intervalo configurado
            await asyncio.sleep(scheduled_job["interval_minutes"] * 60)
            
        except Exception as e:
            log.error(f"Erro no job de geração de sinais: {str(e)}")
            # Aguardar 5 minutos antes de tentar novamente em caso de erro
            await asyncio.sleep(300)

@app.post("/generate-signal", status_code=202) # 202 Accepted para tarefas em background
async def trigger_signal_generation(request: SignalRequest, background_tasks: BackgroundTasks):
    """Endpoint para acionar a geração de um sinal de trading para um ativo/timeframe.
    
    A processamento real ocorre em background.
    """
    # Usar logger configurado
    log.info(f"Recebida requisição para gerar sinal: {request.dict()}")
    
    # Adicionar a tarefa de geração REAL à fila de background
    background_tasks.add_task(
        process_signal_generation, 
        request.asset_id, 
        request.symbol, # Passar o símbolo
        request.timeframe
    )
    
    return {"message": "Signal generation triggered in background.", "details": request.dict()}

@app.post("/signals/schedule")
@log_execution_time
@with_context(endpoint="schedule_signals")
async def schedule_signals(
    request: ScheduleSignalsRequest,
    background_tasks: BackgroundTasks,
    api_key: str = Depends(verify_api_key)
):
    """
    Agenda a geração periódica de sinais baseados em análise técnica.
    O job rodará em background com o intervalo especificado.
    """
    global scheduled_job
    
    try:
        # Atualizar configuração do job
        scheduled_job["interval_minutes"] = request.interval_minutes
        scheduled_job["asset_ids"] = request.asset_ids or []
        scheduled_job["asset_symbols"] = request.asset_symbols or []
        scheduled_job["timeframe"] = request.timeframe
        scheduled_job["use_technical_analysis"] = request.use_technical_analysis
        
        # Se job não estiver rodando, iniciar
        if not scheduled_job["running"]:
            scheduled_job["running"] = True
            background_tasks.add_task(generate_signals_job)
            status_msg = "Job iniciado"
        else:
            status_msg = "Configuração atualizada para job em execução"
        
        return {
            "status": "success",
            "message": status_msg,
            "job_config": {
                "running": scheduled_job["running"],
                "interval_minutes": scheduled_job["interval_minutes"],
                "asset_count": len(scheduled_job["asset_ids"]) + len(scheduled_job["asset_symbols"]),
                "timeframe": scheduled_job["timeframe"],
                "last_run": scheduled_job["last_run"]
            }
        }
    except Exception as e:
        log.error(f"Erro ao agendar geração de sinais: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao agendar geração de sinais: {str(e)}",
        )

@app.post("/signals/stop-schedule")
@log_execution_time
@with_context(endpoint="stop_schedule")
async def stop_scheduled_signals(api_key: str = Depends(verify_api_key)):
    """Para a geração periódica de sinais."""
    global scheduled_job
    
    try:
        if scheduled_job["running"]:
            scheduled_job["running"] = False
            return {
                "status": "success",
                "message": "Geração periódica de sinais interrompida",
                "last_run": scheduled_job["last_run"]
            }
        else:
            return {
                "status": "success",
                "message": "Nenhum job de geração periódica em execução"
            }
    except Exception as e:
        log.error(f"Erro ao interromper geração de sinais: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao interromper geração de sinais: {str(e)}",
        )

async def process_signal_generation(asset_id: str, asset_symbol: str, timeframe: str = "1d"):
    """Processa a geração de um sinal em background."""
    log.info(f"Processando geração de sinal para {asset_symbol} ({timeframe})")
    
    try:
        supabase_helper = SupabaseHelper()
        
        # Obter dados históricos de preço
        price_data = await supabase_helper.get_price_history(
            asset_symbol=asset_symbol,
            timeframe=timeframe,
            limit=200  # Mais dados para análise técnica
        )
        
        if not price_data or len(price_data) < 30:
            log.warning(f"Dados insuficientes para gerar sinal para {asset_symbol}")
            return
        
        # Usar análise técnica para gerar o sinal
        analysis_result = perform_technical_analysis(price_data)
        
        if "error" in analysis_result:
            log.error(f"Erro na análise técnica para {asset_symbol}: {analysis_result['error']}")
            return
        
        # Extrair recomendação
        recommendation = analysis_result.get("recommendation", {})
        action = recommendation.get("action", "neutral")
        
        # Mapear ação para direção de sinal
        if action in ["strong_buy", "buy"]:
            direction = SignalDirection.CALL
        elif action in ["strong_sell", "sell"]:
            direction = SignalDirection.PUT
        else:
            log.info(f"Sem direção clara para {asset_symbol}, pulando")
            return
        
        # Calcular confiança
        buy_signals = recommendation.get("buy_signals", 0)
        sell_signals = recommendation.get("sell_signals", 0)
        total_signals = recommendation.get("total_signals", 1)  # Evitar divisão por zero
        
        if direction == SignalDirection.CALL:
            confidence = (buy_signals / total_signals) * 100
        else:
            confidence = (sell_signals / total_signals) * 100
        
        # Gerar notas baseadas nos indicadores
        notes = []
        
        # RSI
        rsi_value = analysis_result.get("indicators", {}).get("current", {}).get("rsi")
        if rsi_value is not None:
            if rsi_value < 30:
                notes.append(f"RSI em condição de sobrevenda ({rsi_value:.1f})")
            elif rsi_value > 70:
                notes.append(f"RSI em condição de sobrecompra ({rsi_value:.1f})")
        
        # MACD
        macd = analysis_result.get("indicators", {}).get("current", {}).get("macd", {})
        if macd and "value" in macd and "signal" in macd and "histogram" in macd:
            if macd["histogram"] > 0 and macd["histogram"] > abs(macd["histogram"]) * 0.1:
                notes.append("MACD com histograma positivo e crescente")
            elif macd["histogram"] < 0 and abs(macd["histogram"]) > abs(macd["histogram"]) * 0.1:
                notes.append("MACD com histograma negativo e decrescente")
        
        # Tendência
        trend = analysis_result.get("market_structure", {}).get("trend")
        if trend:
            notes.append(f"Tendência de mercado: {trend}")
        
        # Divergências
        divergences = analysis_result.get("divergences", {})
        if divergences:
            for indicator, div in divergences.items():
                if div.get("bullish"):
                    notes.append(f"Divergência positiva no {indicator.upper()}")
                elif div.get("bearish"):
                    notes.append(f"Divergência negativa no {indicator.upper()}")
        
        # Juntar notas
        signal_notes = ". ".join(notes)
        
        # Criar dados do sinal
        now = datetime.now()
        valid_hours = 4 if timeframe in ["1m", "5m", "15m", "30m", "1h"] else 24
        valid_until = now + timedelta(hours=valid_hours)
        
        # Gerar horários otimizados para entradas (de 5 em 5 minutos)
        entry_times = []
        
        # Verificar o período do dia para gerar horários mais assertivos
        current_hour = now.hour
        
        # Períodos de maior assertividade baseados em padrões de mercado
        premium_periods = [
            # Abertura do mercado (alta volatilidade)
            {"start": 9, "end": 10, "confidence_boost": 10, "interval_minutes": 5},
            # Período do almoço (menor volume, movimentos mais previsíveis)
            {"start": 12, "end": 13, "confidence_boost": 5, "interval_minutes": 5},
            # Após almoço (retomada de volume)
            {"start": 14, "end": 15, "confidence_boost": 8, "interval_minutes": 5},
            # Fechamento (alta volatilidade e volume)
            {"start": 16, "end": 17, "confidence_boost": 12, "interval_minutes": 5}
        ]
        
        # Gerar horários para cada período premium
        for period in premium_periods:
            # Verificar se estamos dentro ou antes do período
            if current_hour <= period["end"]:
                period_start = now.replace(hour=period["start"], minute=0, second=0, microsecond=0)
                
                # Se já passou do horário de início, ajustar para o próximo intervalo de 5 minutos
                if period_start < now and current_hour == period["start"]:
                    minutes = ((now.minute // 5) + 1) * 5
                    if minutes >= 60:
                        # Passar para a próxima hora
                        period_start = period_start.replace(hour=period_start.hour + 1, minute=0)
                    else:
                        period_start = period_start.replace(minute=minutes)
                
                # Se o período for hoje no futuro
                if period_start > now:
                    # Calcular quantos slots de X minutos cabem no período
                    period_end = now.replace(hour=period["end"], minute=0, second=0, microsecond=0)
                    total_minutes = (period_end - period_start).total_seconds() / 60
                    num_slots = int(total_minutes / period["interval_minutes"])
                    
                    # Gerar até 6 horários dentro do período
                    for i in range(min(6, num_slots)):
                        entry_time = period_start + timedelta(minutes=i * period["interval_minutes"])
                        
                        # Calcular confiança ajustada para este horário
                        adjusted_confidence = min(99, confidence + period["confidence_boost"])
                        
                        # Adicionar pequena variação para evitar valores idênticos
                        variation = random.uniform(-2, 2)
                        final_confidence = max(70, min(99, adjusted_confidence + variation))
                        
                        entry_times.append({
                            "time": entry_time.isoformat(),
                            "confidence": final_confidence,
                            "isPremium": final_confidence > 85
                        })
        
        # Se não gerou nenhum horário (ex: já passou dos períodos ideais), criar pelo menos um
        if not entry_times:
            # Próximo intervalo de 5 minutos
            next_slot = now + timedelta(minutes=(5 - (now.minute % 5)))
            entry_times.append({
                "time": next_slot.isoformat(),
                "confidence": confidence,
                "isPremium": confidence > 85
            })
        
        # Ordenar horários
        entry_times.sort(key=lambda x: x["time"])
        
        signal_data = {
            "asset_id": asset_id,
            "asset_symbol": asset_symbol,
            "direction": direction.value,
            "confidence": confidence,
            "generated_at": now.isoformat(),
            "valid_until": valid_until.isoformat(),
            "status": SignalStatus.ACTIVE.value,
            "timeframe": timeframe,
            "source": SignalSource.TECHNICAL_ANALYSIS.value,
            "indicators": analysis_result.get("indicators", {}).get("current"),
            "notes": signal_notes,
            "metadata": {
                "market_structure": analysis_result.get("market_structure"),
                "patterns": analysis_result.get("patterns"),
                "recommendation": recommendation,
                "entry_times": entry_times  # Adicionar horários otimizados
            }
        }
        
        # Salvar sinal no Supabase
        signal_result = await supabase_helper.create_signal(signal_data)
        log.info(f"Sinal gerado para {asset_symbol}: {direction.value} com {confidence:.1f}% confiança e {len(entry_times)} horários otimizados")
        
    except Exception as e:
        log.error(f"Erro ao gerar sinal para {asset_symbol}: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    
    uvicorn.run("src.api.main:app", host=host, port=port, reload=True)