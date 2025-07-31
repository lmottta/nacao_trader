#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Gerador diário de sinais para operações binárias/opções digitais.
Este script garante que sinais sejam gerados diariamente, mesmo para ativos OTC.

Principais funcionalidades:
- Geração automática de sinais para operações binárias (CALL/PUT)
- Suporte a sinais OTC (Over The Counter) para mercados fechados
- Distribuição equilibrada entre diferentes tipos de ativos
- Atualização de preços simulados para ativos
- Análise técnica contextualizada baseada no tipo de ativo

Execução recomendada: Cron job diário às 00:05
"""

import os
import sys
import random
import asyncio
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path

import json
from loguru import logger
from dotenv import load_dotenv
from supabase import create_client, Client

# Adicionar diretório principal ao path para importações
ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))

# Configurando logger
LOG_DIR = os.path.join(ROOT_DIR, 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
logger.remove()
logger.add(sys.stdout, level="INFO", colorize=True, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
logger.add(os.path.join(LOG_DIR, "daily_signals.log"), rotation="10 MB", retention="10 days", level="INFO", encoding="utf-8")

# Carregar variáveis de ambiente
dotenv_path = os.path.join(ROOT_DIR, '.env')
load_dotenv(dotenv_path=dotenv_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    logger.error("Variáveis de ambiente SUPABASE_URL e SUPABASE_SERVICE_KEY não encontradas.")
    logger.error(f"Verifique se o arquivo .env existe em {ROOT_DIR} e contém as variáveis.")
    sys.exit(1)

# Configuração do cliente Supabase
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    logger.info("Cliente Supabase inicializado com sucesso.")
except Exception as e:
    logger.error(f"Erro ao inicializar cliente Supabase: {e}")
    sys.exit(1)

# Configurar tipos de análise técnica que serão usados
TECHNICAL_INDICATORS = [
    "RSI", "MACD", "Bollinger", "EMA", "Estocástico", 
    "Fibonacci", "Suporte/Resistência", "Divergência", "Candlesticks"
]

# Padrões para sinais de OTC
OTC_PATTERNS = [
    "Rompimento de Ponto Pivot", "Retorno à Média", "Retração de Fibonacci",
    "Divergência de Volume", "Formação de Cunha", "Bandeiras e Flâmulas", 
    "OCO (One Cancels the Other)", "Reversão Dupla", "Padrão 1-2-3",
    "Pinbar com Confirmação", "Velas Doji", "Engolfo de Alta/Baixa"
]

async def get_assets_from_supabase() -> List[Dict[str, Any]]:
    """Busca todos os ativos cadastrados no Supabase."""
    try:
        response = supabase.table('assets').select('*').execute()
        assets = response.data
        logger.info(f"Obtidos {len(assets)} ativos do Supabase.")
        return assets
    except Exception as e:
        logger.error(f"Erro ao obter ativos do Supabase: {e}")
        return []

async def check_existing_signals() -> int:
    """Verifica sinais ativos existentes para hoje."""
    try:
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        
        response = supabase.table('signals').select('id').gte('generated_at', today.isoformat()).lt('generated_at', tomorrow.isoformat()).execute()
        count = len(response.data) if response.data else 0
        logger.info(f"Existem {count} sinais ativos gerados hoje.")
        return count
    except Exception as e:
        logger.error(f"Erro ao verificar sinais existentes: {e}")
        return 0

def generate_otc_reasoning(asset_type: str, direction: str) -> str:
    """Gera uma análise técnica para ativos OTC baseada no tipo de ativo."""
    indicator1 = random.choice(TECHNICAL_INDICATORS)
    indicator2 = random.choice(TECHNICAL_INDICATORS)
    while indicator2 == indicator1:
        indicator2 = random.choice(TECHNICAL_INDICATORS)
        
    pattern = random.choice(OTC_PATTERNS)
    
    if direction == "CALL":
        if asset_type == "forex":
            return f"Análise OTC: {pattern} identificado com {indicator1} em zona de sobrevenda. {indicator2} indica forte potencial de correção para cima no curto prazo. Padrão de reversão formado nas últimas velas."
        elif asset_type == "crypto":
            return f"Análise OTC: Formação de suporte em {indicator1} com {pattern} claro. {indicator2} mostra acumulação e divergência positiva nos indicadores de fluxo de capital."
        else:  # stocks
            return f"Análise OTC: {indicator1} em confluência com {indicator2} apontando reversão. {pattern} formado nos timeframes menores com confirmação de volume."
    else:  # PUT
        if asset_type == "forex":
            return f"Análise OTC: {pattern} formado no topo com {indicator1} em zona de sobrecompra. {indicator2} sugere esgotamento da tendência atual e potencial de queda."
        elif asset_type == "crypto":
            return f"Análise OTC: {indicator1} mostra distribuição na resistência principal. {pattern} identificado com aumento de pressão vendedora. {indicator2} em divergência negativa."
        else:  # stocks
            return f"Análise OTC: {indicator1} e {indicator2} convergem indicando exaustão de alta. {pattern} formado após falha no teste da resistência principal."

def calculate_signal_strength(asset_type: str) -> float:
    """Calcula a força do sinal baseado no tipo de ativo."""
    base_strength = random.uniform(0.60, 0.95)  # Base entre 60% e 95%
    
    # Ajustes por tipo de ativo (simulando confiança diferente por tipo)
    if asset_type == "forex":
        adjustment = random.uniform(-0.05, 0.05)  # +/- 5%
    elif asset_type == "crypto":
        adjustment = random.uniform(-0.10, 0.10)  # +/- 10% (mais volátil)
    else:  # stocks
        adjustment = random.uniform(-0.03, 0.07)  # -3% a +7%
    
    # Garantir que a força final esteja entre 60% e 95%
    return max(0.60, min(0.95, base_strength + adjustment))

def generate_entry_times(base_time: datetime, count: int = 5) -> List[str]:
    """Gera horários recomendados para entrada no mercado."""
    entry_times = []
    
    # Horários de maior liquidez para day trade
    intervals = [30, 60, 90, 120, 180, 240, 300]
    
    for _ in range(count):
        minutes_ahead = random.choice(intervals)
        entry_time = base_time + timedelta(minutes=minutes_ahead)
        
        # Ajustar para horário comercial se for ação
        hour = entry_time.hour
        if 9 <= hour <= 17:
            # Arredondar para o intervalo de 5 minutos mais próximo
            minute = (entry_time.minute // 5) * 5
            entry_time = entry_time.replace(minute=minute, second=0, microsecond=0)
            entry_times.append(entry_time.isoformat())
    
    return sorted(entry_times)

async def create_signal(asset: Dict[str, Any], force_direction: Optional[str] = None) -> Dict[str, Any]:
    """
    Cria um novo sinal para um ativo com base em análise técnica simulada.
    
    Args:
        asset: Dicionário com dados do ativo
        force_direction: Forçar uma direção específica (CALL/PUT)
        
    Returns:
        Dicionário com dados do sinal criado ou erro
    """
    try:
        now = datetime.now()
        asset_id = asset.get("id")
        asset_symbol = asset.get("symbol")
        asset_type = asset.get("asset_type", "stock")
        market_status = asset.get("market_status", "closed")
        
        # Determinar direção do sinal (CALL/PUT)
        direction = force_direction if force_direction else random.choice(["CALL", "PUT"])
        
        # Calcular confiança do sinal
        confidence = calculate_signal_strength(asset_type)
        
        # Gerar notas de análise
        is_otc = market_status in ["closed", "otc"] or "OTC" in asset_symbol
        
        # Obter preço com fallback para um valor padrão
        last_price = asset.get("last_price")
        if last_price is None:
            # Gerar preço aleatório baseado no tipo de ativo
            if asset_type == "forex":
                last_price = random.uniform(0.5, 2.0)  # Valores típicos de forex
            elif asset_type == "crypto":
                last_price = random.uniform(100, 50000)  # Ampla faixa para criptomoedas
            else:  # stocks
                last_price = random.uniform(10, 500)  # Faixa típica para ações
            
            logger.warning(f"Preço não encontrado para {asset_symbol}. Usando valor simulado: {last_price:.2f}")
        
        # Gerar indicadores técnicos padronizados
        rsi_value = random.uniform(20, 80)
        macd_value = random.uniform(-2, 2)
        macd_signal = random.uniform(-2, 2)
        macd_histogram = random.uniform(-1, 1)
        
        bollinger_middle = last_price
        bollinger_upper = last_price * 1.02
        bollinger_lower = last_price * 0.98
        
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
        
        if is_otc:
            notes = generate_otc_reasoning(asset_type, direction)
            source = "OTC_ANALYSIS"
        else:
            # Análise para mercado regular
            rsi_condition = "sobrevenda" if indicators["rsi"] < 30 else ("sobrecompra" if indicators["rsi"] > 70 else "neutro")
            macd_trend = "cruzamento positivo" if macd_value > macd_signal else "cruzamento negativo"
            
            if direction == "CALL":
                notes = f"RSI em {rsi_condition} ({indicators['rsi']:.1f}). MACD apresenta {macd_trend}. Preço próximo à banda inferior de Bollinger indicando potencial de alta."
            else:
                notes = f"RSI em {rsi_condition} ({indicators['rsi']:.1f}). MACD apresenta {macd_trend}. Preço testando resistência na banda superior de Bollinger."
            
            source = "TECHNICAL_ANALYSIS"
        
        # Período de validade (4h para curto prazo, 24h para diário)
        valid_hours = 24  # Padrão diário
        valid_until = now + timedelta(hours=valid_hours)
        
        # Gerar horários de entrada recomendados
        entry_times = generate_entry_times(now, count=random.randint(3, 6))
        
        # Montar objeto do sinal
        signal_data = {
            "asset_id": asset_id,
            "asset_symbol": asset_symbol,
            "direction": direction,
            "confidence": confidence,
            "accuracy": confidence,  # Usar o mesmo valor de confidence para accuracy (campo obrigatório)
            "generated_at": now.isoformat(),
            "valid_until": valid_until.isoformat(),
            "status": "active",
            "timeframe": "1d",  # Diário
            "source": source,
            "indicators": indicators,
            "notes": notes,
            "metadata": {
                "market_status": market_status,
                "is_otc": is_otc,
                "entry_times": entry_times,
                "recommended_price": last_price,
                "target_price": last_price * (1.01 if direction == "CALL" else 0.99)
            }
        }
        
        # Inserir no Supabase
        response = supabase.table('signals').insert(signal_data).execute()
        
        if response.data and len(response.data) > 0:
            logger.success(f"Sinal criado para {asset_symbol}: {direction} com {confidence:.1f}% confiança")
            return {"success": True, "signal": response.data[0]}
        else:
            logger.error(f"Erro ao inserir sinal para {asset_symbol}")
            return {"success": False, "error": "Sem dados retornados"}
            
    except Exception as e:
        logger.error(f"Erro ao criar sinal para {asset.get('symbol', 'unknown')}: {e}")
        return {"success": False, "error": str(e)}

async def generate_daily_signals(
    min_signals: int = 10, 
    max_signals: int = 20,
    force_otc: bool = False,
    force: bool = False
) -> Dict[str, Any]:
    """
    Gera sinais diários para ativos disponíveis.
    
    Args:
        min_signals: Número mínimo de sinais a gerar
        max_signals: Número máximo de sinais a gerar
        force_otc: Se deve forçar sinais como OTC mesmo para ativos em mercados abertos
        
    Returns:
        Estatísticas da geração de sinais
    """
    try:
        # Verificar sinais existentes para hoje
        existing_count = await check_existing_signals()
        
        # Se já temos sinais suficientes e não estamos forçando, não gerar novos
        if existing_count >= min_signals and not force:
            logger.info(f"Já existem {existing_count} sinais hoje, não é necessário gerar novos.")
            return {
                "status": "skipped",
                "existing_signals": existing_count,
                "new_signals": 0
            }
        
        if force:
            logger.info("Opção --force ativada. Gerando novos sinais independentemente dos existentes.")
        
        # Obter todos os ativos
        assets = await get_assets_from_supabase()
        if not assets:
            logger.error("Nenhum ativo encontrado para gerar sinais.")
            return {"status": "error", "message": "Nenhum ativo disponível"}
        
        # Filtrar ativos por tipo (garantir diversidade)
        stocks = [a for a in assets if a.get("asset_type") == "stock"]
        forex = [a for a in assets if a.get("asset_type") == "forex"]
        crypto = [a for a in assets if a.get("asset_type") == "crypto"]
        
        logger.info(f"Ativos disponíveis: {len(stocks)} ações, {len(forex)} forex, {len(crypto)} criptomoedas")
        
        # Determinar quantos sinais queremos gerar (considerar os existentes)
        num_to_generate = random.randint(min_signals, max_signals) - existing_count
        num_to_generate = max(0, num_to_generate)  # Garantir que não seja negativo
        
        if num_to_generate <= 0:
            logger.info("Número suficiente de sinais já existe.")
            return {
                "status": "skipped",
                "existing_signals": existing_count,
                "required_signals": min_signals
            }
        
        logger.info(f"Gerando {num_to_generate} novos sinais...")
        
        # Distribuir entre os tipos de ativos (garantir diversidade)
        num_stock = min(len(stocks), max(1, int(num_to_generate * 0.4)))
        num_forex = min(len(forex), max(1, int(num_to_generate * 0.3)))
        num_crypto = min(len(crypto), max(1, int(num_to_generate * 0.3)))
        
        # Ajustar se não tivermos ativos suficientes de algum tipo
        total_selected = num_stock + num_forex + num_crypto
        if total_selected < num_to_generate:
            # Distribuir os restantes entre os tipos que temos mais
            remaining = num_to_generate - total_selected
            if len(stocks) > num_stock:
                num_stock += min(remaining, len(stocks) - num_stock)
                remaining = num_to_generate - (num_stock + num_forex + num_crypto)
            
            if remaining > 0 and len(forex) > num_forex:
                num_forex += min(remaining, len(forex) - num_forex)
                remaining = num_to_generate - (num_stock + num_forex + num_crypto)
            
            if remaining > 0 and len(crypto) > num_crypto:
                num_crypto += min(remaining, len(crypto) - num_crypto)
        
        # Selecionar ativos aleatoriamente para cada tipo
        selected_stocks = random.sample(stocks, num_stock) if num_stock > 0 and stocks else []
        selected_forex = random.sample(forex, num_forex) if num_forex > 0 and forex else []
        selected_crypto = random.sample(crypto, num_crypto) if num_crypto > 0 and crypto else []
        
        # Combinar todos os ativos selecionados
        selected_assets = selected_stocks + selected_forex + selected_crypto
        random.shuffle(selected_assets)  # Misturar para ordem aleatória
        
        # Gerar sinais
        successful_signals = []
        failed_signals = []
        
        for asset in selected_assets:
            # Força 70% dos sinais como OTC se force_otc for True
            force_otc_for_this = force_otc and random.random() < 0.7
            
            if force_otc_for_this:
                # Forçar status como fechado para simular OTC
                asset["market_status"] = "closed"
            
            result = await create_signal(asset)
            
            if result.get("success"):
                successful_signals.append({
                    "asset_symbol": asset.get("symbol"),
                    "direction": result["signal"].get("direction"),
                    "is_otc": asset.get("market_status") in ["closed", "otc"] or force_otc_for_this
                })
            else:
                failed_signals.append({
                    "asset_symbol": asset.get("symbol"),
                    "error": result.get("error")
                })
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "existing_signals": existing_count,
            "new_signals": len(successful_signals),
            "failed_signals": len(failed_signals),
            "successful_signals": successful_signals,
            "failed_details": failed_signals
        }
    
    except Exception as e:
        logger.error(f"Erro ao gerar sinais diários: {e}")
        return {"status": "error", "message": str(e)}

async def update_assets_prices():
    """Atualiza os preços dos ativos uma vez ao dia."""
    try:
        logger.info("Iniciando atualização diária de preços dos ativos...")
        
        # Buscar todos os ativos
        assets = await get_assets_from_supabase()
        if not assets:
            logger.error("Nenhum ativo encontrado para atualizar preços.")
            return {"status": "error", "message": "Nenhum ativo disponível"}
        
        updated_count = 0
        failed_count = 0
        
        for asset in assets:
            try:
                asset_id = asset.get("id")
                symbol = asset.get("symbol")
                current_price = asset.get("last_price", 0)
                
                # Simular mudança de preço (entre -3% e +3%)
                price_change = random.uniform(-0.03, 0.03)
                new_price = current_price * (1 + price_change)
                
                # Metadados atuais
                metadata = asset.get("metadata", {})
                if not metadata:
                    metadata = {}
                
                # Atualizar informações
                update_data = {
                    "last_price": round(new_price, 4),
                    "last_update": datetime.now().isoformat(),
                    "metadata": {
                        **metadata,
                        "previous_price": current_price,
                        "change_percent": round(price_change * 100, 2)
                    }
                }
                
                # Atualizar no Supabase
                supabase.table('assets').update(update_data).eq('id', asset_id).execute()
                
                logger.info(f"Preço atualizado para {symbol}: {current_price} -> {new_price:.4f}")
                updated_count += 1
                
            except Exception as e:
                logger.error(f"Erro ao atualizar preço para {asset.get('symbol')}: {e}")
                failed_count += 1
        
        return {
            "status": "success",
            "updated_assets": updated_count,
            "failed_assets": failed_count,
            "total_assets": len(assets)
        }
    
    except Exception as e:
        logger.error(f"Erro ao atualizar preços dos ativos: {e}")
        return {"status": "error", "message": str(e)}

async def main():
    """Função principal para execução do script."""
    parser = argparse.ArgumentParser(description="Gerador diário de sinais para Nação Trader")
    parser.add_argument("--min", type=int, default=15, help="Número mínimo de sinais a gerar")
    parser.add_argument("--max", type=int, default=25, help="Número máximo de sinais a gerar")
    parser.add_argument("--force-otc", action="store_true", help="Forçar sinais como OTC")
    parser.add_argument("--update-prices", action="store_true", help="Atualizar preços dos ativos")
    parser.add_argument("--force", action="store_true", help="Forçar a geração de novos sinais mesmo que já existam")
    args = parser.parse_args()
    
    logger.info("=== Iniciando gerador diário de sinais ===")
    
    # Atualizar preços se solicitado
    if args.update_prices:
        logger.info("Atualizando preços dos ativos...")
        price_result = await update_assets_prices()
        logger.info(f"Resultado da atualização de preços: {price_result}")
    
    # Gerar sinais
    result = await generate_daily_signals(
        min_signals=args.min,
        max_signals=args.max,
        force_otc=args.force_otc,
        force=args.force
    )
    
    logger.info(f"Resultado da geração de sinais: {result}")
    logger.info("=== Gerador diário de sinais concluído ===")
    
    return result

if __name__ == "__main__":
    asyncio.run(main())