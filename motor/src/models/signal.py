"""
Modelo para representar sinais de trading.
"""
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field, validator


class SignalDirection(str, Enum):
    """Direções de sinal de trading."""
    CALL = "CALL"
    PUT = "PUT"
    NEUTRAL = "NEUTRAL"


class SignalStatus(str, Enum):
    """Status de um sinal de trading."""
    ACTIVE = "active"
    EXPIRED = "expired"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class SignalTimeframe(str, Enum):
    """Timeframes suportados para sinais."""
    MINUTE_1 = "1m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    MINUTE_30 = "30m"
    HOUR_1 = "1h"
    HOUR_4 = "4h"
    DAY_1 = "1d"
    WEEK_1 = "1w"
    MONTH_1 = "1M"


class SignalSource(str, Enum):
    """Fontes de geração de sinais."""
    TECHNICAL = "technical"
    ML_BASIC = "ml_basic"
    ML_ADVANCED = "ml_advanced"
    FUNDAMENTAL = "fundamental"
    SENTIMENT = "sentiment"
    ENSEMBLE = "ensemble"
    MANUAL = "manual"


class IndicatorValues(BaseModel):
    """Valores de indicadores técnicos usados para gerar o sinal."""
    rsi: Optional[float] = None
    macd: Optional[Dict[str, Union[float, str]]] = None
    sma: Optional[Dict[str, Union[float, str]]] = None
    ema: Optional[Dict[str, Union[float, str]]] = None
    bollinger: Optional[Dict[str, Union[float, str]]] = None
    stochastic: Optional[Dict[str, Union[float, str]]] = None
    adx: Optional[float] = None
    ichimoku: Optional[Dict[str, Union[float, str]]] = None
    volume: Optional[Dict[str, Union[float, str]]] = None
    patterns: Optional[List[str]] = None
    additional: Optional[Dict[str, Union[float, str, List, Dict]]] = None


class ModelPerformance(BaseModel):
    """Performance do modelo para este sinal específico."""
    model_id: str
    accuracy: float
    precision: float
    recall: float
    f1_score: float
    confidence: float
    training_date: datetime


class Signal(BaseModel):
    """Modelo para representar um sinal de trading."""
    id: Optional[str] = None
    asset_id: str
    asset_symbol: str
    direction: SignalDirection
    confidence: float = Field(..., ge=0.0, le=1.0)
    price_target: Optional[float] = None
    stop_loss: Optional[float] = None
    generated_at: datetime = Field(default_factory=datetime.now)
    valid_until: datetime = None
    status: SignalStatus = SignalStatus.ACTIVE
    timeframe: SignalTimeframe
    source: SignalSource
    indicators: Optional[IndicatorValues] = None
    model_performance: Optional[ModelPerformance] = None
    notes: Optional[str] = None
    created_by: Optional[str] = None  # user_id ou "system"
    
    @validator('valid_until', pre=True, always=True)
    def set_valid_until(cls, v, values):
        """Define valid_until baseado no timeframe se não for fornecido."""
        if v is None and 'generated_at' in values and 'timeframe' in values:
            timeframe = values['timeframe']
            generated_at = values['generated_at']
            
            # Mapeamento de timeframes para durações
            timeframe_durations = {
                SignalTimeframe.MINUTE_1: timedelta(minutes=5),
                SignalTimeframe.MINUTE_5: timedelta(minutes=20),
                SignalTimeframe.MINUTE_15: timedelta(hours=1),
                SignalTimeframe.MINUTE_30: timedelta(hours=2),
                SignalTimeframe.HOUR_1: timedelta(hours=4),
                SignalTimeframe.HOUR_4: timedelta(hours=12),
                SignalTimeframe.DAY_1: timedelta(days=3),
                SignalTimeframe.WEEK_1: timedelta(weeks=2),
                SignalTimeframe.MONTH_1: timedelta(days=45),
            }
            
            duration = timeframe_durations.get(timeframe, timedelta(days=1))
            return generated_at + duration
        return v

    class Config:
        """Configuração do modelo Pydantic."""
        orm_mode = True
        schema_extra = {
            "example": {
                "id": "1",
                "asset_id": "1",
                "asset_symbol": "AAPL",
                "direction": "CALL",
                "confidence": 0.85,
                "price_target": 155.50,
                "stop_loss": 145.75,
                "generated_at": "2023-09-01T14:30:00",
                "valid_until": "2023-09-04T14:30:00",
                "status": "active",
                "timeframe": "1d",
                "source": "ensemble",
                "indicators": {
                    "rsi": 32.5,
                    "macd": {
                        "value": 0.15,
                        "signal": 0.10,
                        "histogram": 0.05,
                        "interpretation": "bullish"
                    },
                    "sma": {
                        "sma_50": 158.75,
                        "sma_200": 152.30,
                        "interpretation": "bullish"
                    },
                    "patterns": ["doji", "hammer"]
                },
                "notes": "Forte tendência de alta após consolidação."
            }
        }


class SignalCreate(BaseModel):
    """Modelo para criação de um novo sinal."""
    asset_id: str
    asset_symbol: str
    direction: SignalDirection
    confidence: float = Field(..., ge=0.0, le=1.0)
    price_target: Optional[float] = None
    stop_loss: Optional[float] = None
    timeframe: SignalTimeframe
    source: SignalSource
    indicators: Optional[IndicatorValues] = None
    model_performance: Optional[ModelPerformance] = None
    notes: Optional[str] = None
    created_by: Optional[str] = None
    # valid_until será calculado automaticamente


class SignalUpdate(BaseModel):
    """Modelo para atualização de um sinal existente."""
    direction: Optional[SignalDirection] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    price_target: Optional[float] = None
    stop_loss: Optional[float] = None
    valid_until: Optional[datetime] = None
    status: Optional[SignalStatus] = None
    indicators: Optional[IndicatorValues] = None
    model_performance: Optional[ModelPerformance] = None
    notes: Optional[str] = None


class SignalPerformance(BaseModel):
    """Modelo para registrar a performance de um sinal após sua expiração."""
    signal_id: str
    successful: bool
    actual_price: float
    target_reached: bool
    stop_triggered: bool
    max_price: float
    min_price: float
    recorded_at: datetime = Field(default_factory=datetime.now)
    notes: Optional[str] = None


class SignalInDB(Signal):
    """Modelo para representar um sinal conforme armazenado no banco de dados."""
    id: str 