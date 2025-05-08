"""
Modelo para representar ativos financeiros no sistema.
"""
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class AssetType(str, Enum):
    """Tipos de ativos suportados no sistema."""
    STOCK = "stock"
    FOREX = "forex"
    CRYPTO = "crypto"
    ETF = "etf"
    INDEX = "index"
    FUTURES = "futures"
    OPTION = "option"
    BOND = "bond"
    COMMODITY = "commodity"


class AssetSource(str, Enum):
    """Fontes de dados para ativos."""
    FINNHUB = "finnhub"
    YAHOO = "yahoo"
    ALPHA_VANTAGE = "alpha_vantage"
    COINGECKO = "coingecko"
    BINANCE = "binance"
    TWELVEDATA = "twelvedata"
    MANUAL = "manual"


class AssetMeta(BaseModel):
    """Metadados adicionais para ativos."""
    sector: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None
    exchange: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    market_cap: Optional[float] = None
    volume: Optional[float] = None
    additional_data: Optional[Dict] = None


class Asset(BaseModel):
    """Modelo principal para representar um ativo financeiro."""
    id: Optional[str] = None
    symbol: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=255)
    type: AssetType
    source: AssetSource
    active: bool = True
    tradable: bool = True
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    last_price: Optional[float] = None
    currency: Optional[str] = None
    meta: Optional[AssetMeta] = None

    class Config:
        """Configuração do modelo Pydantic."""
        orm_mode = True
        schema_extra = {
            "example": {
                "id": "1",
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "type": "stock",
                "source": "finnhub",
                "active": True,
                "tradable": True,
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:00:00",
                "last_price": 150.25,
                "currency": "USD",
                "meta": {
                    "sector": "Technology",
                    "industry": "Consumer Electronics",
                    "country": "US",
                    "exchange": "NASDAQ",
                    "description": "Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories worldwide.",
                    "website": "https://www.apple.com",
                    "logo_url": "https://logo.clearbit.com/apple.com",
                    "market_cap": 2500000000000,
                    "volume": 80000000,
                },
            }
        }


class AssetCreate(BaseModel):
    """Modelo para criação de um novo ativo."""
    symbol: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=255)
    type: AssetType
    source: AssetSource
    active: bool = True
    tradable: bool = True
    last_price: Optional[float] = None
    currency: Optional[str] = None
    meta: Optional[AssetMeta] = None


class AssetUpdate(BaseModel):
    """Modelo para atualização de um ativo existente."""
    symbol: Optional[str] = Field(None, min_length=1, max_length=20)
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    type: Optional[AssetType] = None
    source: Optional[AssetSource] = None
    active: Optional[bool] = None
    tradable: Optional[bool] = None
    last_price: Optional[float] = None
    currency: Optional[str] = None
    meta: Optional[AssetMeta] = None
    updated_at: datetime = Field(default_factory=datetime.now)


class AssetInDB(Asset):
    """Modelo para representar um ativo conforme armazenado no banco de dados."""
    id: str 