# Este arquivo será preenchido com o script Python. 

import os
# print("Importou os")
import time
# print("Importou time")
import json
import random
from datetime import datetime, timedelta
# print("Importou datetime")
import pandas as pd
# print("Importou pandas")
import yfinance as yf
# print("Importou yfinance")
from dotenv import load_dotenv
# print("Importou load_dotenv")
from supabase import create_client, Client
# print("Importou supabase")
from loguru import logger

# Configuração do loguru
import sys
LOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
logger.remove()
logger.add(sys.stdout, level="INFO", colorize=True, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
logger.add(os.path.join(LOG_DIR, "collector.log"), rotation="10 MB", retention="10 days", level="INFO", encoding="utf-8")

# Diretório para cache local
CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', 'cache')
os.makedirs(CACHE_DIR, exist_ok=True)

# Carregar variáveis de ambiente do .env na pasta motor/
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("Erro: Variáveis de ambiente SUPABASE_URL e SUPABASE_SERVICE_KEY não encontradas.")
    print(f"Verifique se o arquivo .env existe em {os.path.dirname(dotenv_path)} e contém as variáveis.")
    exit(1)

# Configuração do cliente Supabase
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    print("Cliente Supabase inicializado com sucesso.")
except Exception as e:
    print(f"Erro ao inicializar cliente Supabase: {e}")
    exit(1)

# --- Definição dos Tickers ---
# Adicione/remova tickers conforme necessário
TICKERS_STOCKS_BR = [
    "PETR4.SA", "VALE3.SA", "ITUB4.SA", "BBDC4.SA", "ABEV3.SA", 
    "MGLU3.SA", "VIIA3.SA", "B3SA3.SA", "WEGE3.SA", "BBAS3.SA" 
]
TICKERS_STOCKS_US = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", 
    "META", "TSLA", "JPM", "V", "JNJ"
]
TICKERS_FOREX = [
    "EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X",
    "USDCHF=X", "NZDUSD=X", "EURGBP=X", "EURJPY=X", "GBPJPY=X"
]
TICKERS_CRYPTO = [
    "BTC-USD", "ETH-USD", "BNB-USD", "XRP-USD", "ADA-USD", 
    "SOL-USD", "DOGE-USD", "DOT-USD", "MATIC-USD", "LTC-USD"
]

ALL_TICKERS = list(set(TICKERS_STOCKS_BR + TICKERS_STOCKS_US + TICKERS_FOREX + TICKERS_CRYPTO))

# --- Configurações Melhoradas ---
MAX_RETRIES = 7  # Aumentado para mais tentativas
INITIAL_RETRY_DELAY = 10  # segundos (aumentado para ser mais conservador)
MAX_RETRY_DELAY = 300  # segundos (aumentado para 5 minutos em casos extremos)
BATCH_SIZE = 3  # Reduzido para apenas 3 tickers por vez
BATCH_PAUSE = 30  # segundos de pausa entre lotes (aumentado)
JITTER_FACTOR = 0.3  # Mais aleatoriedade no tempo de espera
CACHE_EXPIRY = 7  # dias - dados do cache são válidos por 7 dias
# ------

def map_market_state(state: str | None) -> str | None:
    """Mapeia o marketState do yfinance para o nosso enum."""
    if not state:
        return None
    state_lower = state.lower()
    # Mapeamentos diretos de yfinance
    if state_lower == 'regular': return 'open'
    if state_lower == 'closed': return 'closed'
    if state_lower == 'pre': return 'pre'
    if state_lower == 'post': return 'post'
    # Outros estados possíveis (PREPRE, POSTPOST, etc.) são mapeados para fechado ou pré/post
    if 'pre' in state_lower: return 'pre'
    if 'post' in state_lower: return 'post'
    # Não há estado OTC explícito em yfinance, tratar como fechado ou exigir lógica adicional
    if state_lower == 'otc': return 'otc' # Se por acaso existir
    
    print(f"[Aviso] Estado de mercado não mapeado: {state}. Tratando como 'closed'.")
    return 'closed' # Default seguro

def get_asset_type(ticker_info: dict) -> str:
    """Determina o tipo de ativo baseado nas informações do yfinance."""
    quote_type = ticker_info.get('quoteType', '').upper()
    symbol = ticker_info.get('symbol', '')
    exchange = ticker_info.get('exchange', '').upper()
    currency = ticker_info.get('currency', '').upper()

    if quote_type == 'EQUITY':
        # Pode ser ação BR ou US
        if '.SA' in symbol or exchange == 'SAO':
            return 'stock' # Assumindo Ação BR
        else:
             return 'stock' # Assumindo Ação US
    if quote_type == 'CURRENCY':
        return 'forex'
    if quote_type == 'CRYPTOCURRENCY':
        return 'crypto'
    if quote_type == 'INDEX':
         return 'index' # Adicionando suporte a índice
    if quote_type == 'ETF':
         return 'etf' # Adicionando suporte a ETF
    if quote_type == 'FUTURE':
         return 'future' # Adicionando suporte a futuro
    
    # Fallbacks baseados em ticker se quoteType for ausente/ambíguo
    if '.SA' in symbol:
        return 'stock'
    if '=X' in symbol:
        return 'forex'
    if '-USD' in symbol:
        return 'crypto'

    print(f"[Aviso] Tipo de ativo incerto para {symbol} (QuoteType: {quote_type}). Usando 'stock' como padrão.")
    return 'stock' # Default geral

def is_cache_valid(file_path):
    """Verifica se o cache ainda é válido com base na data de modificação."""
    if not os.path.exists(file_path):
        return False
    
    # Obter o timestamp da modificação do arquivo
    mod_time = os.path.getmtime(file_path)
    mod_date = datetime.fromtimestamp(mod_time)
    
    # Verificar se está dentro do período de expiração
    return datetime.now() - mod_date < timedelta(days=CACHE_EXPIRY)

def save_to_cache(ticker_symbol: str, data: dict):
    """Salva dados de um ticker no cache local."""
    cache_file = os.path.join(CACHE_DIR, f"{ticker_symbol.replace('/', '_').replace('=', '_')}.json")
    try:
        with open(cache_file, 'w') as f:
            json.dump(data, f)
        logger.success(f"Cache salvo para {ticker_symbol}")
    except Exception as e:
        logger.error(f"Erro ao salvar cache para {ticker_symbol}: {e}")

def load_from_cache(ticker_symbol: str) -> dict:
    """Carrega dados de um ticker do cache local."""
    cache_file = os.path.join(CACHE_DIR, f"{ticker_symbol.replace('/', '_').replace('=', '_')}.json")
    try:
        if is_cache_valid(cache_file):
            with open(cache_file, 'r') as f:
                data = json.load(f)
            logger.info(f"Cache válido carregado para {ticker_symbol}")
            return data
        else:
            if os.path.exists(cache_file):
                logger.warning(f"Cache expirado para {ticker_symbol}")
            return None
    except Exception as e:
        logger.error(f"Erro ao carregar cache para {ticker_symbol}: {e}")
        return None

def fetch_ticker_data(ticker_symbol: str):
    """Busca dados de um ticker no Yahoo Finance com backoff exponencial."""
    logger.info(f"Processando: {ticker_symbol}")
    retries = 0
    success = False
    asset_data = None
    
    # Verificar cache primeiro
    cached_data = load_from_cache(ticker_symbol)
    if cached_data:
        logger.info(f"[CACHE] {ticker_symbol}")
        return cached_data, True

    while retries < MAX_RETRIES and not success:
        try:
            # Usar history para obter dados mais recentes e info para metadados
            ticker_obj = yf.Ticker(ticker_symbol)
            info = ticker_obj.info
            
            # Verificar se temos informações básicas
            if not info or len(info) < 5:  # Verificação muito básica
                raise ValueError(f"Dados insuficientes recebidos para {ticker_symbol}")
                
            hist = ticker_obj.history(period="2d") # Pegar 2 dias para garantir o último fechamento

            if hist.empty:
                logger.warning(f"Histórico vazio para {ticker_symbol}. Pulando.")
                return None, True
            
            # Último preço disponível no histórico (mais confiável que info para preço)
            last_close_data = hist.iloc[-1]
            last_price = last_close_data.get('Close')
            last_update = last_close_data.name.isoformat() # Timestamp do último dado do histórico

            name = info.get('longName', info.get('shortName', ticker_symbol))
            market_state = info.get('marketState')
            currency = info.get('currency', 'USD')
            asset_type = get_asset_type(info)

            # Tenta usar o symbol retornado pela API se diferente do input
            resolved_symbol = info.get('symbol', ticker_symbol)
            
            # Converter datetime para string ISO com timezone para compatibilidade com TIMESTAMPTZ
            current_time_iso = datetime.now().astimezone().isoformat()
            
            asset_data = {
                "symbol": resolved_symbol, # Usar símbolo resolvido pela API
                "name": name,
                "asset_type": asset_type,
                "description": info.get('longBusinessSummary', None),
                "last_price": float(last_price) if pd.notna(last_price) else None,
                "last_update": last_update,
                "ticker": ticker_symbol, # Manter o ticker original buscado também
                "active": True, 
                "currency": currency,
                "market_status": map_market_state(market_state),
                "market_status_source": "YahooFinance",
                "last_status_update": current_time_iso,
                "metadata": { 
                    'exchange': info.get('exchange'),
                    'quoteType': info.get('quoteType'),
                    'marketCap': info.get('marketCap'),
                    'volume': info.get('regularMarketVolume', last_close_data.get('Volume')),
                    'previousClose': info.get('regularMarketPreviousClose', hist.iloc[-2].get('Close') if len(hist) > 1 else None),
                    'open': last_close_data.get('Open'),
                    'high': last_close_data.get('High'),
                    'low': last_close_data.get('Low')
                }
            }
            
            if not all([asset_data["symbol"], asset_data["name"], asset_data["asset_type"]]):
                logger.warning(f"Dados incompletos para {ticker_symbol}. Pulando.")
                return None, True

            logger.success(f"Dados coletados com sucesso para {ticker_symbol}")
            
            # Salvar no cache para uso futuro
            save_to_cache(ticker_symbol, asset_data)
            
            return asset_data, True

        except Exception as e:
            retries += 1
            # Implementar backoff exponencial com jitter
            if "429" in str(e) or "Too Many Requests" in str(e):
                # Rate limiting detectado - esperar mais
                wait_time = min(INITIAL_RETRY_DELAY * (2 ** retries), MAX_RETRY_DELAY)
                # Adicionar jitter (variação aleatória)
                jitter = random.uniform(-JITTER_FACTOR * wait_time, JITTER_FACTOR * wait_time)
                wait_time = max(5, wait_time + jitter)  # Garantir pelo menos 5 segundos
                logger.warning(f"[Rate Limit {retries}/{MAX_RETRIES}] {ticker_symbol} - Aguardando {wait_time:.1f}s...")
            else:
                # Outro tipo de erro - backoff mais suave
                wait_time = INITIAL_RETRY_DELAY * retries
                logger.error(f"[Falha {retries}/{MAX_RETRIES}] {ticker_symbol} - Erro: {e}. Tentando novamente em {wait_time:.1f}s...")
            
            if retries >= MAX_RETRIES:
                logger.error(f"[ERRO FINAL] Falha ao buscar dados para {ticker_symbol} após {MAX_RETRIES} tentativas. Erro: {e}")
                # Salvar erro em arquivo separado para análise posterior
                with open(os.path.join(CACHE_DIR, "fetch_errors.log"), "a") as f:
                    f.write(f"{datetime.now().isoformat()} - {ticker_symbol}: {str(e)}\n")
                return None, False
            else:
                time.sleep(wait_time)
    
    return None, False  # Não deveria chegar aqui, mas por segurança

def process_ticker_batch(tickers_batch):
    """Processa um lote de tickers com controle de rate limiting."""
    assets_to_upsert = []
    failed_tickers = []
    
    for ticker_symbol in tickers_batch:
        asset_data, success = fetch_ticker_data(ticker_symbol)
        if asset_data:
            assets_to_upsert.append(asset_data)
        elif not success:
            failed_tickers.append(ticker_symbol)
        
        # Pausa maior entre tickers no mesmo lote
        pause_time = random.uniform(3.0, 8.0)
        logger.info(f"Pausa entre tickers: {pause_time:.1f}s...")
        time.sleep(pause_time)
    
    return assets_to_upsert, failed_tickers

def upsert_to_supabase(assets_data):
    """Realiza upsert no Supabase com os dados coletados."""
    if not assets_data:
        logger.warning("Nenhum dado de ativo válido para upsert.")
        return False

    try:
        logger.info(f"Realizando upsert para {len(assets_data)} ativos...")
        # Processar em lotes menores caso a lista seja grande
        UPSERT_BATCH_SIZE = 10
        for i in range(0, len(assets_data), UPSERT_BATCH_SIZE):
            batch = assets_data[i:i + UPSERT_BATCH_SIZE]
            logger.info(f"Upsert de lote {i//UPSERT_BATCH_SIZE + 1}/{(len(assets_data)-1)//UPSERT_BATCH_SIZE + 1} ({len(batch)} ativos)")
            
            response = supabase.table('assets').upsert(
                batch, 
                on_conflict='symbol',
            ).execute()
            
            # Pequena pausa entre lotes de upsert para não sobrecarregar o Supabase
            if i + UPSERT_BATCH_SIZE < len(assets_data):
                time.sleep(1)
        
        logger.success(f"Upsert concluído com sucesso para {len(assets_data)} ativos.")
        return True
    
    except Exception as e:
        logger.error("******************************************************")
        logger.error(f"ERRO DURANTE O UPSERT NO SUPABASE:")
        logger.error(f"Tipo de Erro: {type(e).__name__}")
        logger.error(f"Mensagem: {e}")
        # Tentar imprimir atributos específicos de erros de API
        if hasattr(e, 'details'):
            logger.error(f"Detalhes: {e.details}")
        if hasattr(e, 'message'):
            logger.error(f"Mensagem (atributo): {e.message}")
        if hasattr(e, 'code'):
            logger.error(f"Código: {e.code}")
        if hasattr(e, 'hint'):
            logger.error(f"Dica: {e.hint}")
        logger.error("******************************************************")
        return False

def fetch_and_upsert_assets(tickers: list[str], max_assets: int = None):
    """Busca dados dos tickers no Yahoo Finance e faz upsert no Supabase utilizando processamento em lotes."""
    if max_assets and max_assets < len(tickers):
        logger.info(f"Limitando processamento a {max_assets} tickers (de {len(tickers)} disponíveis).")
        tickers = tickers[:max_assets]
    else:
        logger.info(f"Iniciando busca para {len(tickers)} tickers...")
    
    # Dividir em lotes para controlar rate limiting
    assets_to_upsert_all = []
    failed_tickers_all = []
    
    # Dividir em lotes de BATCH_SIZE
    batches = [tickers[i:i + BATCH_SIZE] for i in range(0, len(tickers), BATCH_SIZE)]
    
    for i, batch in enumerate(batches):
        logger.info(f"Processando lote {i+1}/{len(batches)} ({len(batch)} tickers)")
        
        # Processar o lote atual
        assets_batch, failed_batch = process_ticker_batch(batch)
        
        # Acumular resultados
        assets_to_upsert_all.extend(assets_batch)
        failed_tickers_all.extend(failed_batch)
        
        # Realizar upsert parcial se acumulamos muitos ativos
        if len(assets_to_upsert_all) >= BATCH_SIZE * 2:
            logger.info(f"Upsert parcial de {len(assets_to_upsert_all)} ativos...")
            upsert_to_supabase(assets_to_upsert_all)
            assets_to_upsert_all = []  # Limpar após upsert
        
        # Pausa entre lotes (exceto o último)
        if i < len(batches) - 1:
            pause_time = BATCH_PAUSE + random.uniform(-5, 5)  # Adicionar jitter
            logger.info(f"Pausa entre lotes: {pause_time:.1f}s...")
            time.sleep(pause_time)
    
    # Upsert final para ativos restantes
    if assets_to_upsert_all:
        upsert_to_supabase(assets_to_upsert_all)
    
    # Relatório final
    if failed_tickers_all:
        logger.warning("Tickers que falharam em todas as tentativas:")
        for ticker in failed_tickers_all:
            logger.warning(f"- {ticker}")
        
        # Salvar lista de falhas para tentativa futura
        with open(os.path.join(CACHE_DIR, "failed_tickers.json"), "w") as f:
            json.dump(failed_tickers_all, f)
        logger.info(f"Lista de tickers com falha salva em {os.path.join(CACHE_DIR, 'failed_tickers.json')}")

def check_existing_assets():
    """Verifica ativos já existentes no Supabase para evitar busca desnecessária."""
    try:
        logger.info("Verificando ativos já existentes no Supabase...")
        response = supabase.table('assets').select('symbol').execute()
        existing_symbols = [record['symbol'] for record in response.data]
        logger.info(f"Encontrados {len(existing_symbols)} ativos já cadastrados.")
        return existing_symbols
    except Exception as e:
        logger.error(f"Erro ao verificar ativos existentes: {e}")
        return []

def generate_simplified_signals():
    """Gera sinais simplificados diretamente para teste da UI."""
    try:
        # Buscar ativos existentes no Supabase
        response = supabase.table('assets').select('*').limit(10).execute()
        assets = response.data
        
        if not assets:
            logger.warning("Nenhum ativo encontrado para gerar sinais.")
            return False
            
        logger.info(f"Gerando sinais para {len(assets)} ativos...")
        
        signals = []
        now = datetime.now()
        
        for asset in assets:
            # Gerar sinal aleatório para cada ativo
            direction = random.choice(["BUY", "SELL"])
            signal = {
                "asset_symbol": asset["symbol"],
                "direction": direction,
                "confidence": random.uniform(0.6, 0.95),
                "generated_at": now.isoformat(),
                "valid_until": (now + timedelta(hours=24)).isoformat(),
                "source": "YahooFinance",
                "status": "active",
                "details": {
                    "asset_name": asset["name"],
                    "asset_type": asset["asset_type"],
                    "indicators": {
                        "rsi": random.uniform(20, 80),
                        "macd": random.uniform(-2, 2)
                    },
                    "reason": f"Sinal de teste para demonstração da UI: {direction}"
                }
            }
            signals.append(signal)
        
        # Inserir sinais no Supabase
        if signals:
            logger.info(f"Inserindo {len(signals)} sinais no Supabase...")
            response = supabase.table('signals').insert(signals).execute()
            logger.success("Sinais inseridos com sucesso!")
            return True
    except Exception as e:
        logger.error(f"Erro ao gerar sinais simplificados: {e}")
        return False

def main():
    start_time = time.time()
    logger.info("Verificando existência do diretório de cache...")
    logger.info(f"Cache configurado em: {CACHE_DIR}")

    # Verificar ativos já existentes
    existing_assets = check_existing_assets()

    # Gerar uma lista de tickers prioritários para processar primeiro
    priority_tickers = ["AAPL", "MSFT", "GOOGL", "PETR4.SA", "VALE3.SA", 
                        "EURUSD=X", "BTC-USD", "ETH-USD"]

    # Definir limite para teste ou produção
    USE_LIMIT = input("Limitar o número de ativos para processamento? (s/N): ").lower() == 's'
    if USE_LIMIT:
        MAX_ASSETS = int(input("Número máximo de ativos para processar: ") or "10")
    else:
        MAX_ASSETS = None

    PRIORITY_ONLY = input("Processar apenas tickers prioritários? (s/N): ").lower() == 's'
    if PRIORITY_ONLY:
        tickers_to_process = priority_tickers
        logger.info(f"Processando apenas {len(tickers_to_process)} tickers prioritários.")
    else:
        failed_tickers_file = os.path.join(CACHE_DIR, "failed_tickers.json")
        RETRY_FAILED = False
        if os.path.exists(failed_tickers_file):
            try:
                with open(failed_tickers_file, "r") as f:
                    failed_tickers = json.load(f)
                if failed_tickers and input(f"Encontrados {len(failed_tickers)} tickers falhados anteriormente. Tentar novamente? (s/N): ").lower() == 's':
                    logger.info(f"Tentando novamente {len(failed_tickers)} tickers falhados...")
                    tickers_to_process = failed_tickers
                    RETRY_FAILED = True
            except Exception as e:
                logger.error(f"Erro ao carregar tickers falhados: {e}")
        if not RETRY_FAILED:
            tickers_to_process = ALL_TICKERS

    fetch_and_upsert_assets(tickers_to_process, MAX_ASSETS)

    if input("\nGerar sinais simplificados para teste da UI? (s/N): ").lower() == 's':
        generate_simplified_signals()

    end_time = time.time()
    logger.info(f"\nTempo total de execução: {end_time - start_time:.2f} segundos ({(end_time - start_time) / 60:.2f} minutos).")

if __name__ == "__main__":
    main()

# Substituir prints dentro das funções por logger.info/warning/error conforme o contexto
# Exemplo:
# print("Cliente Supabase inicializado com sucesso.") -> logger.success("Cliente Supabase inicializado com sucesso.")
# print(f"Erro ao inicializar cliente Supabase: {e}") -> logger.error(f"Erro ao inicializar cliente Supabase: {e}")
# print("✓ Cache salvo para {ticker_symbol}") -> logger.success(f"Cache salvo para {ticker_symbol}")
# print("✗ Erro ao salvar cache para {ticker_symbol}: {e}") -> logger.error(f"Erro ao salvar cache para {ticker_symbol}: {e}")
# print("[Aviso] ...") -> logger.warning("...")
# print("[OK]") -> logger.success("[OK]")
# print("[CACHE]") -> logger.info("[CACHE]")
# print("Nenhum dado de ativo válido para upsert.") -> logger.warning("Nenhum dado de ativo válido para upsert.")
# print("Upsert concluído com sucesso para ...") -> logger.success("Upsert concluído com sucesso para ...")
# print("Tickers que falharam em todas as tentativas:") -> logger.warning("Tickers que falharam em todas as tentativas:")
# print(f"- {ticker}") -> logger.warning(f"- {ticker}")
# print(f"Lista de tickers com falha salva em ...") -> logger.info(f"Lista de tickers com falha salva em ...")
# print(f"Verificando ativos já existentes no Supabase...") -> logger.info(f"Verificando ativos já existentes no Supabase...")
# print(f"Encontrados {len(existing_symbols)} ativos já cadastrados.") -> logger.info(f"Encontrados {len(existing_symbols)} ativos já cadastrados.")
# print(f"Erro ao verificar ativos existentes: {e}") -> logger.error(f"Erro ao verificar ativos existentes: {e}")
# print(f"Gerando sinais para {len(assets)} ativos...") -> logger.info(f"Gerando sinais para {len(assets)} ativos...")
# print("Nenhum ativo encontrado para gerar sinais.") -> logger.warning("Nenhum ativo encontrado para gerar sinais.")
# print("Sinais inseridos com sucesso!") -> logger.success("Sinais inseridos com sucesso!")
# print(f"Erro ao gerar sinais simplificados: {e}") -> logger.error(f"Erro ao gerar sinais simplificados: {e}") 