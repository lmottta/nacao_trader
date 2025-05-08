"""
Tarefas Celery para processamento de ML e treinamento de modelos.
"""
import os
import pickle
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Union

import joblib
import numpy as np
import pandas as pd
from celery import Task
from loguru import logger
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split

from src.utils.config import settings
from src.tasks.worker import celery_app


MODEL_SAVE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "models")


class BaseTask(Task):
    """Classe base para tarefas Celery com suporte a retry."""
    
    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3, "countdown": 60}
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True


@celery_app.task(base=BaseTask, name="train_models")
def train_models(model_type: str = "random_forest") -> Dict[str, Any]:
    """
    Tarefa para treinar modelos de ML.
    
    Args:
        model_type: Tipo de modelo a ser treinado
        
    Returns:
        Dict com resultados do treinamento
    """
    try:
        logger.info(f"Iniciando treinamento de modelo: {model_type}")
        
        # Criar diretório de modelos se não existir
        os.makedirs(MODEL_SAVE_DIR, exist_ok=True)
        
        # Na implementação completa, buscaríamos dados reais do Supabase
        # Aqui, vamos gerar dados simulados para demonstração
        
        # Simulação de treinamento
        if model_type == "random_forest":
            # Gerar dados simulados
            n_samples = 1000
            
            # Recursos - preços históricos, indicadores técnicos, etc.
            # Em uma implementação real, esses recursos seriam calculados a partir de dados reais
            X = np.random.rand(n_samples, 20)  # 20 features
            
            # Alvo - movimento de preço (subida=1, descida=0)
            y = (np.random.rand(n_samples) > 0.5).astype(int)
            
            # Dividir em treino e teste
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3, random_state=42)
            
            # Criar e treinar modelo
            model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42
            )
            
            model.fit(X_train, y_train)
            
            # Avaliar modelo
            y_pred = model.predict(X_test)
            accuracy = accuracy_score(y_test, y_pred)
            precision = precision_score(y_test, y_pred)
            recall = recall_score(y_test, y_pred)
            f1 = f1_score(y_test, y_pred)
            
            # Salvar modelo
            model_path = os.path.join(MODEL_SAVE_DIR, f"{model_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.joblib")
            joblib.dump(model, model_path)
            
            metrics = {
                "accuracy": float(accuracy),
                "precision": float(precision),
                "recall": float(recall),
                "f1_score": float(f1),
                "test_samples": len(X_test),
                "feature_importances": {
                    f"feature_{i}": float(importance)
                    for i, importance in enumerate(model.feature_importances_)
                }
            }
            
            # Na implementação completa, salvaríamos estas métricas no Supabase
            
            result = {
                "status": "success",
                "model_type": model_type,
                "model_path": model_path,
                "timestamp": datetime.now().isoformat(),
                "metrics": metrics,
            }
            
            logger.success(f"Treinamento de modelo {model_type} concluído. Métricas: {metrics}")
            return result
        else:
            raise ValueError(f"Tipo de modelo não suportado: {model_type}")
    except Exception as e:
        logger.error(f"Erro no treinamento de modelo {model_type}: {e}")
        raise


@celery_app.task(base=BaseTask, name="evaluate_models")
def evaluate_models() -> Dict[str, Any]:
    """
    Tarefa para avaliar modelos existentes.
    
    Returns:
        Dict com resultados da avaliação
    """
    try:
        logger.info("Iniciando avaliação de modelos")
        
        # Listar todos os modelos
        # Na implementação completa, buscaríamos referências dos modelos no Supabase
        models_list = []
        if os.path.exists(MODEL_SAVE_DIR):
            models_list = [f for f in os.listdir(MODEL_SAVE_DIR) if f.endswith('.joblib')]
        
        if not models_list:
            logger.warning("Nenhum modelo encontrado para avaliação")
            return {
                "status": "warning",
                "message": "Nenhum modelo encontrado para avaliação",
                "timestamp": datetime.now().isoformat(),
            }
        
        # Avaliar cada modelo
        results = []
        for model_file in models_list:
            try:
                model_path = os.path.join(MODEL_SAVE_DIR, model_file)
                model = joblib.load(model_path)
                
                # Gerar dados para teste (em uma implementação real, usaríamos dados mais recentes)
                n_samples = 500
                X_eval = np.random.rand(n_samples, 20)  # Mesmas 20 features
                y_eval = (np.random.rand(n_samples) > 0.5).astype(int)
                
                # Avaliar
                y_pred = model.predict(X_eval)
                accuracy = accuracy_score(y_eval, y_pred)
                
                results.append({
                    "model_file": model_file,
                    "model_path": model_path,
                    "accuracy": float(accuracy),
                    "samples": n_samples,
                })
            except Exception as model_error:
                logger.error(f"Erro ao avaliar modelo {model_file}: {model_error}")
                results.append({
                    "model_file": model_file,
                    "error": str(model_error)
                })
        
        # Ordenar modelos por desempenho
        valid_results = [r for r in results if "error" not in r]
        if valid_results:
            best_model = max(valid_results, key=lambda x: x["accuracy"])
        else:
            best_model = None
        
        return {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "models_evaluated": len(results),
            "results": results,
            "best_model": best_model,
        }
    except Exception as e:
        logger.error(f"Erro na avaliação de modelos: {e}")
        raise


@celery_app.task(base=BaseTask, name="generate_predictions")
def generate_predictions(
    asset_ids: Optional[List[str]] = None,
    model_file: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Tarefa para gerar previsões para ativos usando um modelo específico.
    
    Args:
        asset_ids: Lista de IDs de ativos (opcional, se não for fornecido, gera para todos)
        model_file: Nome do arquivo do modelo a ser usado (opcional, se não for fornecido, usa o melhor)
        
    Returns:
        Dict com previsões
    """
    try:
        logger.info(f"Iniciando geração de previsões para {len(asset_ids) if asset_ids else 'todos'} ativos")
        
        # Se não foi especificado um modelo, encontrar o melhor disponível
        if not model_file:
            eval_results = evaluate_models()
            if eval_results["status"] == "success" and eval_results["best_model"]:
                model_file = eval_results["best_model"]["model_file"]
            else:
                raise ValueError("Nenhum modelo disponível para gerar previsões")
        
        # Carregar modelo
        model_path = os.path.join(MODEL_SAVE_DIR, model_file)
        model = joblib.load(model_path)
        
        # Obter ativos - na implementação completa, buscaríamos do Supabase
        # Se asset_ids for None, gerar para todos (limite de 10 para demonstração)
        if not asset_ids:
            asset_ids = [f"ASSET_{i}" for i in range(1, 11)]
        
        # Para cada ativo, gerar features (em uma implementação real, calculadas a partir de dados reais)
        predictions = []
        for asset_id in asset_ids:
            # Simular features do ativo
            features = np.random.rand(1, 20)  # 20 features
            
            # Gerar previsão
            prediction = int(model.predict(features)[0])
            probability = float(model.predict_proba(features)[0][prediction])
            
            # Mapear para direção de sinal
            direction = "CALL" if prediction == 1 else "PUT"
            
            predictions.append({
                "asset_id": asset_id,
                "direction": direction,
                "confidence": probability,
                "timestamp": datetime.now().isoformat(),
            })
        
        return {
            "status": "success",
            "model_file": model_file,
            "timestamp": datetime.now().isoformat(),
            "predictions_count": len(predictions),
            "predictions": predictions,
        }
    except Exception as e:
        logger.error(f"Erro na geração de previsões: {e}")
        raise 