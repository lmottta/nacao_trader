"""
Modelos de Machine Learning para previsão de direção de preços.
"""
from enum import Enum
from typing import Dict, List, Optional, Union, Any
from datetime import datetime
import pickle
import os

import pandas as pd
import numpy as np
from pydantic import BaseModel, Field
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

from loguru import logger


class ModelType(str, Enum):
    """Tipos de modelos ML suportados."""
    RANDOM_FOREST = "random_forest"
    GRADIENT_BOOSTING = "gradient_boosting"
    LOGISTIC_REGRESSION = "logistic_regression"
    SVM = "svm"
    ENSEMBLE = "ensemble"


class ModelConfig(BaseModel):
    """Configuração para modelos de ML."""
    model_type: ModelType
    features: List[str]
    target: str
    hyperparameters: Dict[str, Any]
    lookback_periods: int = 10
    train_test_ratio: float = 0.8
    random_state: int = 42
    scaler: bool = True


class ModelPerformanceMetrics(BaseModel):
    """Métricas de performance do modelo."""
    accuracy: float
    precision: float
    recall: float
    f1: float
    training_size: int
    test_size: int
    created_at: datetime = Field(default_factory=datetime.now)
    asset_id: Optional[str] = None
    timeframe: Optional[str] = None


class MLModel:
    """Classe base para modelos de ML."""
    
    def __init__(self, config: ModelConfig):
        """
        Inicializa um modelo de ML.
        
        Args:
            config: Configuração do modelo
        """
        self.config = config
        self.model = None
        self.scaler = StandardScaler() if config.scaler else None
        self.performance = None
        self.is_trained = False
        self._initialize_model()
    
    def _initialize_model(self):
        """Inicializa o modelo baseado na configuração."""
        model_type = self.config.model_type
        params = self.config.hyperparameters
        
        if model_type == ModelType.RANDOM_FOREST:
            self.model = RandomForestClassifier(**params)
        elif model_type == ModelType.GRADIENT_BOOSTING:
            self.model = GradientBoostingClassifier(**params)
        elif model_type == ModelType.LOGISTIC_REGRESSION:
            self.model = LogisticRegression(**params)
        elif model_type == ModelType.SVM:
            self.model = SVC(probability=True, **params)
        elif model_type == ModelType.ENSEMBLE:
            # Para ensemble, criamos múltiplos modelos
            self.models = {
                "rf": RandomForestClassifier(**params.get("random_forest", {})),
                "gb": GradientBoostingClassifier(**params.get("gradient_boosting", {})),
                "lr": LogisticRegression(**params.get("logistic_regression", {})),
            }
            self.weights = params.get("weights", {"rf": 0.4, "gb": 0.4, "lr": 0.2})
        else:
            raise ValueError(f"Tipo de modelo não suportado: {model_type}")
    
    def preprocess_data(self, df: pd.DataFrame) -> tuple:
        """
        Pré-processa os dados para treinamento ou predição.
        
        Args:
            df: DataFrame com os dados
            
        Returns:
            Tupla (X, y) com features e target
        """
        # Garantir que todas as features existem
        for feature in self.config.features:
            if feature not in df.columns:
                raise ValueError(f"Feature '{feature}' não encontrada no DataFrame")
        
        X = df[self.config.features].copy()
        
        # Processar coluna target somente se existir (para inferência ela pode não existir)
        y = None
        if self.config.target in df.columns:
            y = df[self.config.target].copy()
        
        # Escalar se necessário
        if self.scaler is not None and self.is_trained:
            X = pd.DataFrame(
                self.scaler.transform(X),
                columns=X.columns,
                index=X.index
            )
        
        return X, y
    
    def train(self, df: pd.DataFrame) -> ModelPerformanceMetrics:
        """
        Treina o modelo com os dados fornecidos.
        
        Args:
            df: DataFrame com os dados de treinamento
            
        Returns:
            Métricas de performance do modelo
        """
        X, y = self.preprocess_data(df)
        
        if y is None:
            raise ValueError("Coluna target não encontrada no DataFrame")
        
        # Split treino/teste
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, 
            test_size=1-self.config.train_test_ratio,
            random_state=self.config.random_state
        )
        
        # Escalar apenas dados de treino
        if self.scaler is not None:
            X_train = pd.DataFrame(
                self.scaler.fit_transform(X_train),
                columns=X_train.columns,
                index=X_train.index
            )
            X_test = pd.DataFrame(
                self.scaler.transform(X_test),
                columns=X_test.columns,
                index=X_test.index
            )
        
        if self.config.model_type == ModelType.ENSEMBLE:
            # Treinar cada modelo no ensemble
            for name, model in self.models.items():
                model.fit(X_train, y_train)
            
            # Predição combinada ponderada
            y_pred = self.predict(X_test.copy())
        else:
            # Treinar modelo único
            self.model.fit(X_train, y_train)
            y_pred = self.model.predict(X_test)
        
        # Calcular métricas
        performance = ModelPerformanceMetrics(
            accuracy=accuracy_score(y_test, y_pred),
            precision=precision_score(y_test, y_pred, average='weighted'),
            recall=recall_score(y_test, y_pred, average='weighted'),
            f1=f1_score(y_test, y_pred, average='weighted'),
            training_size=len(X_train),
            test_size=len(X_test)
        )
        
        self.performance = performance
        self.is_trained = True
        
        logger.info(f"Modelo treinado com accuracy: {performance.accuracy:.4f}")
        return performance
    
    def predict(self, X: Union[pd.DataFrame, np.ndarray]) -> np.ndarray:
        """
        Faz predições com o modelo treinado.
        
        Args:
            X: DataFrame ou array com os dados para predição
            
        Returns:
            Array com as predições
        """
        if not self.is_trained:
            raise ValueError("O modelo precisa ser treinado antes de fazer predições")
        
        # Se X for um DataFrame, preprocess
        if isinstance(X, pd.DataFrame):
            X, _ = self.preprocess_data(X)
        
        if self.config.model_type == ModelType.ENSEMBLE:
            # Predição ponderada
            predictions = {}
            for name, model in self.models.items():
                if hasattr(model, "predict_proba"):
                    pred_prob = model.predict_proba(X)
                    predictions[name] = pred_prob
                else:
                    predictions[name] = model.predict(X)
            
            # Combinar predições ponderadas
            weighted_preds = None
            for name, pred in predictions.items():
                weight = self.weights.get(name, 1.0/len(self.models))
                if weighted_preds is None:
                    weighted_preds = weight * pred
                else:
                    weighted_preds += weight * pred
            
            # Obter a classe com maior probabilidade
            return np.argmax(weighted_preds, axis=1)
        else:
            return self.model.predict(X)
    
    def predict_proba(self, X: Union[pd.DataFrame, np.ndarray]) -> np.ndarray:
        """
        Retorna probabilidades de predição.
        
        Args:
            X: DataFrame ou array com os dados para predição
            
        Returns:
            Array com as probabilidades para cada classe
        """
        if not self.is_trained:
            raise ValueError("O modelo precisa ser treinado antes de fazer predições")
        
        # Se X for um DataFrame, preprocess
        if isinstance(X, pd.DataFrame):
            X, _ = self.preprocess_data(X)
        
        if self.config.model_type == ModelType.ENSEMBLE:
            # Predição ponderada
            predictions = {}
            for name, model in self.models.items():
                if hasattr(model, "predict_proba"):
                    pred_prob = model.predict_proba(X)
                    predictions[name] = pred_prob
                else:
                    pred = model.predict(X)
                    # Converter para one-hot
                    n_classes = len(np.unique(pred))
                    one_hot = np.zeros((pred.shape[0], n_classes))
                    for i, p in enumerate(pred):
                        one_hot[i, p] = 1
                    predictions[name] = one_hot
            
            # Combinar predições ponderadas
            weighted_preds = None
            for name, pred in predictions.items():
                weight = self.weights.get(name, 1.0/len(self.models))
                if weighted_preds is None:
                    weighted_preds = weight * pred
                else:
                    weighted_preds += weight * pred
            
            # Normalizar
            row_sums = weighted_preds.sum(axis=1)
            return weighted_preds / row_sums[:, np.newaxis]
        else:
            if hasattr(self.model, "predict_proba"):
                return self.model.predict_proba(X)
            else:
                # Para modelos que não têm predict_proba
                preds = self.model.predict(X)
                # Converter para probabilidades simuladas
                n_classes = len(np.unique(preds))
                proba = np.zeros((preds.shape[0], n_classes))
                for i, p in enumerate(preds):
                    proba[i, p] = 0.9  # Confiança alta na classe predita
                    # Distribuir o restante igualmente entre as outras classes
                    for j in range(n_classes):
                        if j != p:
                            proba[i, j] = 0.1 / (n_classes - 1)
                return proba
    
    def save(self, path: str):
        """
        Salva o modelo em disco.
        
        Args:
            path: Caminho para salvar o modelo
        """
        if not self.is_trained:
            raise ValueError("O modelo precisa ser treinado antes de ser salvo")
        
        # Criar diretório se não existir
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        # Salvar o modelo
        with open(path, 'wb') as f:
            pickle.dump({
                'model': self.model if self.config.model_type != ModelType.ENSEMBLE else self.models,
                'scaler': self.scaler,
                'config': self.config.dict(),
                'performance': self.performance.dict() if self.performance else None,
                'is_trained': self.is_trained,
                'weights': getattr(self, 'weights', None)
            }, f)
        
        logger.info(f"Modelo salvo em {path}")
    
    @classmethod
    def load(cls, path: str) -> 'MLModel':
        """
        Carrega um modelo do disco.
        
        Args:
            path: Caminho do modelo salvo
            
        Returns:
            Modelo carregado
        """
        with open(path, 'rb') as f:
            data = pickle.load(f)
        
        # Reconstruir o modelo
        config = ModelConfig(**data['config'])
        instance = cls(config)
        
        if config.model_type == ModelType.ENSEMBLE:
            instance.models = data['model']
        else:
            instance.model = data['model']
            
        instance.scaler = data['scaler']
        
        if data['performance']:
            instance.performance = ModelPerformanceMetrics(**data['performance'])
            
        instance.is_trained = data['is_trained']
        
        if 'weights' in data and data['weights']:
            instance.weights = data['weights']
        
        logger.info(f"Modelo carregado de {path}")
        return instance


class DirectionPredictionModel(MLModel):
    """
    Modelo específico para predição de direção de preço (alta, baixa, neutro).
    Estende a classe base MLModel com funcionalidades específicas para trading.
    """
    
    @staticmethod
    def generate_features(df: pd.DataFrame, lookback: int = 10) -> pd.DataFrame:
        """
        Gera features técnicas para predição de direção.
        
        Args:
            df: DataFrame com dados OHLCV
            lookback: Períodos para lookback de features
            
        Returns:
            DataFrame com features geradas
        """
        # Verificar colunas obrigatórias
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Colunas obrigatórias ausentes: {missing_cols}")
        
        # Criar cópia para não modificar o original
        result = df.copy()
        
        # 1. Retornos
        result['return_1d'] = result['close'].pct_change(1)
        result['return_2d'] = result['close'].pct_change(2)
        result['return_5d'] = result['close'].pct_change(5)
        result['return_10d'] = result['close'].pct_change(10)
        
        # 2. Médias móveis
        result['sma_5'] = result['close'].rolling(window=5).mean()
        result['sma_10'] = result['close'].rolling(window=10).mean()
        result['sma_20'] = result['close'].rolling(window=20).mean()
        result['sma_50'] = result['close'].rolling(window=50).mean()
        
        # 3. Distância percentual das médias
        result['dist_sma_5'] = (result['close'] / result['sma_5'] - 1) * 100
        result['dist_sma_10'] = (result['close'] / result['sma_10'] - 1) * 100
        result['dist_sma_20'] = (result['close'] / result['sma_20'] - 1) * 100
        
        # 4. RSI (Relative Strength Index)
        delta = result['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(window=14).mean()
        avg_loss = loss.rolling(window=14).mean()
        rs = avg_gain / avg_loss
        result['rsi'] = 100 - (100 / (1 + rs))
        
        # 5. MACD (Moving Average Convergence Divergence)
        result['ema_12'] = result['close'].ewm(span=12, adjust=False).mean()
        result['ema_26'] = result['close'].ewm(span=26, adjust=False).mean()
        result['macd'] = result['ema_12'] - result['ema_26']
        result['macd_signal'] = result['macd'].ewm(span=9, adjust=False).mean()
        result['macd_hist'] = result['macd'] - result['macd_signal']
        
        # 6. Bollinger Bands
        result['bb_middle'] = result['close'].rolling(window=20).mean()
        result['bb_stddev'] = result['close'].rolling(window=20).std()
        result['bb_upper'] = result['bb_middle'] + 2 * result['bb_stddev']
        result['bb_lower'] = result['bb_middle'] - 2 * result['bb_stddev']
        result['bb_width'] = (result['bb_upper'] - result['bb_lower']) / result['bb_middle']
        result['bb_pct'] = (result['close'] - result['bb_lower']) / (result['bb_upper'] - result['bb_lower'])
        
        # 7. Volume features
        result['volume_change'] = result['volume'].pct_change(1)
        result['volume_sma_5'] = result['volume'].rolling(window=5).mean()
        result['volume_ratio'] = result['volume'] / result['volume_sma_5']
        
        # 8. Volatilidade
        result['true_range'] = np.maximum(
            result['high'] - result['low'],
            np.maximum(
                abs(result['high'] - result['close'].shift(1)),
                abs(result['low'] - result['close'].shift(1))
            )
        )
        result['atr'] = result['true_range'].rolling(window=14).mean()
        result['atr_pct'] = result['atr'] / result['close'] * 100
        
        # 9. Target: direção do preço (para treinamento)
        # 1 = alta, 0 = neutro, -1 = baixa (usando threshold de 0.5%)
        result['target'] = 0
        # Alta significativa
        result.loc[result['return_1d'].shift(-1) > 0.005, 'target'] = 1
        # Baixa significativa
        result.loc[result['return_1d'].shift(-1) < -0.005, 'target'] = -1
        
        # Remover linhas com NaN
        result = result.dropna()
        
        return result
    
    @staticmethod
    def get_default_config() -> ModelConfig:
        """
        Retorna uma configuração padrão para o modelo.
        
        Returns:
            Configuração padrão
        """
        return ModelConfig(
            model_type=ModelType.ENSEMBLE,
            features=[
                'return_1d', 'return_2d', 'return_5d',
                'dist_sma_5', 'dist_sma_10', 'dist_sma_20',
                'rsi', 'macd', 'macd_hist',
                'bb_pct', 'bb_width', 'volume_ratio', 'atr_pct'
            ],
            target='target',
            hyperparameters={
                "random_forest": {
                    "n_estimators": 100,
                    "max_depth": 5,
                    "random_state": 42
                },
                "gradient_boosting": {
                    "n_estimators": 100,
                    "learning_rate": 0.1,
                    "max_depth": 3,
                    "random_state": 42
                },
                "logistic_regression": {
                    "C": 1.0,
                    "max_iter": 1000,
                    "random_state": 42
                },
                "weights": {
                    "rf": 0.4,
                    "gb": 0.4,
                    "lr": 0.2
                }
            },
            lookback_periods=50,
            train_test_ratio=0.8,
            random_state=42,
            scaler=True
        )
    
    def predict_direction(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Prediz a direção do preço e retorna detalhes.
        
        Args:
            df: DataFrame com dados OHLCV
            
        Returns:
            Dicionário com predição e detalhes
        """
        # Gerar features
        features_df = self.generate_features(df)
        
        # Últimos dados para predição
        X = features_df.iloc[-1:][self.config.features]
        
        # Fazer predição
        direction_class = self.predict(X)[0]
        probabilities = self.predict_proba(X)[0]
        
        # Mapear classe para direção
        if direction_class == 1:
            direction = "CALL"
        elif direction_class == -1:
            direction = "PUT"
        else:
            direction = "NEUTRAL"
        
        # Calcular confiança
        confidence = probabilities[np.where(np.array([0, 1, -1]) == direction_class)[0][0]]
        
        # Extrair valores de indicadores
        indicators = {
            "rsi": float(features_df.iloc[-1]['rsi']),
            "macd": {
                "value": float(features_df.iloc[-1]['macd']),
                "signal": float(features_df.iloc[-1]['macd_signal']),
                "histogram": float(features_df.iloc[-1]['macd_hist']),
                "interpretation": "bullish" if features_df.iloc[-1]['macd'] > 0 else "bearish"
            },
            "sma": {
                "sma_5": float(features_df.iloc[-1]['sma_5']),
                "sma_10": float(features_df.iloc[-1]['sma_10']),
                "sma_20": float(features_df.iloc[-1]['sma_20']),
                "interpretation": "bullish" if features_df.iloc[-1]['dist_sma_20'] > 0 else "bearish"
            },
            "bollinger": {
                "upper": float(features_df.iloc[-1]['bb_upper']),
                "middle": float(features_df.iloc[-1]['bb_middle']),
                "lower": float(features_df.iloc[-1]['bb_lower']),
                "width": float(features_df.iloc[-1]['bb_width']),
                "pct": float(features_df.iloc[-1]['bb_pct']),
                "interpretation": self._interpret_bollinger(features_df.iloc[-1]['bb_pct'])
            },
            "volume": {
                "change": float(features_df.iloc[-1]['volume_change']),
                "sma_ratio": float(features_df.iloc[-1]['volume_ratio']),
                "interpretation": "high" if features_df.iloc[-1]['volume_ratio'] > 1.5 else "low" if features_df.iloc[-1]['volume_ratio'] < 0.7 else "normal"
            },
            "additional": {
                "atr": float(features_df.iloc[-1]['atr']),
                "atr_pct": float(features_df.iloc[-1]['atr_pct']),
                "returns": {
                    "1d": float(features_df.iloc[-1]['return_1d']),
                    "5d": float(features_df.iloc[-1]['return_5d'])
                }
            }
        }
        
        # Calculando preço atual e alvos de preço
        current_price = float(df.iloc[-1]['close'])
        
        # Cria volatilidade estimada baseada no ATR
        volatility = features_df.iloc[-1]['atr_pct'] / 100
        
        # Calcular price_target e stop_loss se a direção não for neutra
        if direction != "NEUTRAL":
            if direction == "CALL":
                price_target = round(current_price * (1 + volatility * 2), 2)
                stop_loss = round(current_price * (1 - volatility), 2)
            else:  # PUT
                price_target = round(current_price * (1 - volatility * 2), 2)
                stop_loss = round(current_price * (1 + volatility), 2)
        else:
            price_target = None
            stop_loss = None
        
        return {
            "direction": direction,
            "confidence": float(confidence),
            "price_target": price_target,
            "stop_loss": stop_loss,
            "current_price": current_price,
            "indicators": indicators,
            "model_type": self.config.model_type,
            "timestamp": datetime.now().isoformat()
        }
    
    @staticmethod
    def _interpret_bollinger(bb_pct: float) -> str:
        """
        Interpreta a posição nas Bandas de Bollinger.
        
        Args:
            bb_pct: Percentual dentro das bandas (0-1)
            
        Returns:
            Interpretação textual
        """
        if bb_pct > 0.95:
            return "overbought"
        elif bb_pct < 0.05:
            return "oversold"
        elif bb_pct > 0.8:
            return "upper_band"
        elif bb_pct < 0.2:
            return "lower_band"
        else:
            return "middle_band" 