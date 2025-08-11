import asyncio
import websockets
import json
import time
from typing import Dict, List, Optional, Any, Callable, Set
from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from abc import ABC, abstractmethod
from enum import Enum

from ..resilience.circuit_breaker import AdvancedCircuitBreaker
from ..cache.intelligent_cache import IntelligentCache
from ..monitoring.metrics import MetricsCollector

logger = logging.getLogger(__name__)

class ConnectionState(Enum):
    """Estados da conexão WebSocket."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"

@dataclass
class WebSocketResult:
    """Resultado de dados recebidos via WebSocket."""
    symbol: str
    data: Dict[str, Any]
    source: str
    timestamp: datetime
    message_type: str
    raw_message: Optional[str] = None

class WebSocketException(Exception):
    """Exceção específica para erros de WebSocket."""
    pass

class WebSocketCollector(ABC):
    """Classe base para coletores WebSocket."""
    
    def __init__(self, cache: IntelligentCache, metrics: MetricsCollector):
        self.cache = cache
        self.metrics = metrics
        self.websocket = None
        self.connection_state = ConnectionState.DISCONNECTED
        self.subscribed_symbols: Set[str] = set()
        self.message_handlers: Dict[str, Callable] = {}
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        self.reconnect_delay = 1.0
        self.max_reconnect_delay = 60.0
        self.ping_interval = 30
        self.ping_timeout = 10
        self.last_ping_time = 0
        self.last_pong_time = 0
        
        # Circuit breaker para conexões
        from src.resilience.circuit_breaker import CircuitBreakerConfig
        
        cb_config = CircuitBreakerConfig(
            failure_threshold=5,
            open_timeout=300
        )
        self.circuit_breaker = AdvancedCircuitBreaker(f'{self.source_name}_websocket', cb_config)
        
        # Task de conexão
        self.connection_task: Optional[asyncio.Task] = None
        self.ping_task: Optional[asyncio.Task] = None
        
        logger.info(f"{self.__class__.__name__} inicializado")
    
    @property
    @abstractmethod
    def websocket_url(self) -> str:
        """URL do WebSocket."""
        pass
    
    @property
    @abstractmethod
    def source_name(self) -> str:
        """Nome da fonte de dados."""
        pass
    
    @abstractmethod
    async def subscribe_symbol(self, symbol: str) -> bool:
        """Inscreve-se para receber dados de um símbolo."""
        pass
    
    @abstractmethod
    async def unsubscribe_symbol(self, symbol: str) -> bool:
        """Cancela inscrição de um símbolo."""
        pass
    
    @abstractmethod
    async def parse_message(self, message: str) -> Optional[WebSocketResult]:
        """Faz parse de uma mensagem recebida."""
        pass
    
    async def connect(self) -> bool:
        """Conecta ao WebSocket."""
        if self.connection_state in [ConnectionState.CONNECTED, ConnectionState.CONNECTING]:
            return True
        
        try:
            async with self.circuit_breaker:
                self.connection_state = ConnectionState.CONNECTING
                
                logger.info(f"Conectando ao WebSocket: {self.websocket_url}")
                
                self.websocket = await websockets.connect(
                    self.websocket_url,
                    ping_interval=self.ping_interval,
                    ping_timeout=self.ping_timeout,
                    close_timeout=10
                )
                
                self.connection_state = ConnectionState.CONNECTED
                self.reconnect_attempts = 0
                
                # Iniciar tasks de monitoramento
                self.connection_task = asyncio.create_task(self._connection_handler())
                self.ping_task = asyncio.create_task(self._ping_handler())
                
                # Registrar métricas
                await self.metrics.record_counter(
                    f"websocket_{self.source_name}_connections_total",
                    labels={"status": "success"}
                )
                
                logger.info(f"Conectado ao WebSocket {self.source_name}")
                return True
        
        except Exception as e:
            self.connection_state = ConnectionState.ERROR
            
            await self.metrics.record_counter(
                f"websocket_{self.source_name}_connections_total",
                labels={"status": "error", "error": type(e).__name__}
            )
            
            logger.error(f"Erro ao conectar WebSocket {self.source_name}: {e}")
            return False
    
    async def disconnect(self):
        """Desconecta do WebSocket."""
        self.connection_state = ConnectionState.DISCONNECTED
        
        # Cancelar tasks
        if self.connection_task:
            self.connection_task.cancel()
            try:
                await self.connection_task
            except asyncio.CancelledError:
                pass
        
        if self.ping_task:
            self.ping_task.cancel()
            try:
                await self.ping_task
            except asyncio.CancelledError:
                pass
        
        # Fechar WebSocket
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        
        self.subscribed_symbols.clear()
        
        logger.info(f"Desconectado do WebSocket {self.source_name}")
    
    async def _connection_handler(self):
        """Handler principal da conexão WebSocket."""
        try:
            while self.connection_state == ConnectionState.CONNECTED:
                if not self.websocket:
                    break
                
                try:
                    # Aguardar mensagem com timeout
                    message = await asyncio.wait_for(
                        self.websocket.recv(), 
                        timeout=60.0
                    )
                    
                    # Processar mensagem
                    await self._handle_message(message)
                    
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout na recepção de mensagem {self.source_name}")
                    continue
                
                except websockets.exceptions.ConnectionClosed:
                    logger.warning(f"Conexão WebSocket {self.source_name} fechada")
                    break
                
                except Exception as e:
                    logger.error(f"Erro no handler de conexão {self.source_name}: {e}")
                    await asyncio.sleep(1)
        
        except Exception as e:
            logger.error(f"Erro crítico no handler de conexão {self.source_name}: {e}")
        
        finally:
            # Tentar reconectar se necessário
            if self.connection_state == ConnectionState.CONNECTED:
                await self._schedule_reconnect()
    
    async def _handle_message(self, message: str):
        """Processa uma mensagem recebida."""
        try:
            start_time = time.time()
            
            # Parse da mensagem
            result = await self.parse_message(message)
            
            if result:
                # Cache dos dados
                cache_key = f"websocket:{self.source_name}:{result.symbol}:latest"
                await self.cache.set(cache_key, result, ttl=60)  # 1 minuto
                
                # Registrar métricas
                processing_time = time.time() - start_time
                await self.metrics.record_counter(
                    f"websocket_{self.source_name}_messages_total",
                    labels={"symbol": result.symbol, "type": result.message_type}
                )
                await self.metrics.record_histogram(
                    f"websocket_{self.source_name}_message_processing_seconds",
                    processing_time,
                    labels={"symbol": result.symbol}
                )
                
                # Chamar handlers registrados
                for handler in self.message_handlers.values():
                    try:
                        await handler(result)
                    except Exception as e:
                        logger.error(f"Erro no handler de mensagem: {e}")
        
        except Exception as e:
            logger.error(f"Erro ao processar mensagem {self.source_name}: {e}")
            await self.metrics.record_counter(
                f"websocket_{self.source_name}_message_errors_total",
                labels={"error": type(e).__name__}
            )
    
    async def _ping_handler(self):
        """Handler para ping/pong do WebSocket."""
        while self.connection_state == ConnectionState.CONNECTED:
            try:
                if self.websocket:
                    self.last_ping_time = time.time()
                    pong_waiter = await self.websocket.ping()
                    await pong_waiter
                    self.last_pong_time = time.time()
                    
                    # Registrar latência
                    latency = self.last_pong_time - self.last_ping_time
                    await self.metrics.record_histogram(
                        f"websocket_{self.source_name}_ping_latency_seconds",
                        latency
                    )
                
                await asyncio.sleep(self.ping_interval)
            
            except Exception as e:
                logger.error(f"Erro no ping {self.source_name}: {e}")
                break
    
    async def _schedule_reconnect(self):
        """Agenda uma tentativa de reconexão."""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error(f"Máximo de tentativas de reconexão atingido para {self.source_name}")
            self.connection_state = ConnectionState.ERROR
            return
        
        self.connection_state = ConnectionState.RECONNECTING
        self.reconnect_attempts += 1
        
        # Backoff exponencial
        delay = min(
            self.reconnect_delay * (2 ** (self.reconnect_attempts - 1)),
            self.max_reconnect_delay
        )
        
        logger.info(
            f"Reagendando reconexão {self.source_name} em {delay:.1f}s "
            f"(tentativa {self.reconnect_attempts}/{self.max_reconnect_attempts})"
        )
        
        await asyncio.sleep(delay)
        
        # Tentar reconectar
        if await self.connect():
            # Re-inscrever símbolos
            symbols_to_resubscribe = self.subscribed_symbols.copy()
            self.subscribed_symbols.clear()
            
            for symbol in symbols_to_resubscribe:
                await self.subscribe_symbol(symbol)
    
    async def send_message(self, message: Dict[str, Any]) -> bool:
        """Envia uma mensagem via WebSocket."""
        if not self.websocket or self.connection_state != ConnectionState.CONNECTED:
            return False
        
        try:
            message_str = json.dumps(message)
            await self.websocket.send(message_str)
            
            await self.metrics.record_counter(
                f"websocket_{self.source_name}_sent_messages_total"
            )
            
            return True
        
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem {self.source_name}: {e}")
            await self.metrics.record_counter(
                f"websocket_{self.source_name}_send_errors_total",
                labels={"error": type(e).__name__}
            )
            return False
    
    def register_message_handler(self, name: str, handler: Callable[[WebSocketResult], None]):
        """Registra um handler para mensagens recebidas."""
        self.message_handlers[name] = handler
    
    def unregister_message_handler(self, name: str):
        """Remove um handler de mensagens."""
        self.message_handlers.pop(name, None)
    
    async def get_latest_data(self, symbol: str) -> Optional[WebSocketResult]:
        """Obtém os dados mais recentes de um símbolo do cache."""
        cache_key = f"websocket:{self.source_name}:{symbol}:latest"
        return await self.cache.get(cache_key)
    
    def get_connection_info(self) -> Dict[str, Any]:
        """Retorna informações sobre a conexão."""
        return {
            'state': self.connection_state.value,
            'subscribed_symbols': list(self.subscribed_symbols),
            'reconnect_attempts': self.reconnect_attempts,
            'last_ping_time': self.last_ping_time,
            'last_pong_time': self.last_pong_time,
            'ping_latency': self.last_pong_time - self.last_ping_time if self.last_pong_time > self.last_ping_time else None
        }
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Retorna status de saúde do coletor."""
        connection_info = self.get_connection_info()
        
        # Determinar saúde baseada no estado da conexão
        is_healthy = (
            self.connection_state == ConnectionState.CONNECTED and
            self.reconnect_attempts < self.max_reconnect_attempts // 2
        )
        
        return {
            'healthy': is_healthy,
            'connection': connection_info,
            'circuit_breaker': self.circuit_breaker.get_stats(),
            'source': self.source_name
        }