# motor/scripts/fetch_yahoo_prices.py
import os
import time
from datetime import datetime, timedelta
import asyncio

import pandas as pd
import yfinance as yf
from dotenv import load_dotenv
from loguru import logger

# Ajustar o path para importar de src (Removido - Usar import relativo)
# import sys
# sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Usar importações relativas ao pacote 'motor'
from ..src.utils.supabase_client import SupabaseHelper
# Remover import desnecessário de setup_logging
# from ..src.utils.logger import setup_logging
# Importar get_logger para obter a instância
from ..src.utils.logger import get_logger

# Configurar logging (Obter instância)
# setup_logging() # Remover chamada
log = get_logger("fetch_yahoo_prices") # Obter logger com nome específico

# Carregar variáveis de ambiente do .env na pasta motor/
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

# --- Configurações ---
DEFAULT_PERIOD = "1y" # Período padrão para buscar dados históricos (ex: "1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max")
DEFAULT_INTERVAL = "1d" # Intervalo padrão dos dados (ex: "1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo")
BATCH_SIZE = 50 # Quantidade de registros para inserir no Supabase por vez
RATE_LIMIT_DELAY = 5 # Aumentar delay para 5 segundos
# --- Fim Configurações ---

def convert_symbol_to_yfinance(symbol: str, asset_type: str) -> str:
    """Converte símbolo para o formato esperado pelo yfinance."""
    symbol_upper = symbol.upper()
    asset_type_lower = asset_type.lower()
    
    if asset_type_lower == 'forex':
        # Ex: EUR/USD -> EURUSD=X
        return symbol_upper.replace('/', '') + "=X"
    elif asset_type_lower == 'crypto':
        # Ex: BTC/USD -> BTC-USD
        return symbol_upper.replace('/', '-')
    elif asset_type_lower == 'stock' or asset_type_lower == 'index':
        # Geralmente o símbolo já está correto, mas podemos remover barras se houver
        return symbol_upper.replace('/', '') 
    # Adicionar outras conversões se necessário (CFDs, etc.)
    else:
        # Retorna o símbolo original se o tipo não for reconhecido para conversão
        return symbol_upper

async def fetch_and_store_prices(max_assets: int = None):
    """
    Busca símbolos da tabela 'assets', obtém dados históricos do Yahoo Finance
    e salva na tabela 'price_history'.
    """
    log.info("Iniciando busca e armazenamento de preços históricos...")
    helper = SupabaseHelper()
    processed_symbols = 0
    assets = [] # Inicializa fora do try

    try:
        # 1. Buscar ativos com TIPO também
        log.info("Buscando lista de ativos do Supabase...")
        try:
            # Esta chamada é síncrona
            assets_response = helper.client.table('assets')\
                                            .select('id, symbol, asset_type') \
                                            .eq('active', True)\
                                            .execute()
            
            # V2: Verificar .data diretamente. Erros podem levantar exceção.
            if assets_response.data:
                assets = assets_response.data
            else:
                log.warning("Nenhum dado retornado ao buscar ativos. Verifique a tabela 'assets' ou logs anteriores.")
        
        except Exception as fetch_err:
            log.error(f"Exceção ao buscar ativos do Supabase: {fetch_err}", exc_info=True)
            # Se falhar aqui, não podemos continuar
            log.info(f"Processo abortado devido à falha na busca de ativos. {processed_symbols} símbolos processados.")
            return 

        if not assets:
            log.warning("Nenhum ativo encontrado no Supabase para buscar preços.")
            return
            
        log.info(f"Encontrados {len(assets)} ativos para processar.")
        if max_assets:
            assets = assets[:max_assets]
            log.info(f"Limitando processamento aos primeiros {max_assets} ativos.")

        # 2. Iterar sobre os ativos
        for asset in assets:
            original_symbol = asset.get('symbol')
            asset_type = asset.get('asset_type')
            
            if not original_symbol or not asset_type:
                log.warning(f"Ativo com ID {asset.get('id')} sem símbolo ou tipo. Pulando.")
                continue
                
            yf_symbol = convert_symbol_to_yfinance(original_symbol, asset_type)
            log.info(f"Processando: {original_symbol} (Tipo: {asset_type}) -> YF: {yf_symbol}")
            
            try:
                ticker = yf.Ticker(yf_symbol)
                hist_df = ticker.history(period=DEFAULT_PERIOD, interval=DEFAULT_INTERVAL)
                
                if hist_df.empty:
                    log.warning(f"Nenhum dado histórico retornado pelo yfinance para {yf_symbol} ({original_symbol}). Pulando.")
                    continue

                log.info(f"Dados históricos encontrados para {yf_symbol}: {len(hist_df)} registros.")

                # 3. Formatar dados (usar o SÍMBOLO ORIGINAL do DB para salvar)
                price_data_to_insert = []
                for index, row in hist_df.iterrows():
                    # Verificar se o timestamp do índice já tem timezone
                    timestamp_obj = pd.Timestamp(index)
                    if timestamp_obj.tzinfo is not None:
                        # Se já tem timezone, converter para UTC
                        timestamp_aware = timestamp_obj.tz_convert('UTC')
                    else:
                        # Se não tem timezone (naive), localizar como UTC
                        timestamp_aware = timestamp_obj.tz_localize('UTC')
                        
                    price_data_to_insert.append({
                        "symbol": original_symbol, 
                        "timestamp": timestamp_aware.isoformat(), # Usar timestamp convertido/localizado
                        "timeframe": DEFAULT_INTERVAL,
                        "open": row['Open'],
                        "high": row['High'],
                        "low": row['Low'],
                        "close": row['Close'],
                        "volume": row['Volume'],
                        "source": "yahoo_finance"
                    })
                
                if price_data_to_insert:
                    log.info(f"Inserindo/Atualizando {len(price_data_to_insert)} registros de preço para {original_symbol}...")
                    try:
                        # Esta chamada é síncrona
                        helper.upsert_price_data(price_data_to_insert)
                        log.info(f"Dados para {original_symbol} salvos no Supabase.")
                    except Exception as upsert_err:
                        log.error(f"Erro ao fazer upsert dos dados de preço para {original_symbol}: {upsert_err}", exc_info=True)
                 
                processed_symbols += 1

            except Exception as e:
                log.error(f"Erro ao processar símbolo {original_symbol} (YF: {yf_symbol}): {e}", exc_info=True)
            
            log.debug(f"Aguardando {RATE_LIMIT_DELAY}s antes do próximo símbolo...")
            await asyncio.sleep(RATE_LIMIT_DELAY)
            
    # O finally executa mesmo se a função retornar antes
    finally:
        log.info(f"Processo concluído. {processed_symbols} símbolos processados.")

if __name__ == "__main__":
    start_time = time.time()
    # Definir limite de ativos para processar (None para todos)
    MAX_ASSETS_TO_PROCESS = 10 # Reduzir para teste inicial
    
    # Usar asyncio.run() para executar a função async
    asyncio.run(fetch_and_store_prices(max_assets=MAX_ASSETS_TO_PROCESS))
    
    end_time = time.time()
    log.info(f"Tempo total de execução: {end_time - start_time:.2f} segundos.") # Usar 'log' 