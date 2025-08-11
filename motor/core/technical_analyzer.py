import pandas as pd
import pandas_ta as ta

class TechnicalAnalyzer:
    """Classe para realizar análise técnica em dados de mercado."""

    def calculate_rsi(self, data: pd.DataFrame, length: int = 14) -> pd.Series:
        """Calcula o Índice de Força Relativa (RSI)."""
        return ta.rsi(data['Close'], length=length)

    def analyze(self, data: pd.DataFrame) -> dict:
        """
        Executa uma análise técnica completa nos dados.
        """
        if 'Close' not in data.columns:
            raise ValueError("O DataFrame deve conter a coluna 'Close'.")

        rsi = self.calculate_rsi(data)

        # Retorna os últimos valores dos indicadores calculados
        return {
            'rsi': rsi.iloc[-1] if not rsi.empty else None
            # Outros indicadores podem ser adicionados aqui
        }