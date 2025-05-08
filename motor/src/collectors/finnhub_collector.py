"""
Coletor de dados da API Finnhub.

Este módulo fornece uma implementação para coleta de dados de mercado
usando a API Finnhub (https://finnhub.io/).
"""
import asyncio
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union

import finnhub
import pandas as pd
from dotenv import load_dotenv
from loguru import logger

from src.utils.config import settings
from src.utils.supabase_client import get_supabase_client, refresh_supabase_connection

# Carregar variáveis de ambiente
load_dotenv()


class FinnhubCollector:
    """Implementação do coletor para a API Finnhub."""

    def __init__(self):
        """Inicializa o coletor Finnhub."""
        self.api_key = settings.FINNHUB_API_KEY
        if not self.api_key:
            raise ValueError("FINNHUB_API_KEY não está configurado nas variáveis de ambiente")
            
        self.client = finnhub.Client(api_key=self.api_key)
        self.supabase = get_supabase_client()
        logger.info(f"Coletor Finnhub inicializado")

    async def fetch_stock_symbols(self, exchange: str = "US") -> List[Dict[str, Any]]:
        """
        Obtém lista de símbolos de ações disponíveis.
        
        Args:
            exchange: Código da bolsa (US, L, HK, etc.)
            
        Returns:
            Lista de dicionários com símbolos
        """
        try:
            # Chamar a API Finnhub
            stocks = self.client.stock_symbols(exchange)
            
            assets = []
            for stock in stocks:
                if not stock.get('symbol'):
                    continue
                    
                asset = {
                    "symbol": stock.get('symbol'),
                    "name": stock.get('description', stock.get('displaySymbol', stock.get('symbol'))),
                    "asset_type": "stock",
                    "currency": "USD",  # Padrão para ações US
                    "exchange": stock.get('mic', exchange),
                    "active": True,
                    "api_source": "finnhub"
                }
                assets.append(asset)
                
            logger.info(f"Obtidos {len(assets)} símbolos da bolsa {exchange}")
            return assets
        except Exception as e:
            logger.error(f"Erro ao buscar símbolos da bolsa {exchange}: {e}")
            return []

    async def fetch_forex_symbols(self) -> List[Dict[str, Any]]:
        """
        Obtém lista de pares forex disponíveis.
        
        Returns:
            Lista de dicionários com símbolos
        """
        try:
            # Chamar a API Finnhub
            forex_data = self.client.forex_symbols("OANDA")
            
            assets = []
            for pair in forex_data:
                if not pair.get('symbol'):
                    continue
                    
                asset = {
                    "symbol": pair.get('symbol'),
                    "name": pair.get('displaySymbol', pair.get('symbol')),
                    "asset_type": "forex",
                    "currency": pair.get('symbol').split(':')[-1][:3] if ':' in pair.get('symbol') else "USD",
                    "exchange": "OANDA",
                    "active": True,
                    "api_source": "finnhub"
                }
                assets.append(asset)
                
            logger.info(f"Obtidos {len(assets)} pares forex")
            return assets
        except Exception as e:
            logger.error(f"Erro ao buscar pares forex: {e}")
            return []

    async def fetch_crypto_symbols(self, exchange: str = "BINANCE") -> List[Dict[str, Any]]:
        """
        Obtém lista de pares de criptomoedas disponíveis.
        
        Args:
            exchange: Nome da exchange (BINANCE, COINBASE, etc.)
            
        Returns:
            Lista de dicionários com símbolos
        """
        try:
            # Chamar a API Finnhub
            crypto_data = self.client.crypto_symbols(exchange)
            
            assets = []
            for crypto in crypto_data:
                if not crypto.get('symbol'):
                    continue
                    
                # Extrair símbolos da moeda base e cotação
                symbol_parts = crypto.get('symbol', '').split(':')[-1].split('-')
                base_currency = symbol_parts[0] if len(symbol_parts) > 0 else ""
                quote_currency = symbol_parts[1] if len(symbol_parts) > 1 else "USD"
                
                asset = {
                    "symbol": crypto.get('symbol'),
                    "name": crypto.get('displaySymbol', crypto.get('symbol')),
                    "asset_type": "crypto",
                    "currency": quote_currency,
                    "exchange": exchange,
                    "active": True,
                    "api_source": "finnhub",
                    "metadata": {
                        "base_currency": base_currency,
                        "quote_currency": quote_currency
                    }
                }
                assets.append(asset)
                
            logger.info(f"Obtidos {len(assets)} pares de criptomoedas da {exchange}")
            return assets
        except Exception as e:
            logger.error(f"Erro ao buscar pares de criptomoedas da {exchange}: {e}")
            return []

    async def fetch_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Obtém cotação atual para um símbolo.
        
        Args:
            symbol: Símbolo do ativo
            
        Returns:
            Dicionário com dados da cotação
        """
        try:
            # Chamar a API Finnhub
            quote = self.client.quote(symbol)
            
            if not quote:
                logger.warning(f"Nenhuma cotação encontrada para {symbol}")
                return {}
                
            # Adicionar timestamp e símbolo
            quote["symbol"] = symbol
            quote["timestamp"] = datetime.now().isoformat()
            
            return quote
        except Exception as e:
            logger.error(f"Erro ao buscar cotação para {symbol}: {e}")
            return {}

    async def fetch_and_store_assets(self) -> int:
        """
        Busca e armazena ativos de diferentes tipos.
        
        Returns:
            Número total de ativos armazenados
        """
        try:
            # Obter ativos de diferentes fontes
            stocks = await self.fetch_stock_symbols("US")
            forex = await self.fetch_forex_symbols()
            crypto = await self.fetch_crypto_symbols("BINANCE")
            
            # Combinar todos os ativos
            all_assets = stocks + forex + crypto
            logger.info(f"Coletados {len(all_assets)} ativos via Finnhub")
            
            try:
                # Reconectar para atualizar o cache do schema
                refresh_supabase_connection()
                
                # Inserir no Supabase
                # Armazenar em lotes para evitar problemas de tamanho de requisição
                batch_size = 100
                for i in range(0, len(all_assets), batch_size):
                    batch = all_assets[i:i+batch_size]
                    self.supabase.table("assets").upsert(
                        batch, 
                        on_conflict=["symbol"]
                    ).execute()
                
                return len(all_assets)
            except Exception as e:
                logger.error(f"Erro ao upsert ativos no Supabase: {e}")
                raise
        except Exception as e:
            logger.error(f"Erro ao armazenar ativos no Supabase: {e}")
            return 0

    async def update_asset_prices(self, limit: int = 100) -> int:
        """
        Atualiza preços dos ativos armazenados.
        
        Args:
            limit: Número máximo de ativos para atualizar
            
        Returns:
            Número de ativos atualizados
        """
        try:
            # Reconectar para atualizar o cache do schema
            refresh_supabase_connection()
            
            # Buscar ativos ativos no banco
            assets_result = self.supabase.table("assets").select("symbol").eq("active", True).limit(limit).execute()
            assets = assets_result.data
            
            if not assets:
                logger.warning("Nenhum ativo encontrado para atualizar preços")
                return 0
                
            updated = 0
            for asset in assets:
                symbol = asset.get("symbol")
                if not symbol:
                    continue
                    
                quote = await self.fetch_quote(symbol)
                if not quote or "c" not in quote:
                    continue
                    
                # Atualizar preço do ativo
                try:
                    self.supabase.table("assets").update({
                        "last_price": quote.get("c"),  # Preço atual
                        "updated_at": datetime.now().isoformat()
                    }).eq("symbol", symbol).execute()
                    updated += 1
                except Exception as e:
                    logger.error(f"Erro ao atualizar preço de {symbol}: {e}")
                
                # Evitar rate limiting
                await asyncio.sleep(0.2)
                
            logger.info(f"Atualizados preços de {updated}/{len(assets)} ativos")
            return updated
        except Exception as e:
            logger.error(f"Erro ao atualizar preços dos ativos: {e}")
            return 0


# Criar uma instância singleton do coletor
_finnhub_collector = None

def get_finnhub_collector() -> FinnhubCollector:
    """
    Retorna uma instância singleton do FinnhubCollector.
    
    Returns:
        FinnhubCollector: Instância do coletor Finnhub
    """
    global _finnhub_collector
    
    if _finnhub_collector is None:
        try:
            _finnhub_collector = FinnhubCollector()
        except Exception as e:
            logger.error(f"Erro ao criar FinnhubCollector: {e}")
            raise
    
    return _finnhub_collector


async def run_collector():
    """Executa o coletor para demonstração."""
    collector = get_finnhub_collector()
    
    # Buscar e armazenar ativos
    await collector.fetch_and_store_assets()
    
    # Atualizar preços
    await collector.update_asset_prices(limit=20)


if __name__ == "__main__":
    asyncio.run(run_collector()) 