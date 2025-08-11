"""
Coletor de dados de mercado em tempo real.

Este módulo implementa a coleta de dados em tempo real usando a API do Yahoo Finance
para todos os ativos configurados, incluindo preços atualizados e informações do mercado.
"""
import asyncio
import datetime
import time
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Tuple

import pandas as pd
import numpy as np
import yfinance as yf
from src.utils.logger import setup_logger

logger = setup_logger("realtime_market_data", "realtime_market_data.log")

from src.utils.config import settings
from src.utils.supabase_client import get_supabase_client, refresh_supabase_connection
from src.processors import signal_generator
from src.collectors.asset_list import (
    ALL_ASSETS, 
    get_symbols_by_category, 
    get_asset_info,
    search_assets
)

# Configuração de diretório para dados de backup
BACKUP_DIR = Path("data/backup/realtime")
os.makedirs(BACKUP_DIR, exist_ok=True)

class RealtimeMarketData:
    """Coletor de dados de mercado em tempo real."""

    def __init__(self):
        """Inicializa o coletor de dados de mercado em tempo real."""
        self.supabase = get_supabase_client()
        self.realtime_data = {}  # Cache temporário de dados em tempo real
        self.last_update = {}  # Registro do último momento de atualização por símbolo
        self.update_interval = 30  # Intervalo mínimo entre atualizações (segundos)
        
        # Ativos que estão sendo monitorados ativamente
        self.active_symbols = set()
        
        logger.info("Coletor de dados de mercado em tempo real inicializado")

    async def get_realtime_price(self, symbol: str, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Obtém o preço em tempo real de um ativo.
        
        Args:
            symbol: Símbolo do ativo
            force_refresh: Se True, força a atualização mesmo que o cache esteja recente
            
        Returns:
            Dicionário com dados em tempo real
        """
        current_time = time.time()
        
        # Verificar se precisamos atualizar o dado (cache expirado ou forçado)
        if (symbol not in self.last_update or 
                current_time - self.last_update.get(symbol, 0) > self.update_interval or
                force_refresh):
            
            try:
                logger.info(f"Buscando preço em tempo real para {symbol}")
                
                # Usar yfinance para obter dados em tempo real
                ticker = yf.Ticker(symbol)
                info = ticker.info
                
                # Obter último preço
                last_price = info.get('regularMarketPrice', info.get('currentPrice', None))
                
                # Obter outros dados relevantes
                open_price = info.get('regularMarketOpen', None)
                high_price = info.get('regularMarketDayHigh', None)
                low_price = info.get('regularMarketDayLow', None)
                volume = info.get('regularMarketVolume', None)
                market_cap = info.get('marketCap', None)
                fifty_two_week_high = info.get('fiftyTwoWeekHigh', None)
                fifty_two_week_low = info.get('fiftyTwoWeekLow', None)
                trailing_pe = info.get('trailingPE', None)
                
                # Verificar se temos um preço válido
                if last_price is None:
                    # Tentar uma abordagem alternativa para obter o preço
                    history = ticker.history(period="1d")
                    if not history.empty:
                        last_price = history['Close'][-1]
                
                # Preparar dados
                price_data = {
                    'symbol': symbol,
                    'last_price': last_price,
                    'timestamp': datetime.datetime.now().isoformat(),
                    'open': open_price,
                    'high': high_price,
                    'low': low_price,
                    'volume': volume,
                    'market_cap': market_cap,
                    '52_week_high': fifty_two_week_high,
                    '52_week_low': fifty_two_week_low,
                    'pe_ratio': trailing_pe,
                    'source': 'yahoo_finance'
                }
                
                # Atualizar cache e timestamp
                self.realtime_data[symbol] = price_data
                self.last_update[symbol] = current_time
                
                # Adicionar à lista de símbolos ativos
                self.active_symbols.add(symbol)
                
                return price_data
                
            except Exception as e:
                logger.error(f"Erro ao buscar preço em tempo real para {symbol}: {e}")
                if symbol in self.realtime_data:
                    # Retornar dados antigos com flag de erro
                    self.realtime_data[symbol]['error'] = str(e)
                    return self.realtime_data[symbol]
                return {
                    'symbol': symbol,
                    'error': str(e),
                    'timestamp': datetime.datetime.now().isoformat()
                }
        else:
            # Retornar dados em cache
            return self.realtime_data.get(symbol, {
                'symbol': symbol,
                'error': 'Dados não disponíveis',
                'timestamp': datetime.datetime.now().isoformat()
            })

    async def get_bulk_realtime_prices(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Obtém preços em tempo real para múltiplos símbolos.
        
        Args:
            symbols: Lista de símbolos
            
        Returns:
            Dicionário com dados em tempo real por símbolo
        """
        results = {}
        tasks = []
        
        # Criar tarefas para buscar cada símbolo
        for symbol in symbols:
            task = asyncio.create_task(self.get_realtime_price(symbol))
            tasks.append((symbol, task))
        
        # Aguardar todas as tarefas completarem
        for symbol, task in tasks:
            try:
                result = await task
                results[symbol] = result
            except Exception as e:
                logger.error(f"Erro ao buscar preço em tempo real para {symbol}: {e}")
                results[symbol] = {
                    'symbol': symbol,
                    'error': str(e),
                    'timestamp': datetime.datetime.now().isoformat()
                }
        
        return results

    async def save_realtime_data(self, data: Dict[str, Any]) -> bool:
        """
        Salva dados em tempo real no Supabase.
        
        Args:
            data: Dicionário com dados em tempo real
            
        Returns:
            bool: True se bem-sucedido, False caso contrário
        """
        try:
            # Montar registro para inserção
            record = {
                'symbol': data['symbol'],
                'timestamp': data['timestamp'],
                'price': data.get('last_price', None),
                'open': data.get('open', None),
                'high': data.get('high', None),
                'low': data.get('low', None),
                'volume': data.get('volume', None),
                'market_cap': data.get('market_cap', None),
                'pe_ratio': data.get('pe_ratio', None),
                'source': data.get('source', 'yahoo_finance')
            }
            
            # Reconectar para atualizar o cache do schema se necessário
            refresh_supabase_connection()
            
            # Inserir no Supabase
            self.supabase.table('realtime_market_data').upsert(
                record,
                on_conflict=['symbol', 'timestamp']
            ).execute()
            
            # Atualizar também a tabela de assets
            asset_record = {
                'symbol': data['symbol'],
                'last_price': data.get('last_price', None),
                'last_update': data['timestamp'],
                'active': True
            }
            
            self.supabase.table('assets').update(
                asset_record
            ).eq('symbol', data['symbol']).execute()
            
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar dados em tempo real: {e}")
            return False

    async def monitor_active_symbols(self, interval: int = 60) -> None:
        """
        Monitora continuamente os símbolos ativos, atualizando seus preços.
        
        Args:
            interval: Intervalo entre atualizações em segundos
        """
        logger.info(f"Iniciando monitoramento de símbolos ativos a cada {interval} segundos")
        
        while True:
            if not self.active_symbols:
                logger.info("Nenhum símbolo ativo para monitorar. Aguardando...")
                await asyncio.sleep(interval)
                continue
            
            active_symbols_list = list(self.active_symbols)
            logger.info(f"Monitorando {len(active_symbols_list)} símbolos ativos")
            
            # Atualizar dados em lotes para evitar sobrecarga
            batch_size = 10
            for i in range(0, len(active_symbols_list), batch_size):
                batch = active_symbols_list[i:i+batch_size]
                logger.debug(f"Processando lote {i//batch_size + 1}/{(len(active_symbols_list)-1)//batch_size + 1}")
                
                results = await self.get_bulk_realtime_prices(batch)
                
                # Salvar resultados no banco de dados
                for symbol, data in results.items():
                    if 'error' not in data and data.get('last_price'):
                        await self.save_realtime_data(data)
                
                # Breve pausa entre lotes
                if i + batch_size < len(active_symbols_list):
                    await asyncio.sleep(2)
            
            # Aguardar até o próximo ciclo
            await asyncio.sleep(interval)

    async def get_category_market_summary(self, category: str) -> List[Dict[str, Any]]:
        """
        Obtém um resumo de mercado para uma categoria específica de ativos.
        
        Args:
            category: Categoria ('stocks', 'indices', 'forex', 'crypto', 'cfds')
            
        Returns:
            Lista de dicionários com resumo de cada ativo
        """
        symbols = get_symbols_by_category(category)
        results = []
        
        # Obter dados em lotes para evitar sobrecarga
        batch_size = 10
        for i in range(0, len(symbols), batch_size):
            batch = symbols[i:i+batch_size]
            batch_data = await self.get_bulk_realtime_prices(batch)
            
            for symbol, data in batch_data.items():
                if 'error' not in data:
                    asset_info = get_asset_info(symbol)
                    name = asset_info[1] if asset_info else symbol
                    
                    # Adicionar ao resultado
                    results.append({
                        'symbol': symbol,
                        'name': name,
                        'price': data.get('last_price'),
                        'change': None,  # Será calculado futuramente
                        'volume': data.get('volume'),
                        'timestamp': data.get('timestamp')
                    })
            
            # Breve pausa entre lotes
            if i + batch_size < len(symbols):
                await asyncio.sleep(1)
        
        return results

    async def initialize_assets_table(self) -> int:
        """
        Inicializa a tabela de ativos no Supabase com todos os ativos configurados.
        
        Returns:
            int: Número de ativos atualizados
        """
        logger.info("Inicializando tabela de ativos no Supabase")
        count = 0
        
        # Obter todos os símbolos
        all_assets = ALL_ASSETS
        
        # Processar em lotes
        batch_size = 10
        for i in range(0, len(all_assets), batch_size):
            batch = all_assets[i:i+batch_size]
            
            for symbol, name, description in batch:
                try:
                    # Extrair tipo do ativo baseado no símbolo
                    asset_type = "stock"  # padrão
                    
                    if symbol.endswith("=X"):
                        asset_type = "forex"
                    elif "-USD" in symbol:
                        asset_type = "crypto"
                    elif symbol.startswith("^"):
                        asset_type = "index"
                    elif symbol.endswith("=F"):
                        asset_type = "cfd"
                    
                    # Preparar registro
                    asset_record = {
                        'symbol': symbol,
                        'name': name,
                        'description': description,
                        'asset_type': asset_type,
                        'active': True,
                        'source': 'yahoo_finance'
                    }
                    
                    # Inserir/atualizar no Supabase
                    refresh_supabase_connection()
                    self.supabase.table('assets').upsert(
                        asset_record,
                        on_conflict=['symbol']
                    ).execute()
                    
                    count += 1
                    logger.debug(f"Ativo {symbol} atualizado com sucesso")
                    
                except Exception as e:
                    logger.error(f"Erro ao atualizar ativo {symbol}: {e}")
            
            # Breve pausa entre lotes
            if i + batch_size < len(all_assets):
                await asyncio.sleep(1)
        
        logger.info(f"Atualização de ativos concluída: {count} ativos processados")
        return count


# Singleton para acesso global
_realtime_data_instance = None

def get_realtime_market_data() -> RealtimeMarketData:
    """
    Obtém uma instância do coletor de dados de mercado em tempo real.
    
    Returns:
        RealtimeMarketData: Instância singleton
    """
    global _realtime_data_instance
    if _realtime_data_instance is None:
        _realtime_data_instance = RealtimeMarketData()
    return _realtime_data_instance


async def run_realtime_collector():
    """
    Ponto de entrada para execução do coletor em tempo real e acionamento da geração de sinais.
    """
    collector = get_realtime_market_data()

    # Inicializar tabela de ativos
    await collector.initialize_assets_table()

    all_symbols = [asset[0] for asset in ALL_ASSETS]
    
    logger.info(f"Iniciando monitoramento para {len(all_symbols)} ativos...")
    
    last_signal_generation_time = 0
    signal_generation_interval = 300  # 5 minutos

    while True:
        try:
            current_time = time.time()
            logger.info("Iniciando novo ciclo de coleta...")
            
            # Obter dados em tempo real para todos os ativos
            realtime_data = await collector.get_bulk_realtime_prices(all_symbols)
            
            # Salvar dados no Supabase
            for symbol, data in realtime_data.items():
                if 'error' not in data and data.get('last_price'):
                    await collector.save_realtime_data(data)
                else:
                    logger.warning(f"Não foi possível salvar dados para {symbol}: {data.get('error', 'Dados ausentes')}")

            # Acionar geração de sinais periodicamente
            if current_time - last_signal_generation_time > signal_generation_interval:
                logger.info("Acionando a geração de sinais...")
                try:
                    await signal_generator.main(realtime_data)
                    last_signal_generation_time = current_time
                    logger.info("Geração de sinais concluída com sucesso.")
                except Exception as e:
                    logger.error(f"Erro ao executar a geração de sinais: {e}")

            logger.info(f"Ciclo de coleta concluído. Próximo ciclo em {settings.REALTIME_COLLECTION_INTERVAL} segundos.")
            await asyncio.sleep(settings.REALTIME_COLLECTION_INTERVAL)
            
        except KeyboardInterrupt:
            logger.info("Coleta em tempo real interrompida pelo usuário")
            break
        except Exception as e:
            logger.error(f"Erro no loop principal do coletor: {e}")
            logger.error("Aguardando 60 segundos antes de tentar novamente...")
            await asyncio.sleep(60)


if __name__ == "__main__":
    # Configurar logging
    logger.remove()
    logger.add(sys.stderr, level=settings.LOG_LEVEL)
    logger.add(
        "logs/realtime_collector_{time}.log",
        rotation="100 MB",
        retention="10 days",
        level=settings.LOG_LEVEL
    )
    
    # Executar coletor
    try:
        asyncio.run(run_realtime_collector())
    except KeyboardInterrupt:
        print("Interrompido pelo usuário. Encerrando...")
    except Exception as e:
        logger.critical(f"Erro fatal: {e}")
        sys.exit(1)