"""
Coletor de dados financeiros da API do Yahoo Finance.

Este módulo implementa a coleta de dados históricos usando yfinance,
fornecendo preços OHLCV para diversos ativos.
"""
import asyncio
import datetime
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Union, Any

import numpy as np
import pandas as pd
import yfinance as yf
from loguru import logger

from src.utils.config import settings
from src.utils.data_helpers import create_backup_file, save_json
from src.utils.supabase_client import get_supabase_client, refresh_supabase_connection

# Caminho para dados de backup
BACKUP_DIR = Path("data/backup")
os.makedirs(BACKUP_DIR, exist_ok=True)


class YahooFinanceCollector:
    """Coletor de dados da API Yahoo Finance."""

    def __init__(self):
        """Inicializa o coletor de dados do Yahoo Finance."""
        self.supabase = get_supabase_client()
        logger.info("Coletor Yahoo Finance inicializado")

    async def fetch_historical_data(
        self, symbol: str, period: str = "1y", interval: str = "1d"
    ) -> Optional[pd.DataFrame]:
        """
        Obtém dados históricos para um símbolo usando yfinance.

        Args:
            symbol: Símbolo do ativo (ex: AAPL)
            period: Período de tempo ("1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max")
            interval: Intervalo de tempo ("1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo")

        Returns:
            DataFrame com dados históricos ou None em caso de erro
        """
        try:
            logger.info(f"Buscando dados históricos para {symbol} (período: {period}, intervalo: {interval})")
            
            # Usar yfinance para obter dados
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period, interval=interval)
            
            if data.empty:
                logger.warning(f"Nenhum dado histórico encontrado para {symbol}")
                return None
                
            # Renomear colunas para formato padrão
            data.reset_index(inplace=True)
            
            # Preparar dados para armazenamento
            data.columns = [col.lower() for col in data.columns]
            data.rename(columns={"date": "timestamp", "stock splits": "stock_splits"}, inplace=True)
            
            # Certificar que timestamp é datetime
            if not pd.api.types.is_datetime64_any_dtype(data["timestamp"]):
                data["timestamp"] = pd.to_datetime(data["timestamp"])
            
            return data
        except Exception as e:
            logger.error(f"Erro ao buscar dados históricos para {symbol}: {e}")
            return None

    async def batch_fetch_historical_data(
        self, symbols: List[str], period: str = "1y", interval: str = "1d"
    ) -> Dict[str, pd.DataFrame]:
        """
        Obtém dados históricos para múltiplos símbolos.

        Args:
            symbols: Lista de símbolos
            period: Período de tempo
            interval: Intervalo de tempo

        Returns:
            Dicionário com dados históricos por símbolo
        """
        results = {}
        for symbol in symbols:
            data = await self.fetch_historical_data(symbol, period, interval)
            if data is not None:
                await self.save_price_data(symbol, data, interval)
                results[symbol] = data
                logger.info(f"Dados obtidos para {symbol}: {len(data)} registros")
            else:
                logger.warning(f"Falha ao obter dados para {symbol}")
                
            # Pausa para evitar limitações de API
            await asyncio.sleep(0.5)
            
        return results

    async def save_price_data(self, symbol: str, data: pd.DataFrame, timeframe: str) -> bool:
        """
        Salva dados de preço no Supabase.

        Args:
            symbol: Símbolo do ativo
            data: DataFrame com dados históricos
            timeframe: Intervalo de tempo (1m, 5m, 1h, 1d, etc)

        Returns:
            bool: True se bem-sucedido, False caso contrário
        """
        try:
            # Transformar DataFrame em lista de dicionários para inserção
            records = []
            
            for _, row in data.iterrows():
                # Ignorar valores NaN
                if np.isnan(row.get("open", np.nan)) or np.isnan(row.get("close", np.nan)):
                    continue
                    
                record = {
                    "symbol": symbol,
                    "timestamp": row["timestamp"].isoformat(),
                    "timeframe": timeframe,
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": float(row["volume"]) if "volume" in row and not np.isnan(row["volume"]) else None,
                    "source": "yahoo_finance"
                }
                records.append(record)
            
            # Criar backup local dos dados
            filename = f"price_data_{symbol}_{timeframe}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            backup_path = BACKUP_DIR / filename
            save_json(records, backup_path)
            logger.info(f"Dados de preço salvos localmente em {backup_path}")
            
            # Inserir no Supabase
            try:
                # Tentar reconectar para atualizar o cache do schema se necessário
                refresh_supabase_connection()
                
                # Inserir registros com conflito nas colunas indicadas
                self.supabase.table("price_history").upsert(
                    records,
                    on_conflict=["symbol", "timestamp", "timeframe"]
                ).execute()
                return True
            except Exception as e:
                logger.error(f"Erro ao upsert dados de preço no Supabase: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao salvar dados de preço para {symbol}: {e}")
            return False

    async def get_asset_info(self, symbol: str) -> Dict[str, Any]:
        """
        Obtém informações detalhadas sobre um ativo.

        Args:
            symbol: Símbolo do ativo

        Returns:
            Dicionário com informações do ativo
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Determinar o tipo de ativo
            asset_type = "stock"
            if symbol.endswith("=X"):
                asset_type = "forex"
            elif symbol.startswith("^"):
                asset_type = "index"
            elif "-USD" in symbol:
                asset_type = "crypto"
                
            # Extrair campos relevantes
            asset_info = {
                "symbol": symbol,
                "name": info.get("shortName", info.get("longName", symbol)),
                "asset_type": asset_type,
                "currency": info.get("currency", "USD"),
                "last_price": info.get("regularMarketPrice", info.get("previousClose", None)),
                "exchange": info.get("exchange", None),
                "active": True,
                "api_source": "yahoo_finance"
            }
            
            return asset_info
        except Exception as e:
            logger.error(f"Erro ao obter informações para {symbol}: {e}")
            return {
                "symbol": symbol,
                "name": symbol,
                "asset_type": "unknown",
                "currency": "USD",
                "active": True,
                "api_source": "yahoo_finance"
            }

    async def update_assets_info(self, symbols: List[str]) -> int:
        """
        Atualiza informações de múltiplos ativos no Supabase.

        Args:
            symbols: Lista de símbolos

        Returns:
            int: Número de ativos atualizados
        """
        updated = 0
        
        for symbol in symbols:
            try:
                logger.info(f"Buscando informações para {symbol}")
                asset_info = await self.get_asset_info(symbol)
                
                try:
                    # Reconectar para atualizar o cache do schema
                    refresh_supabase_connection()
                    
                    # Inserir ou atualizar no Supabase
                    self.supabase.table("assets").upsert(
                        asset_info,
                        on_conflict=["symbol"]
                    ).execute()
                    
                    updated += 1
                except Exception as e:
                    logger.error(f"Erro ao upsert ativos no Supabase: {e}")
            except Exception as e:
                logger.error(f"Erro ao atualizar informações para {symbol}: {e}")
                
            # Pausa para evitar limitações de API
            await asyncio.sleep(0.5)
                
        return updated


# Instância singleton
_yahoo_finance_collector = None

def get_yahoo_finance_collector() -> YahooFinanceCollector:
    """
    Retorna uma instância singleton do YahooFinanceCollector.
    
    Returns:
        YahooFinanceCollector: Instância do coletor
    """
    global _yahoo_finance_collector
    
    if _yahoo_finance_collector is None:
        _yahoo_finance_collector = YahooFinanceCollector()
        
    return _yahoo_finance_collector


async def run_collector():
    """Executa o coletor para demonstração."""
    collector = get_yahoo_finance_collector()
    
    # Exemplo: coletar dados para algumas ações
    symbols = ["AAPL", "MSFT", "GOOGL"]
    results = await collector.batch_fetch_historical_data(symbols, period="1mo", interval="1d")
    
    # Imprimir resultados
    for symbol, data in results.items():
        if data is not None:
            print(f"{symbol}: {len(data)} registros")


if __name__ == "__main__":
    asyncio.run(run_collector()) 