"""
Coletor de dados do CoinGecko.

Este módulo fornece funções para obter dados de criptomoedas
da API gratuita do CoinGecko.
"""
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union

import pandas as pd
import requests
from loguru import logger

from src.utils.config import settings
from src.utils.supabase_client import SupabaseHelper


class CoinGeckoCollector:
    """Coletor de dados do CoinGecko."""
    
    BASE_URL = "https://api.coingecko.com/api/v3"
    
    def __init__(self):
        """Inicializa o coletor."""
        self.supabase = SupabaseHelper()
        self.rate_limit_sleep = 1.5  # Sleep para evitar limites de requisição
    
    async def fetch_coins_list(self) -> List[Dict[str, Any]]:
        """
        Busca a lista de criptomoedas disponíveis.
        
        Returns:
            Lista de criptomoedas com ids, símbolos e nomes
        """
        endpoint = "/coins/list"
        
        try:
            response = self._make_get_request(endpoint)
            
            if response and isinstance(response, list):
                logger.info(f"Lista de criptomoedas obtida: {len(response)} moedas")
                return response
            
            return []
        except Exception as e:
            logger.error(f"Erro ao buscar lista de criptomoedas: {e}")
            return []
    
    async def fetch_coin_data(self, coin_id: str) -> Dict[str, Any]:
        """
        Busca informações detalhadas de uma criptomoeda.
        
        Args:
            coin_id: ID da moeda no CoinGecko (ex: bitcoin, ethereum)
            
        Returns:
            Dicionário com informações detalhadas
        """
        endpoint = f"/coins/{coin_id}"
        params = {
            "localization": "false",
            "tickers": "false",
            "market_data": "true",
            "community_data": "false",
            "developer_data": "false",
        }
        
        try:
            response = self._make_get_request(endpoint, params)
            
            if response and isinstance(response, dict):
                logger.info(f"Dados obtidos para {coin_id}")
                
                # Extrair informações relevantes
                market_data = response.get("market_data", {})
                
                return {
                    "id": response.get("id", coin_id),
                    "symbol": response.get("symbol", "").upper(),
                    "name": response.get("name", coin_id),
                    "current_price": market_data.get("current_price", {}).get("usd"),
                    "market_cap": market_data.get("market_cap", {}).get("usd"),
                    "market_cap_rank": market_data.get("market_cap_rank"),
                    "total_volume": market_data.get("total_volume", {}).get("usd"),
                    "high_24h": market_data.get("high_24h", {}).get("usd"),
                    "low_24h": market_data.get("low_24h", {}).get("usd"),
                    "price_change_24h": market_data.get("price_change_percentage_24h"),
                    "price_change_7d": market_data.get("price_change_percentage_7d"),
                    "price_change_30d": market_data.get("price_change_percentage_30d"),
                    "last_updated": market_data.get("last_updated"),
                    "image": response.get("image", {}).get("large"),
                }
            
            return {}
        except Exception as e:
            logger.error(f"Erro ao buscar dados para {coin_id}: {e}")
            return {}
    
    async def fetch_market_data(
        self,
        vs_currency: str = "usd",
        ids: Optional[List[str]] = None,
        category: Optional[str] = None,
        order: str = "market_cap_desc",
        per_page: int = 100,
        page: int = 1,
        sparkline: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Busca dados de mercado para múltiplas criptomoedas.
        
        Args:
            vs_currency: Moeda de referência (ex: usd, eur, btc)
            ids: Lista de IDs de criptomoedas específicas
            category: Categoria de criptomoedas (ex: defi, stablecoins)
            order: Ordenação (market_cap_desc, volume_desc, id_asc, etc)
            per_page: Resultados por página
            page: Número da página
            sparkline: Se True, inclui dados para gráfico sparkline
            
        Returns:
            Lista de dados de mercado de criptomoedas
        """
        endpoint = "/coins/markets"
        params = {
            "vs_currency": vs_currency,
            "order": order,
            "per_page": per_page,
            "page": page,
            "sparkline": sparkline,
        }
        
        if ids:
            params["ids"] = ",".join(ids)
        
        if category:
            params["category"] = category
        
        try:
            response = self._make_get_request(endpoint, params)
            
            if response and isinstance(response, list):
                logger.info(f"Dados de mercado obtidos: {len(response)} criptomoedas")
                return response
            
            return []
        except Exception as e:
            logger.error(f"Erro ao buscar dados de mercado: {e}")
            return []
    
    async def fetch_historical_data(
        self,
        coin_id: str,
        vs_currency: str = "usd",
        days: Union[int, str] = "max",
        interval: Optional[str] = "daily",
        save_to_db: bool = True,
    ) -> pd.DataFrame:
        """
        Busca dados históricos de preços de uma criptomoeda.
        
        Args:
            coin_id: ID da moeda no CoinGecko
            vs_currency: Moeda de referência
            days: Número de dias ou "max" para todo o histórico
            interval: Intervalo dos dados (daily, hourly, minutely)
            save_to_db: Se True, salva os dados no banco de dados
            
        Returns:
            DataFrame com dados históricos OHLCV
        """
        endpoint = f"/coins/{coin_id}/market_chart"
        params = {
            "vs_currency": vs_currency,
            "days": days,
            "interval": interval if interval else "daily",
        }
        
        try:
            response = self._make_get_request(endpoint, params)
            
            if response and isinstance(response, dict):
                # Extrair dados
                prices = response.get("prices", [])
                market_caps = response.get("market_caps", [])
                total_volumes = response.get("total_volumes", [])
                
                if not prices:
                    logger.warning(f"Nenhum dado de preço encontrado para {coin_id}")
                    return pd.DataFrame()
                
                # Criar DataFrame
                df = pd.DataFrame(prices, columns=["timestamp", "close"])
                
                # Converter timestamp de milissegundos para datetime
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
                
                # Adicionar volumes e market caps se disponíveis
                if total_volumes and len(total_volumes) == len(prices):
                    df["volume"] = [v[1] for v in total_volumes]
                else:
                    df["volume"] = 0
                
                # O CoinGecko não fornece OHLC completo, apenas preço de fechamento
                # Vamos usar o valor de fechamento para outros campos
                df["open"] = df["close"]
                df["high"] = df["close"]
                df["low"] = df["close"]
                
                # Para dados diários, podemos tentar reconstruir OHLC
                if interval == "daily" and len(df) > 1:
                    # Tentar buscar dados OHLC separadamente
                    ohlc_df = await self._fetch_ohlc(coin_id, vs_currency, days)
                    
                    if not ohlc_df.empty:
                        # Mesclar com os dados de preço
                        df = ohlc_df
                
                # Converter de volta para string ISO
                df["timestamp"] = df["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%S%z")
                
                # Reordenar colunas
                df = df[["timestamp", "open", "high", "low", "close", "volume"]]
                
                # Salvar no banco de dados
                if save_to_db:
                    symbol = coin_id.upper()
                    await self._save_price_data(symbol, df, self._map_interval(interval))
                
                logger.info(f"Dados históricos obtidos para {coin_id}: {len(df)} registros")
                return df
            
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Erro ao buscar dados históricos para {coin_id}: {e}")
            return pd.DataFrame()
    
    async def _fetch_ohlc(
        self,
        coin_id: str,
        vs_currency: str = "usd",
        days: Union[int, str] = 30,
    ) -> pd.DataFrame:
        """
        Busca dados OHLC (Open, High, Low, Close) de uma criptomoeda.
        
        Args:
            coin_id: ID da moeda no CoinGecko
            vs_currency: Moeda de referência
            days: Número de dias (1, 7, 14, 30, 90, 180, 365, max)
            
        Returns:
            DataFrame com dados OHLC
        """
        # API do CoinGecko só aceita valores específicos para days
        valid_days = [1, 7, 14, 30, 90, 180, 365]
        if isinstance(days, int) and days not in valid_days:
            days = min(valid_days, key=lambda x: abs(x - days))
        elif days != "max":
            days = 30  # valor padrão
        
        endpoint = f"/coins/{coin_id}/ohlc"
        params = {
            "vs_currency": vs_currency,
            "days": days,
        }
        
        try:
            response = self._make_get_request(endpoint, params)
            
            if response and isinstance(response, list):
                # Formato: [timestamp, open, high, low, close]
                df = pd.DataFrame(response, columns=["timestamp", "open", "high", "low", "close"])
                
                # Converter timestamp de milissegundos para datetime
                df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
                
                # Adicionar volume (não disponível na API OHLC)
                df["volume"] = 0
                
                return df
            
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Erro ao buscar dados OHLC para {coin_id}: {e}")
            return pd.DataFrame()
    
    async def update_assets_info(self, top_n: int = 100) -> List[Dict[str, Any]]:
        """
        Atualiza informações das principais criptomoedas no banco de dados.
        
        Args:
            top_n: Número de criptomoedas a atualizar (por market cap)
            
        Returns:
            Lista de informações atualizadas
        """
        try:
            # Buscar top N criptomoedas por market cap
            market_data = await self.fetch_market_data(per_page=top_n, page=1)
            
            assets_info = []
            
            for crypto in market_data:
                try:
                    # Criar objeto de ativo
                    asset_info = {
                        "symbol": crypto.get("symbol", "").upper(),
                        "name": crypto.get("name", ""),
                        "type": "crypto",
                        "data_source": "coingecko",
                        "last_updated": datetime.now().isoformat(),
                        "metadata": {
                            "coingecko_id": crypto.get("id", ""),
                            "image": crypto.get("image", ""),
                            "current_price": crypto.get("current_price"),
                            "market_cap": crypto.get("market_cap"),
                            "market_cap_rank": crypto.get("market_cap_rank"),
                            "price_change_24h": crypto.get("price_change_percentage_24h"),
                        }
                    }
                    
                    assets_info.append(asset_info)
                    
                    # Upsert no banco de dados
                    await self.supabase.upsert_assets([asset_info])
                    
                    # Aguardar para evitar rate limiting
                    time.sleep(self.rate_limit_sleep)
                    
                except Exception as e:
                    logger.error(f"Erro ao processar criptomoeda {crypto.get('id')}: {e}")
            
            logger.info(f"Atualizadas informações de {len(assets_info)} criptomoedas")
            return assets_info
        
        except Exception as e:
            logger.error(f"Erro ao atualizar informações de criptomoedas: {e}")
            return []
    
    async def fetch_all_supported_coins(self) -> List[Dict[str, Any]]:
        """
        Obtém informações básicas de todas as criptomoedas suportadas pelo CoinGecko.
        
        Returns:
            Lista de criptomoedas com detalhes básicos
        """
        try:
            # Primeiro obter a lista completa de IDs
            coins_list = await self.fetch_coins_list()
            
            # Filtrar apenas moedas com volume significativo
            # Fazemos isso buscando em lotes de 250 por vez
            all_coins = []
            page = 1
            per_page = 250
            
            while True:
                market_data = await self.fetch_market_data(per_page=per_page, page=page)
                
                if not market_data:
                    break
                
                all_coins.extend(market_data)
                
                if len(market_data) < per_page:
                    break
                
                page += 1
                time.sleep(self.rate_limit_sleep)  # Respeitar rate limit
            
            # Converter para formato de ativos
            assets = []
            for coin in all_coins:
                assets.append({
                    "symbol": coin.get("symbol", "").upper(),
                    "name": coin.get("name", ""),
                    "type": "crypto",
                    "data_source": "coingecko",
                    "last_updated": datetime.now().isoformat(),
                    "metadata": {
                        "coingecko_id": coin.get("id", ""),
                        "image": coin.get("image", ""),
                        "current_price": coin.get("current_price"),
                        "market_cap": coin.get("market_cap"),
                        "market_cap_rank": coin.get("market_cap_rank"),
                    }
                })
            
            logger.info(f"Obtidas informações de {len(assets)} criptomoedas")
            return assets
        except Exception as e:
            logger.error(f"Erro ao buscar todas as criptomoedas: {e}")
            return []
    
    def _make_get_request(self, endpoint: str, params: Dict[str, Any] = None) -> Any:
        """
        Faz uma requisição GET para a API do CoinGecko.
        
        Args:
            endpoint: Endpoint da API
            params: Parâmetros da requisição
            
        Returns:
            Resposta da API (geralmente dict ou list)
        """
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 429:
                # Rate limit atingido, aguardar e tentar novamente
                logger.warning("Rate limit atingido, aguardando 30 segundos")
                time.sleep(30)
                return self._make_get_request(endpoint, params)
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro na requisição para {url}: {e}")
            return None
    
    async def _save_price_data(self, symbol: str, df: pd.DataFrame, interval: str) -> bool:
        """
        Salva dados de preço no banco de dados.
        
        Args:
            symbol: Símbolo do ativo
            df: DataFrame com dados
            interval: Intervalo entre os dados
            
        Returns:
            True se salvou com sucesso, False caso contrário
        """
        if df.empty:
            return False
        
        try:
            # Converter DataFrame para registros
            records = df.to_dict("records")
            
            # Adicionar identificadores
            for record in records:
                record["symbol"] = symbol
                record["timeframe"] = interval
            
            # Upsert no banco de dados usando a tabela price_history
            if hasattr(self.supabase, "upsert_price_data"):
                await self.supabase.upsert_price_data(records)
            
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar dados de preço para {symbol}: {e}")
            return False
    
    def _map_interval(self, interval: Optional[str]) -> str:
        """
        Mapeia o intervalo do CoinGecko para formato padrão.
        
        Args:
            interval: Intervalo no formato CoinGecko
            
        Returns:
            Intervalo no formato padrão (1m, 1h, 1d, etc)
        """
        if interval == "minutely":
            return "1m"
        elif interval == "hourly":
            return "1h"
        elif interval == "daily":
            return "1d"
        else:
            return "1d"  # padrão


# Função para obter uma instância do coletor
def get_coingecko_collector() -> CoinGeckoCollector:
    """Retorna uma instância do coletor do CoinGecko."""
    return CoinGeckoCollector() 