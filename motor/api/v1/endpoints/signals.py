from fastapi import APIRouter, HTTPException
from motor.api.v1.schemas.signals import SignalRequest, SignalResponse
from motor.core.signals_generator import SignalGenerator

router = APIRouter()
generator = SignalGenerator()

@router.post("/signals", response_model=SignalResponse)
def get_trading_signal(request: SignalRequest):
    """
    Endpoint para receber uma solicitação de sinal de trading, processá-la
    e retornar uma recomendação de Compra/Venda/Neutro.
    """
    try:
        signal = generator.generate(request.asset, request.timeframe)
        return SignalResponse(
            asset=request.asset,
            timeframe=request.timeframe,
            signal=signal['recommendation'],
            details=signal
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))