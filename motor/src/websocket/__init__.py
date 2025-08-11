"""Módulo de coletores WebSocket para dados em tempo real."""

from .websocket_collector import WebSocketCollector, WebSocketResult
from .binance_websocket import BinanceWebSocketCollector
from .alpha_vantage_websocket import AlphaVantageWebSocketCollector

__all__ = [
    'WebSocketCollector',
    'WebSocketResult',
    'BinanceWebSocketCollector',
    'AlphaVantageWebSocketCollector'
]