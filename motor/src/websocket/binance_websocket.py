import json
import asyncio
from typing import Dict, Optional, List, Any
from datetime import datetime, timezone
import logging

from .websocket_collector import WebSocketCollector, WebSocketResult
from ..cache.intelligent_cache import IntelligentCache
from ..monitoring.metrics import MetricsCollector

logger = logging.getLogger(__name__)

class BinanceWebSocketCollector(WebSocketCollector):
    """Coletor WebSocket para dados da Binance."""
    
    def __init__(self, cache: IntelligentCache, metrics: MetricsCollector, testnet: bool = False):
        super().__init__(cache, metrics)
        self.testnet = testnet
        self.stream_names: Dict[str, str] = {}  # symbol -> stream_name
        
        logger.info(f"BinanceWebSocketCollector inicializado (testnet={testnet})")
    
    @property
    def websocket_url(self) -> str:
        """URL do WebSocket da Binance."""
        if self.testnet:
            return "wss://testnet.binance.vision/ws"
        return "wss://stream.binance.com:9443/ws"
    
    @property
    def source_name(self) -> str:
        """Nome da fonte de dados."""
        return "binance"
    
    async def subscribe_symbol(self, symbol: str) -> bool:
        """Inscreve-se para receber dados de um símbolo."""
        if symbol in self.subscribed_symbols:
            return True
        
        try:
            # Converter símbolo para formato Binance (ex: BTCUSDT)
            binance_symbol = self._convert_to_binance_symbol(symbol)
            stream_name = f"{binance_symbol.lower()}@ticker"
            
            # Mensagem de inscrição
            subscribe_message = {
                "method": "SUBSCRIBE",
                "params": [stream_name],
                "id": int(datetime.now().timestamp() * 1000)
            }
            
            success = await self.send_message(subscribe_message)
            
            if success:
                self.subscribed_symbols.add(symbol)
                self.stream_names[symbol] = stream_name
                
                logger.info(f"Inscrito no stream {stream_name} para símbolo {symbol}")
                
                await self.metrics.record_counter(
                    "websocket_binance_subscriptions_total",
                    labels={"symbol": symbol, "status": "success"}
                )
                
                return True
            else:
                await self.metrics.record_counter(
                    "websocket_binance_subscriptions_total",
                    labels={"symbol": symbol, "status": "error"}
                )
                return False
        
        except Exception as e:
            logger.error(f"Erro ao inscrever símbolo {symbol} na Binance: {e}")
            await self.metrics.record_counter(
                "websocket_binance_subscriptions_total",
                labels={"symbol": symbol, "status": "error", "error": type(e).__name__}
            )
            return False
    
    async def unsubscribe_symbol(self, symbol: str) -> bool:
        """Cancela inscrição de um símbolo."""
        if symbol not in self.subscribed_symbols:
            return True
        
        try:
            stream_name = self.stream_names.get(symbol)
            if not stream_name:
                return False
            
            # Mensagem de cancelamento
            unsubscribe_message = {
                "method": "UNSUBSCRIBE",
                "params": [stream_name],
                "id": int(datetime.now().timestamp() * 1000)
            }
            
            success = await self.send_message(unsubscribe_message)
            
            if success:
                self.subscribed_symbols.discard(symbol)
                self.stream_names.pop(symbol, None)
                
                logger.info(f"Cancelada inscrição do stream {stream_name} para símbolo {symbol}")
                
                await self.metrics.record_counter(
                    "websocket_binance_unsubscriptions_total",
                    labels={"symbol": symbol, "status": "success"}
                )
                
                return True
            else:
                await self.metrics.record_counter(
                    "websocket_binance_unsubscriptions_total",
                    labels={"symbol": symbol, "status": "error"}
                )
                return False
        
        except Exception as e:
            logger.error(f"Erro ao cancelar inscrição do símbolo {symbol} na Binance: {e}")
            await self.metrics.record_counter(
                "websocket_binance_unsubscriptions_total",
                labels={"symbol": symbol, "status": "error", "error": type(e).__name__}
            )
            return False
    
    async def parse_message(self, message: str) -> Optional[WebSocketResult]:
        """Faz parse de uma mensagem da Binance."""
        try:
            data = json.loads(message)
            
            # Verificar se é uma mensagem de ticker
            if 'stream' in data and 'data' in data:
                stream = data['stream']
                ticker_data = data['data']
                
                # Extrair símbolo do stream
                if '@ticker' in stream:
                    binance_symbol = stream.split('@')[0].upper()
                    symbol = self._convert_from_binance_symbol(binance_symbol)
                    
                    # Extrair dados relevantes
                    parsed_data = {
                        'symbol': symbol,
                        'current_price': float(ticker_data.get('c', 0)),  # Close price
                        'open_price': float(ticker_data.get('o', 0)),     # Open price
                        'high_price': float(ticker_data.get('h', 0)),     # High price
                        'low_price': float(ticker_data.get('l', 0)),      # Low price
                        'volume': float(ticker_data.get('v', 0)),         # Volume
                        'quote_volume': float(ticker_data.get('q', 0)),   # Quote volume
                        'price_change': float(ticker_data.get('p', 0)),   # Price change
                        'price_change_percent': float(ticker_data.get('P', 0)),  # Price change percent
                        'weighted_avg_price': float(ticker_data.get('w', 0)),    # Weighted average price
                        'prev_close_price': float(ticker_data.get('x', 0)),      # Previous close
                        'last_qty': float(ticker_data.get('Q', 0)),              # Last quantity
                        'bid_price': float(ticker_data.get('b', 0)),             # Best bid price
                        'bid_qty': float(ticker_data.get('B', 0)),               # Best bid quantity
                        'ask_price': float(ticker_data.get('a', 0)),             # Best ask price
                        'ask_qty': float(ticker_data.get('A', 0)),               # Best ask quantity
                        'count': int(ticker_data.get('n', 0)),                   # Total number of trades
                        'event_time': int(ticker_data.get('E', 0)),              # Event time
                        'symbol_time': int(ticker_data.get('C', 0))              # Close time
                    }
                    
                    return WebSocketResult(
                        symbol=symbol,
                        data=parsed_data,
                        source='binance_websocket',
                        timestamp=datetime.now(timezone.utc),
                        message_type='ticker',
                        raw_message=message
                    )
            
            # Verificar se é uma resposta de inscrição/cancelamento
            elif 'result' in data and 'id' in data:
                logger.debug(f"Resposta de comando Binance: {data}")
                return None
            
            # Verificar se é uma mensagem de erro
            elif 'error' in data:
                logger.error(f"Erro da Binance WebSocket: {data['error']}")
                return None
            
            else:
                logger.debug(f"Mensagem Binance não reconhecida: {message[:200]}...")
                return None
        
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao decodificar JSON da Binance: {e}")
            return None
        
        except Exception as e:
            logger.error(f"Erro ao processar mensagem da Binance: {e}")
            return None
    
    def _convert_to_binance_symbol(self, symbol: str) -> str:
        """Converte símbolo para formato Binance."""
        # Remover sufixos comuns
        symbol = symbol.replace('.SA', '').replace('-USD', 'USDT')
        
        # Mapeamentos específicos
        symbol_mapping = {
            'BTC': 'BTCUSDT',
            'ETH': 'ETHUSDT',
            'BNB': 'BNBUSDT',
            'ADA': 'ADAUSDT',
            'DOT': 'DOTUSDT',
            'LINK': 'LINKUSDT',
            'LTC': 'LTCUSDT',
            'BCH': 'BCHUSDT',
            'XRP': 'XRPUSDT',
            'DOGE': 'DOGEUSDT'
        }
        
        if symbol in symbol_mapping:
            return symbol_mapping[symbol]
        
        # Se não tem USDT no final, adicionar
        if not symbol.endswith('USDT') and not symbol.endswith('BTC') and not symbol.endswith('ETH'):
            return f"{symbol}USDT"
        
        return symbol
    
    def _convert_from_binance_symbol(self, binance_symbol: str) -> str:
        """Converte símbolo do formato Binance para formato padrão."""
        # Mapeamentos reversos
        reverse_mapping = {
            'BTCUSDT': 'BTC',
            'ETHUSDT': 'ETH',
            'BNBUSDT': 'BNB',
            'ADAUSDT': 'ADA',
            'DOTUSDT': 'DOT',
            'LINKUSDT': 'LINK',
            'LTCUSDT': 'LTC',
            'BCHUSDT': 'BCH',
            'XRPUSDT': 'XRP',
            'DOGEUSDT': 'DOGE'
        }
        
        if binance_symbol in reverse_mapping:
            return reverse_mapping[binance_symbol]
        
        # Remover sufixos comuns
        if binance_symbol.endswith('USDT'):
            return binance_symbol[:-4]
        elif binance_symbol.endswith('BTC'):
            return binance_symbol[:-3] + '-BTC'
        elif binance_symbol.endswith('ETH'):
            return binance_symbol[:-3] + '-ETH'
        
        return binance_symbol
    
    async def subscribe_multiple_symbols(self, symbols: List[str]) -> Dict[str, bool]:
        """Inscreve-se em múltiplos símbolos de uma vez."""
        results = {}
        
        # Preparar streams
        streams = []
        symbol_to_stream = {}
        
        for symbol in symbols:
            if symbol not in self.subscribed_symbols:
                binance_symbol = self._convert_to_binance_symbol(symbol)
                stream_name = f"{binance_symbol.lower()}@ticker"
                streams.append(stream_name)
                symbol_to_stream[symbol] = stream_name
        
        if not streams:
            return {symbol: True for symbol in symbols}  # Já inscritos
        
        try:
            # Mensagem de inscrição múltipla
            subscribe_message = {
                "method": "SUBSCRIBE",
                "params": streams,
                "id": int(datetime.now().timestamp() * 1000)
            }
            
            success = await self.send_message(subscribe_message)
            
            if success:
                for symbol, stream_name in symbol_to_stream.items():
                    self.subscribed_symbols.add(symbol)
                    self.stream_names[symbol] = stream_name
                    results[symbol] = True
                    
                    await self.metrics.record_counter(
                        "websocket_binance_subscriptions_total",
                        labels={"symbol": symbol, "status": "success"}
                    )
                
                logger.info(f"Inscrito em {len(streams)} streams da Binance")
            else:
                results = {symbol: False for symbol in symbol_to_stream.keys()}
        
        except Exception as e:
            logger.error(f"Erro ao inscrever múltiplos símbolos na Binance: {e}")
            results = {symbol: False for symbol in symbol_to_stream.keys()}
        
        # Adicionar símbolos já inscritos
        for symbol in symbols:
            if symbol not in results:
                results[symbol] = True
        
        return results
    
    async def get_24h_ticker_stats(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Obtém estatísticas de 24h para um símbolo específico."""
        latest_data = await self.get_latest_data(symbol)
        
        if latest_data and latest_data.message_type == 'ticker':
            return {
                'symbol': symbol,
                'price_change_24h': latest_data.data.get('price_change'),
                'price_change_percent_24h': latest_data.data.get('price_change_percent'),
                'weighted_avg_price_24h': latest_data.data.get('weighted_avg_price'),
                'high_24h': latest_data.data.get('high_price'),
                'low_24h': latest_data.data.get('low_price'),
                'volume_24h': latest_data.data.get('volume'),
                'quote_volume_24h': latest_data.data.get('quote_volume'),
                'trade_count_24h': latest_data.data.get('count'),
                'timestamp': latest_data.timestamp
            }
        
        return None
    
    async def get_orderbook_snapshot(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Obtém snapshot do livro de ofertas."""
        latest_data = await self.get_latest_data(symbol)
        
        if latest_data and latest_data.message_type == 'ticker':
            return {
                'symbol': symbol,
                'best_bid': {
                    'price': latest_data.data.get('bid_price'),
                    'quantity': latest_data.data.get('bid_qty')
                },
                'best_ask': {
                    'price': latest_data.data.get('ask_price'),
                    'quantity': latest_data.data.get('ask_qty')
                },
                'spread': latest_data.data.get('ask_price', 0) - latest_data.data.get('bid_price', 0),
                'timestamp': latest_data.timestamp
            }
        
        return None