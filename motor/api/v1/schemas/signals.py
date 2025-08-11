from pydantic import BaseModel
from typing import Dict, Any

class SignalRequest(BaseModel):
    asset: str
    timeframe: str

class SignalResponse(BaseModel):
    asset: str
    timeframe: str
    signal: str
    details: Dict[str, Any]