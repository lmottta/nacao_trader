import yfinance as yf
import pandas as pd
import numpy as np
import requests
import os
import json
from datetime import datetime, timedelta
from tenacity import retry, stop_after_attempt, wait_exponential
import logging
from dotenv import load_dotenv, find_dotenv

# Configuração básica de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', 'cache')
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

class DataCollector:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DataCollector, cls).__new__(cls)
            # A inicialização do __init__ só acontece na primeira vez
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):  # Evita re-inicialização
            self.initialized = True
            # Carrega as variáveis de ambiente do arquivo .env mais próximo
            dotenv_path = find_dotenv()
            if dotenv_path:
                logging.info(f"Carregando .env do caminho: {dotenv_path}")
                load_dotenv(dotenv_path)
            else:
                logging.warning("Arquivo .env não encontrado.")

            self.finnhub_api_key = os.getenv('FINNHUB_API_KEY')
            self.alphavantage_api_key = os.getenv('ALPHAVANTAGE_API_KEY')
            logging.info(f"Finnhub Key Loaded: {'Yes' if self.finnhub_api_key else 'No'}")
            logging.info(f"Alpha Vantage Key Loaded: {'Yes' if self.alphavantage_api_key else 'No'}")

    def _get_cache_path(self, asset: str, period: str, interval: str) -> str:
        return os.path.join(CACHE_DIR, f"{asset}_{period}_{interval}.json")

    def _save_to_cache(self, data: pd.DataFrame, path: str):
        data.to_json(path, orient='split', date_format='iso')

    def _load_from_cache(self, path: str, cache_duration_hours: int = 1) -> pd.DataFrame | None:
        if os.path.exists(path):
            file_mod_time = datetime.fromtimestamp(os.path.getmtime(path))
            if datetime.now() - file_mod_time < timedelta(hours=cache_duration_hours):
                logging.info(f"Carregando dados do cache: {path}")
                return pd.read_json(path, orient='split')
        return None

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _fetch_yfinance_data(self, asset: str, period: str, interval: str) -> pd.DataFrame:
        """Busca dados históricos de um ativo usando o yfinance."""
        try:
            logging.info(f"Buscando dados do yfinance para o ativo: {asset}, Período: {period}, Intervalo: {interval}")
            session = requests.Session()
            session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'})
            ticker = yf.Ticker(asset, session=session)
            data = ticker.history(period=period, interval=interval)
            
            if data.empty:
                logging.warning(f"Nenhum dado encontrado para o ativo {asset} via yfinance.")
                return pd.DataFrame()

            return data
        except Exception as e:
            logging.error(f"Falha ao buscar dados da API yfinance para {asset}: {e}.")
            return pd.DataFrame()

    def _fetch_finnhub_data(self, asset: str, period: str, interval: str) -> pd.DataFrame:
        if not self.finnhub_api_key:
            logging.warning("Chave da API Finnhub não configurada. Pulando.")
            return pd.DataFrame()
        
        logging.info(f"Buscando dados do Finnhub para o ativo: {asset}")
        resolution_map = {
            '1m': '1',
            '5m': '5',
            '15m': '15',
            '30m': '30',
            '1h': '60',
            '1d': 'D',
            '1wk': 'W',
            '1mo': 'M'
        }
        resolution = resolution_map.get(interval)
        if not resolution:
            logging.warning(f"Intervalo '{interval}' não suportado pelo Finnhub.")
            return pd.DataFrame()

        # Finnhub usa timestamps, então calculamos o período
        end_time = int(datetime.now().timestamp())
        # Aproximação grosseira para o período, pode ser melhorada
        if 'mo' in period:
            start_time = int((datetime.now() - timedelta(days=30 * int(period.replace('mo', '')))).timestamp())
        elif 'd' in period:
            start_time = int((datetime.now() - timedelta(days=int(period.replace('d', '')))).timestamp())
        else: # default para 1 mês
            start_time = int((datetime.now() - timedelta(days=30)).timestamp())

        try:
            url = f'https://finnhub.io/api/v1/stock/candle?symbol={asset}&resolution={resolution}&from={start_time}&to={end_time}&token={self.finnhub_api_key}'
            r = requests.get(url)
            r.raise_for_status()
            data = r.json()

            if data.get('s') == 'no_data' or not data.get('c'):
                logging.warning(f"Finnhub não retornou dados para {asset}.")
                return pd.DataFrame()

            df = pd.DataFrame(data)
            df['datetime'] = pd.to_datetime(df['t'], unit='s')
            df = df.set_index('datetime')
            df = df.rename(columns={'o': 'Open', 'h': 'High', 'l': 'Low', 'c': 'Close', 'v': 'Volume'})
            return df[['Open', 'High', 'Low', 'Close', 'Volume']]

        except requests.exceptions.RequestException as e:
            logging.error(f"Erro na chamada da API Finnhub para {asset}: {e}")
            return pd.DataFrame()
        except Exception as e:
            logging.error(f"Erro ao processar dados do Finnhub para {asset}: {e}")
            return pd.DataFrame()

    def _fetch_alphavantage_data(self, asset: str, period: str, interval: str) -> pd.DataFrame:
        if not self.alphavantage_api_key:
            logging.warning("Chave da API Alpha Vantage não configurada. Pulando.")
            return pd.DataFrame()

        logging.info(f"Buscando dados do Alpha Vantage para o ativo: {asset}")
        function_map = {
            '1m': 'TIME_SERIES_INTRADAY',
            '5m': 'TIME_SERIES_INTRADAY',
            '15m': 'TIME_SERIES_INTRADAY',
            '30m': 'TIME_SERIES_INTRADAY',
            '1h': 'TIME_SERIES_INTRADAY',
            '1d': 'TIME_SERIES_DAILY_ADJUSTED',
            '1wk': 'TIME_SERIES_WEEKLY_ADJUSTED',
            '1mo': 'TIME_SERIES_MONTHLY_ADJUSTED'
        }
        function = function_map.get(interval)
        if not function:
            logging.warning(f"Intervalo '{interval}' não suportado pelo Alpha Vantage.")
            return pd.DataFrame()

        # A Alpha Vantage tem uma estrutura de URL diferente para intraday
        if 'INTRADAY' in function:
            url = f'https://www.alphavantage.co/query?function={function}&symbol={asset}&interval={interval}&apikey={self.alphavantage_api_key}'
        else:
            url = f'https://www.alphavantage.co/query?function={function}&symbol={asset}&apikey={self.alphavantage_api_key}'

        try:
            r = requests.get(url)
            r.raise_for_status()
            data = r.json()

            # A chave principal da resposta varia com a função
            key = next(iter(data.keys()))
            if 'Time Series' not in key:
                 logging.warning(f"Alpha Vantage não retornou dados para {asset}. Resposta: {data}")
                 return pd.DataFrame()

            df = pd.DataFrame.from_dict(data[key], orient='index')
            df.index = pd.to_datetime(df.index)
            df = df.rename(columns={
                '1. open': 'Open',
                '2. high': 'High',
                '3. low': 'Low',
                '4. close': 'Close',
                '5. volume': 'Volume',
                '5. adjusted close': 'Adj Close', # Para diário/semanal/mensal
                '6. volume': 'Volume' # Para diário/semanal/mensal
            })
            # Garante que as colunas numéricas sejam do tipo float
            for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                if col in df.columns:
                    df[col] = df[col].astype(float)
            
            return df.sort_index()[['Open', 'High', 'Low', 'Close', 'Volume']]

        except requests.exceptions.RequestException as e:
            logging.error(f"Erro na chamada da API Alpha Vantage para {asset}: {e}")
            return pd.DataFrame()
        except Exception as e:
            logging.error(f"Erro ao processar dados do Alpha Vantage para {asset}: {e}")
            return pd.DataFrame()

    def fetch_historical_data(self, asset: str, period: str = "1mo", interval: str = "1d") -> pd.DataFrame:
        """
        Busca dados históricos de um ativo usando uma estratégia de fallback.
        Ordem: Cache -> yfinance -> Finnhub -> Alpha Vantage.
        """
        cache_path = self._get_cache_path(asset, period, interval)
        cached_data = self._load_from_cache(cache_path)
        if cached_data is not None:
            logging.info(f"Dados para {asset} carregados do cache.")
            return cached_data
        
        logging.info(f"Cache miss para {asset}. Buscando de fontes externas.")

        # Fonte 1: yfinance
        data = self._fetch_yfinance_data(asset, period, interval)
        if not data.empty:
            logging.info(f"Sucesso com yfinance para {asset}. Salvando no cache.")
            self._save_to_cache(data, cache_path)
            return data
        logging.warning(f"Falha ao buscar de yfinance para {asset}. Tentando próxima fonte.")

        # Fonte 2: Finnhub
        data = self._fetch_finnhub_data(asset, period, interval)
        if not data.empty:
            logging.info(f"Sucesso com Finnhub para {asset}. Salvando no cache.")
            self._save_to_cache(data, cache_path)
            return data
        logging.warning(f"Falha ao buscar de Finnhub para {asset}. Tentando próxima fonte.")
            
        # Fonte 3: Alpha Vantage
        data = self._fetch_alphavantage_data(asset, period, interval)
        if not data.empty:
            logging.info(f"Sucesso com Alpha Vantage para {asset}. Salvando no cache.")
            self._save_to_cache(data, cache_path)
            return data
        logging.warning(f"Falha ao buscar de Alpha Vantage para {asset}.")

        logging.error(f"Falha em todas as fontes para o ativo {asset}. Retornando DataFrame vazio.")
        return pd.DataFrame()