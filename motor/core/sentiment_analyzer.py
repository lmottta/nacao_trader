from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from textblob import TextBlob

class SentimentAnalyzer:
    """Classe para realizar análise de sentimento em textos."""

    def __init__(self):
        self.vader_analyzer = SentimentIntensityAnalyzer()

    def analyze_vader(self, text: str) -> dict:
        """Analisa o sentimento de um texto usando VADER."""
        return self.vader_analyzer.polarity_scores(text)

    def analyze_textblob(self, text: str) -> dict:
        """Analisa o sentimento de um texto usando TextBlob."""
        blob = TextBlob(text)
        return {
            'polarity': blob.sentiment.polarity,
            'subjectivity': blob.sentiment.subjectivity
        }

    def analyze(self, text: str) -> dict:
        """
        Executa uma análise de sentimento combinada.
        Por enquanto, retorna a análise do VADER.
        """
        # No futuro, podemos adicionar uma lógica para combinar os resultados
        # ou buscar notícias e integrá-las aqui.
        vader_scores = self.analyze_vader(text)
        textblob_scores = self.analyze_textblob(text)

        return {
            'vader': vader_scores,
            'textblob': textblob_scores
        }