import json
import asyncio
from typing import Dict, Optional, List, Any
from datetime import datetime, timezone
import logging
import os

from .websocket_collector import WebSocketCollector, WebSocketResult
from ..cache.intelligent_cache import IntelligentCache
from ..monitoring.metrics import MetricsCollector

logger = logging.getLogger(__name__)

class AlphaVantageWebSocketCollector(WebSocketCollector):
    """Coletor WebSocket para dados da Alpha Vantage."""
    
    def __init__(self, cache: IntelligentCache, metrics: MetricsCollector, api_key: str = None):
        super().__init__(cache, metrics)
        self.api_key = api_key or os.getenv('ALPHA_VANTAGE_API_KEY')
        self.session_id = None
        
        if not self.api_key:
            logger.warning("API key da Alpha Vantage não fornecida")
        
        logger.info("AlphaVantageWebSocketCollector inicializado")
    
    @property
    def websocket_url(self) -> str:
        """URL do WebSocket da Alpha Vantage."""
        return "wss://ws.twelvedata.com/v1/quotes/price"
    
    @property
    def source_name(self) -> str:
        """Nome da fonte de dados."""
        return "alpha_vantage"
    
    async def connect(self) -> bool:
        """Conecta ao WebSocket com autenticação."""
        if not self.api_key:
            logger.error("API key da Alpha Vantage é obrigatória")
            return False
        
        success = await super().connect()
        
        if success:
            # Enviar mensagem de autenticação
            auth_message = {
                "action": "auth",
                "params": {
                    "apikey": self.api_key
                }
            }
            
            auth_success = await self.send_message(auth_message)
            if not auth_success:
                logger.error("Falha na autenticação com Alpha Vantage")
                await self.disconnect()
                return False
        
        return success
    
    async def subscribe_symbol(self, symbol: str) -> bool:
        """Inscreve-se para receber dados de um símbolo."""
        if symbol in self.subscribed_symbols:
            return True
        
        if not self.api_key:
            logger.error("API key necessária para inscrição")
            return False
        
        try:
            # Converter símbolo para formato Alpha Vantage
            av_symbol = self._convert_to_alpha_vantage_symbol(symbol)
            
            # Mensagem de inscrição
            subscribe_message = {
                "action": "subscribe",
                "params": {
                    "symbols": av_symbol
                }
            }
            
            success = await self.send_message(subscribe_message)
            
            if success:
                self.subscribed_symbols.add(symbol)
                
                logger.info(f"Inscrito no símbolo {av_symbol} (original: {symbol}) na Alpha Vantage")
                
                await self.metrics.record_counter(
                    "websocket_alpha_vantage_subscriptions_total",
                    labels={"symbol": symbol, "status": "success"}
                )
                
                return True
            else:
                await self.metrics.record_counter(
                    "websocket_alpha_vantage_subscriptions_total",
                    labels={"symbol": symbol, "status": "error"}
                )
                return False
        
        except Exception as e:
            logger.error(f"Erro ao inscrever símbolo {symbol} na Alpha Vantage: {e}")
            await self.metrics.record_counter(
                "websocket_alpha_vantage_subscriptions_total",
                labels={"symbol": symbol, "status": "error", "error": type(e).__name__}
            )
            return False
    
    async def unsubscribe_symbol(self, symbol: str) -> bool:
        """Cancela inscrição de um símbolo."""
        if symbol not in self.subscribed_symbols:
            return True
        
        try:
            av_symbol = self._convert_to_alpha_vantage_symbol(symbol)
            
            # Mensagem de cancelamento
            unsubscribe_message = {
                "action": "unsubscribe",
                "params": {
                    "symbols": av_symbol
                }
            }
            
            success = await self.send_message(unsubscribe_message)
            
            if success:
                self.subscribed_symbols.discard(symbol)
                
                logger.info(f"Cancelada inscrição do símbolo {av_symbol} (original: {symbol}) na Alpha Vantage")
                
                await self.metrics.record_counter(
                    "websocket_alpha_vantage_unsubscriptions_total",
                    labels={"symbol": symbol, "status": "success"}
                )
                
                return True
            else:
                await self.metrics.record_counter(
                    "websocket_alpha_vantage_unsubscriptions_total",
                    labels={"symbol": symbol, "status": "error"}
                )
                return False
        
        except Exception as e:
            logger.error(f"Erro ao cancelar inscrição do símbolo {symbol} na Alpha Vantage: {e}")
            await self.metrics.record_counter(
                "websocket_alpha_vantage_unsubscriptions_total",
                labels={"symbol": symbol, "status": "error", "error": type(e).__name__}
            )
            return False
    
    async def parse_message(self, message: str) -> Optional[WebSocketResult]:
        """Faz parse de uma mensagem da Alpha Vantage."""
        try:
            data = json.loads(message)
            
            # Verificar se é uma mensagem de preço
            if 'event' in data and data['event'] == 'price':
                symbol_data = data.get('data', {})
                
                if symbol_data:
                    # Extrair símbolo
                    av_symbol = symbol_data.get('symbol', '')
                    symbol = self._convert_from_alpha_vantage_symbol(av_symbol)
                    
                    # Extrair dados relevantes
                    parsed_data = {
                        'symbol': symbol,
                        'current_price': float(symbol_data.get('price', 0)),
                        'timestamp_ms': int(symbol_data.get('timestamp', 0)),
                        'exchange': symbol_data.get('exchange', ''),
                        'mic_code': symbol_data.get('mic_code', ''),
                        'currency': symbol_data.get('currency', ''),
                        'datetime': symbol_data.get('datetime', ''),
                        'type': symbol_data.get('type', '')
                    }
                    
                    return WebSocketResult(
                        symbol=symbol,
                        data=parsed_data,
                        source='alpha_vantage_websocket',
                        timestamp=datetime.now(timezone.utc),
                        message_type='price',
                        raw_message=message
                    )
            
            # Verificar se é uma mensagem de status
            elif 'event' in data and data['event'] == 'status':
                status = data.get('status', '')
                
                if status == 'ok':
                    logger.info("Conexão Alpha Vantage estabelecida com sucesso")
                elif status == 'error':
                    error_msg = data.get('message', 'Erro desconhecido')
                    logger.error(f"Erro da Alpha Vantage: {error_msg}")
                
                return None
            
            # Verificar se é uma mensagem de heartbeat
            elif 'event' in data and data['event'] == 'heartbeat':
                logger.debug("Heartbeat recebido da Alpha Vantage")
                return None
            
            # Verificar se é uma resposta de inscrição
            elif 'event' in data and data['event'] == 'subscribe-status':
                status = data.get('status', '')
                symbols = data.get('symbols', [])
                
                if status == 'ok':
                    logger.info(f"Inscrição confirmada para símbolos: {symbols}")
                else:
                    logger.error(f"Erro na inscrição para símbolos {symbols}: {data.get('message', '')}")
                
                return None
            
            else:
                logger.debug(f"Mensagem Alpha Vantage não reconhecida: {message[:200]}...")
                return None
        
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao decodificar JSON da Alpha Vantage: {e}")
            return None
        
        except Exception as e:
            logger.error(f"Erro ao processar mensagem da Alpha Vantage: {e}")
            return None
    
    def _convert_to_alpha_vantage_symbol(self, symbol: str) -> str:
        """Converte símbolo para formato Alpha Vantage."""
        # Remover sufixos brasileiros
        if symbol.endswith('.SA'):
            return symbol  # Alpha Vantage suporta .SA para ações brasileiras
        
        # Mapeamentos específicos para ações americanas
        symbol_mapping = {
            'AAPL': 'AAPL',
            'GOOGL': 'GOOGL',
            'MSFT': 'MSFT',
            'AMZN': 'AMZN',
            'TSLA': 'TSLA',
            'META': 'META',
            'NVDA': 'NVDA',
            'NFLX': 'NFLX',
            'BTC': 'BTC-USD',
            'ETH': 'ETH-USD'
        }
        
        return symbol_mapping.get(symbol, symbol)
    
    def _convert_from_alpha_vantage_symbol(self, av_symbol: str) -> str:
        """Converte símbolo do formato Alpha Vantage para formato padrão."""
        # Mapeamentos reversos
        reverse_mapping = {
            'BTC-USD': 'BTC',
            'ETH-USD': 'ETH'
        }
        
        return reverse_mapping.get(av_symbol, av_symbol)
    
    async def subscribe_multiple_symbols(self, symbols: List[str]) -> Dict[str, bool]:
        """Inscreve-se em múltiplos símbolos de uma vez."""
        if not self.api_key:
            return {symbol: False for symbol in symbols}
        
        results = {}
        
        # Filtrar símbolos não inscritos
        new_symbols = [s for s in symbols if s not in self.subscribed_symbols]
        
        if not new_symbols:
            return {symbol: True for symbol in symbols}  # Já inscritos
        
        try:
            # Converter símbolos
            av_symbols = [self._convert_to_alpha_vantage_symbol(s) for s in new_symbols]
            
            # Mensagem de inscrição múltipla
            subscribe_message = {
                "action": "subscribe",
                "params": {
                    "symbols": ",".join(av_symbols)
                }
            }
            
            success = await self.send_message(subscribe_message)
            
            if success:
                for symbol in new_symbols:
                    self.subscribed_symbols.add(symbol)
                    results[symbol] = True
                    
                    await self.metrics.record_counter(
                        "websocket_alpha_vantage_subscriptions_total",
                        labels={"symbol": symbol, "status": "success"}
                    )
                
                logger.info(f"Inscrito em {len(new_symbols)} símbolos da Alpha Vantage")
            else:
                results = {symbol: False for symbol in new_symbols}
        
        except Exception as e:
            logger.error(f"Erro ao inscrever múltiplos símbolos na Alpha Vantage: {e}")
            results = {symbol: False for symbol in new_symbols}
        
        # Adicionar símbolos já inscritos
        for symbol in symbols:
            if symbol not in results:
                results[symbol] = True
        
        return results
    
    async def get_real_time_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Obtém cotação em tempo real para um símbolo específico."""
        latest_data = await self.get_latest_data(symbol)
        
        if latest_data and latest_data.message_type == 'price':
            return {
                'symbol': symbol,
                'price': latest_data.data.get('current_price'),
                'exchange': latest_data.data.get('exchange'),
                'currency': latest_data.data.get('currency'),
                'datetime': latest_data.data.get('datetime'),
                'timestamp_ms': latest_data.data.get('timestamp_ms'),
                'mic_code': latest_data.data.get('mic_code'),
                'type': latest_data.data.get('type'),
                'last_update': latest_data.timestamp
            }
        
        return None
    
    async def send_heartbeat(self) -> bool:
        """Envia heartbeat para manter a conexão ativa."""
        heartbeat_message = {
            "action": "heartbeat"
        }
        
        return await self.send_message(heartbeat_message)
    
    async def get_connection_status(self) -> Dict[str, Any]:
        """Obtém status detalhado da conexão."""
        base_status = await self.get_health_status()
        
        # Adicionar informações específicas da Alpha Vantage
        base_status.update({
            'api_key_configured': bool(self.api_key),
            'session_id': self.session_id,
            'supported_markets': ['US', 'BR', 'Crypto'],
            'rate_limits': {
                'requests_per_minute': 5,  # Limite típico da Alpha Vantage
                'symbols_per_request': 100
            }
        })
        
        return base_status
    
    def set_api_key(self, api_key: str):
        """Define a API key."""
        self.api_key = api_key
        logger.info("API key da Alpha Vantage atualizada")
    
    async def test_connection(self) -> bool:
        """Testa a conexão e autenticação."""
        if not self.api_key:
            logger.error("API key necessária para teste de conexão")
            return False
        
        try:
            # Tentar conectar
            if await self.connect():
                # Tentar inscrever em um símbolo de teste
                test_result = await self.subscribe_symbol('AAPL')
                
                if test_result:
                    await self.unsubscribe_symbol('AAPL')
                    logger.info("Teste de conexão Alpha Vantage bem-sucedido")
                    return True
                else:
                    logger.error("Falha no teste de inscrição Alpha Vantage")
                    return False
            else:
                logger.error("Falha na conexão Alpha Vantage")
                return False
        
        except Exception as e:
            logger.error(f"Erro no teste de conexão Alpha Vantage: {e}")
            return False
        
        finally:
            await self.disconnect()