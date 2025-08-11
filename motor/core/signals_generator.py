from motor.core.data_collector import DataCollector
from motor.core.sentiment_analyzer import SentimentAnalyzer
from motor.core.technical_analyzer import TechnicalAnalyzer

class SignalGenerator:
    def __init__(self):
        self.data_collector = DataCollector()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.technical_analyzer = TechnicalAnalyzer()

    def generate(self, asset: str, timeframe: str):
        """
        Orquestra a coleta de dados, análise e geração de sinais.
        """
        print(f"Gerando sinal para {asset} no timeframe {timeframe}...")
        
        # 1. Coleta de dados
        # Ajusta o período com base no timeframe para atender às limitações da API do yfinance.
        # Intervalos curtos (ex: '15m') exigem um período mais curto (máximo de 60 dias).
        period = "60d" if timeframe == "15m" else "1y"
        historical_data = self.data_collector.fetch_historical_data(asset, period=period, interval=timeframe)

        print(f"[SignalGenerator] DataFrame recebido do DataCollector. Vazio: {historical_data.empty}")
        if not historical_data.empty:
            print(f"[SignalGenerator] Head do DataFrame:\n{historical_data.head()}")

        if historical_data.empty:
            return {
                "recommendation": "ERRO",
                "details": "Não foi possível obter dados para o ativo."
            }

        # 2. Análise (placeholders por enquanto)
        # 2. Análise de Sentimento (com texto de exemplo)
        # No futuro, buscaremos notícias reais sobre o ativo.
        example_text = f"Ações da {asset} mostram forte volatilidade, mas especialistas estão otimistas com os resultados trimestrais."
        sentiment_scores = self.sentiment_analyzer.analyze(example_text)

        # 3. Análise Técnica
        technical_indicators = self.technical_analyzer.analyze(historical_data)

        # 4. Modelos de ML (placeholder)
        # ...

        # 5. Geração de sinal (lógica de placeholder aprimorada)
        recommendation = self.make_recommendation(technical_indicators, sentiment_scores)

        return {
            "recommendation": recommendation,
            "confidence": 0.5, # Placeholder
            "technical_analysis": technical_indicators,
            "sentiment_analysis": sentiment_scores,
            "ml_prediction": {},
            "data_summary": {
                "rows_fetched": len(historical_data),
                "start_date": str(historical_data.index.min()),
                "end_date": str(historical_data.index.max())
            }
        }

    def make_recommendation(self, tech_indicators: dict, sentiment: dict) -> str:
        """
        Combina os resultados das análises para gerar uma recomendação final.
        Esta é uma lógica de exemplo e será aprimorada.
        """
        rsi = tech_indicators.get('rsi')
        sentiment_compound = sentiment.get('vader', {}).get('compound', 0)

        if rsi is None:
            return "NEUTRO"

        # Lógica simples baseada em RSI e sentimento
        if rsi < 30 and sentiment_compound > 0.05:
            return "COMPRA_FORTE"
        if rsi < 30:
            return "COMPRA"
        if rsi > 70 and sentiment_compound < -0.05:
            return "VENDA_FORTE"
        if rsi > 70:
            return "VENDA"
        
        return "NEUTRO"