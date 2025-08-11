from typing import Dict, List, Optional, Any, Callable, Union, Set
from datetime import datetime, timezone, timedelta
from enum import Enum
from dataclasses import dataclass, field
import asyncio
import logging
import statistics
import math
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

class QualityDimension(Enum):
    """Dimensões de qualidade de dados."""
    COMPLETENESS = "completeness"        # Completude
    ACCURACY = "accuracy"                # Precisão
    CONSISTENCY = "consistency"          # Consistência
    TIMELINESS = "timeliness"            # Pontualidade
    VALIDITY = "validity"                # Validade
    UNIQUENESS = "uniqueness"            # Unicidade
    INTEGRITY = "integrity"              # Integridade
    RELIABILITY = "reliability"          # Confiabilidade

class QualityLevel(Enum):
    """Níveis de qualidade."""
    EXCELLENT = "excellent"              # Excelente (90-100%)
    GOOD = "good"                        # Bom (70-89%)
    FAIR = "fair"                        # Razoável (50-69%)
    POOR = "poor"                        # Ruim (30-49%)
    CRITICAL = "critical"                # Crítico (0-29%)

@dataclass
class QualityMetrics:
    """Métricas de qualidade de dados."""
    dimension: QualityDimension
    score: float                         # Score 0-100
    level: QualityLevel
    details: Dict[str, Any] = field(default_factory=dict)
    issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    @classmethod
    def from_score(cls, dimension: QualityDimension, score: float, 
                   details: Dict[str, Any] = None) -> 'QualityMetrics':
        """Cria métricas a partir de um score."""
        level = cls._score_to_level(score)
        return cls(
            dimension=dimension,
            score=score,
            level=level,
            details=details or {}
        )
    
    @staticmethod
    def _score_to_level(score: float) -> QualityLevel:
        """Converte score para nível de qualidade."""
        if score >= 90:
            return QualityLevel.EXCELLENT
        elif score >= 70:
            return QualityLevel.GOOD
        elif score >= 50:
            return QualityLevel.FAIR
        elif score >= 30:
            return QualityLevel.POOR
        else:
            return QualityLevel.CRITICAL

@dataclass
class QualityThreshold:
    """Limites de qualidade para alertas."""
    dimension: QualityDimension
    min_score: float                     # Score mínimo aceitável
    warning_score: float                 # Score para aviso
    critical_score: float                # Score crítico
    enabled: bool = True
    
    def check_threshold(self, score: float) -> Optional[str]:
        """Verifica se o score viola algum limite."""
        if not self.enabled:
            return None
        
        if score < self.critical_score:
            return "critical"
        elif score < self.warning_score:
            return "warning"
        elif score < self.min_score:
            return "below_minimum"
        
        return None

@dataclass
class QualityReport:
    """Relatório de qualidade de dados."""
    source: str
    symbol: str
    data_type: str
    overall_score: float
    overall_level: QualityLevel
    metrics: Dict[QualityDimension, QualityMetrics] = field(default_factory=dict)
    threshold_violations: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def get_metric(self, dimension: QualityDimension) -> Optional[QualityMetrics]:
        """Obtém métrica por dimensão."""
        return self.metrics.get(dimension)
    
    def add_recommendation(self, recommendation: str):
        """Adiciona recomendação ao relatório."""
        if recommendation not in self.recommendations:
            self.recommendations.append(recommendation)
    
    def get_critical_issues(self) -> List[QualityMetrics]:
        """Obtém métricas com nível crítico."""
        return [m for m in self.metrics.values() if m.level == QualityLevel.CRITICAL]
    
    def get_poor_metrics(self) -> List[QualityMetrics]:
        """Obtém métricas com qualidade ruim ou crítica."""
        return [m for m in self.metrics.values() 
                if m.level in [QualityLevel.POOR, QualityLevel.CRITICAL]]

class DataQualityChecker:
    """Verificador de qualidade de dados que analisa múltiplas dimensões."""
    
    def __init__(self):
        self.thresholds: Dict[QualityDimension, QualityThreshold] = {}
        self.quality_history: deque = deque(maxlen=1000)
        self.source_profiles: Dict[str, Dict] = defaultdict(dict)
        
        # Configurações
        self.sample_size_for_analysis = 100
        self.historical_window_hours = 24
        
        # Callbacks
        self.on_quality_degradation: Optional[Callable] = None
        self.on_critical_quality: Optional[Callable] = None
        
        # Configurar limites padrão
        self._setup_default_thresholds()
        
        logger.info("DataQualityChecker inicializado")
    
    def _setup_default_thresholds(self):
        """Configura limites padrão de qualidade."""
        default_thresholds = {
            QualityDimension.COMPLETENESS: QualityThreshold(
                QualityDimension.COMPLETENESS, 80.0, 70.0, 50.0
            ),
            QualityDimension.ACCURACY: QualityThreshold(
                QualityDimension.ACCURACY, 85.0, 75.0, 60.0
            ),
            QualityDimension.CONSISTENCY: QualityThreshold(
                QualityDimension.CONSISTENCY, 90.0, 80.0, 65.0
            ),
            QualityDimension.TIMELINESS: QualityThreshold(
                QualityDimension.TIMELINESS, 85.0, 70.0, 50.0
            ),
            QualityDimension.VALIDITY: QualityThreshold(
                QualityDimension.VALIDITY, 95.0, 85.0, 70.0
            ),
            QualityDimension.RELIABILITY: QualityThreshold(
                QualityDimension.RELIABILITY, 90.0, 80.0, 60.0
            )
        }
        
        for dimension, threshold in default_thresholds.items():
            self.set_threshold(threshold)
    
    def set_threshold(self, threshold: QualityThreshold):
        """Define limite de qualidade para uma dimensão."""
        self.thresholds[threshold.dimension] = threshold
        logger.info(f"Limite definido para {threshold.dimension.value}: {threshold.min_score}%")
    
    def get_threshold(self, dimension: QualityDimension) -> Optional[QualityThreshold]:
        """Obtém limite de qualidade para uma dimensão."""
        return self.thresholds.get(dimension)
    
    async def check_data_quality(self, source: str, symbol: str, data_type: str, 
                                data: Any, historical_data: List[Any] = None) -> QualityReport:
        """Verifica qualidade dos dados em múltiplas dimensões."""
        report = QualityReport(
            source=source,
            symbol=symbol,
            data_type=data_type,
            overall_score=0.0,
            overall_level=QualityLevel.CRITICAL
        )
        
        # Verificar cada dimensão de qualidade
        dimensions_to_check = [
            QualityDimension.COMPLETENESS,
            QualityDimension.ACCURACY,
            QualityDimension.CONSISTENCY,
            QualityDimension.TIMELINESS,
            QualityDimension.VALIDITY,
            QualityDimension.RELIABILITY
        ]
        
        total_score = 0.0
        valid_dimensions = 0
        
        for dimension in dimensions_to_check:
            try:
                metric = await self._check_dimension(dimension, source, symbol, 
                                                    data_type, data, historical_data)
                if metric:
                    report.metrics[dimension] = metric
                    total_score += metric.score
                    valid_dimensions += 1
                    
                    # Verificar violações de limite
                    threshold = self.get_threshold(dimension)
                    if threshold:
                        violation = threshold.check_threshold(metric.score)
                        if violation:
                            report.threshold_violations.append(
                                f"{dimension.value}: {violation} (score: {metric.score:.1f}%)"
                            )
                    
                    # Adicionar recomendações da métrica
                    for rec in metric.recommendations:
                        report.add_recommendation(rec)
                        
            except Exception as e:
                logger.error(f"Erro ao verificar dimensão {dimension.value}: {e}")
        
        # Calcular score geral
        if valid_dimensions > 0:
            report.overall_score = total_score / valid_dimensions
            report.overall_level = QualityMetrics._score_to_level(report.overall_score)
        
        # Adicionar recomendações gerais
        self._add_general_recommendations(report)
        
        # Registrar no histórico
        self._record_quality_check(report)
        
        # Chamar callbacks se necessário
        await self._handle_quality_callbacks(report)
        
        logger.debug(f"Qualidade verificada para {source}/{symbol}: {report.overall_score:.1f}%")
        return report
    
    async def _check_dimension(self, dimension: QualityDimension, source: str, 
                              symbol: str, data_type: str, data: Any, 
                              historical_data: List[Any] = None) -> Optional[QualityMetrics]:
        """Verifica uma dimensão específica de qualidade."""
        if dimension == QualityDimension.COMPLETENESS:
            return self._check_completeness(data)
        elif dimension == QualityDimension.ACCURACY:
            return self._check_accuracy(data, historical_data)
        elif dimension == QualityDimension.CONSISTENCY:
            return self._check_consistency(data, historical_data)
        elif dimension == QualityDimension.TIMELINESS:
            return self._check_timeliness(data)
        elif dimension == QualityDimension.VALIDITY:
            return self._check_validity(data, data_type)
        elif dimension == QualityDimension.RELIABILITY:
            return self._check_reliability(source, symbol, historical_data)
        
        return None
    
    def _check_completeness(self, data: Any) -> QualityMetrics:
        """Verifica completude dos dados."""
        if isinstance(data, dict):
            total_fields = len(data)
            complete_fields = sum(1 for v in data.values() if v is not None and v != '')
            
            if total_fields == 0:
                score = 0.0
            else:
                score = (complete_fields / total_fields) * 100
            
            details = {
                "total_fields": total_fields,
                "complete_fields": complete_fields,
                "missing_fields": total_fields - complete_fields
            }
            
            metric = QualityMetrics.from_score(QualityDimension.COMPLETENESS, score, details)
            
            if score < 80:
                metric.issues.append(f"Dados incompletos: {complete_fields}/{total_fields} campos")
                metric.recommendations.append("Verificar fonte de dados para campos ausentes")
            
            return metric
        
        elif data is not None:
            # Para dados não-dict, considerar completo se não for None
            return QualityMetrics.from_score(QualityDimension.COMPLETENESS, 100.0)
        
        else:
            metric = QualityMetrics.from_score(QualityDimension.COMPLETENESS, 0.0)
            metric.issues.append("Dados completamente ausentes")
            metric.recommendations.append("Verificar conectividade com a fonte")
            return metric
    
    def _check_accuracy(self, data: Any, historical_data: List[Any] = None) -> QualityMetrics:
        """Verifica precisão dos dados."""
        score = 100.0  # Assumir precisão perfeita por padrão
        details = {}
        issues = []
        recommendations = []
        
        # Verificar valores numéricos para outliers
        numeric_value = self._extract_numeric_value(data)
        if numeric_value is not None and historical_data:
            historical_values = [self._extract_numeric_value(d) for d in historical_data[-50:]]
            historical_values = [v for v in historical_values if v is not None]
            
            if len(historical_values) >= 5:
                median = statistics.median(historical_values)
                mad = statistics.median([abs(v - median) for v in historical_values])
                
                if mad > 0:
                    # Usar MAD (Median Absolute Deviation) para detectar outliers
                    deviation = abs(numeric_value - median) / mad
                    
                    if deviation > 3.5:  # Outlier extremo
                        score = 30.0
                        issues.append(f"Valor suspeito detectado: {numeric_value} (desvio: {deviation:.2f})")
                        recommendations.append("Verificar fonte e validar valor manualmente")
                    elif deviation > 2.5:  # Outlier moderado
                        score = 70.0
                        issues.append(f"Valor atípico detectado: {numeric_value}")
                        recommendations.append("Monitorar valores futuros desta fonte")
                    
                    details["deviation_score"] = deviation
                    details["median_reference"] = median
        
        # Verificar formato de dados
        if isinstance(data, dict):
            # Verificar se campos numéricos são realmente numéricos
            numeric_fields = ['price', 'volume', 'high', 'low', 'open', 'close']
            for field in numeric_fields:
                if field in data:
                    try:
                        float(data[field])
                    except (ValueError, TypeError):
                        score = min(score, 60.0)
                        issues.append(f"Campo {field} não é numérico válido")
                        recommendations.append(f"Verificar formato do campo {field}")
        
        return QualityMetrics.from_score(
            QualityDimension.ACCURACY, score, details
        )
    
    def _check_consistency(self, data: Any, historical_data: List[Any] = None) -> QualityMetrics:
        """Verifica consistência dos dados."""
        score = 100.0
        details = {}
        issues = []
        recommendations = []
        
        if isinstance(data, dict) and historical_data:
            # Verificar consistência de estrutura
            recent_data = historical_data[-10:] if len(historical_data) >= 10 else historical_data
            
            if recent_data:
                # Verificar se campos estão consistentes
                current_fields = set(data.keys())
                
                field_consistency = []
                for hist_data in recent_data:
                    if isinstance(hist_data, dict):
                        hist_fields = set(hist_data.keys())
                        consistency = len(current_fields & hist_fields) / len(current_fields | hist_fields)
                        field_consistency.append(consistency)
                
                if field_consistency:
                    avg_consistency = statistics.mean(field_consistency) * 100
                    score = min(score, avg_consistency)
                    
                    if avg_consistency < 80:
                        issues.append(f"Inconsistência na estrutura de dados: {avg_consistency:.1f}%")
                        recommendations.append("Verificar mudanças na API da fonte")
                    
                    details["field_consistency"] = avg_consistency
        
        # Verificar consistência de tipos de dados
        if isinstance(data, dict):
            type_issues = 0
            total_fields = 0
            
            for key, value in data.items():
                total_fields += 1
                
                # Verificar se campos esperados têm tipos corretos
                if key in ['price', 'volume', 'high', 'low', 'open', 'close']:
                    if not isinstance(value, (int, float)) and value is not None:
                        type_issues += 1
                elif key in ['symbol', 'name', 'currency']:
                    if not isinstance(value, str) and value is not None:
                        type_issues += 1
            
            if total_fields > 0:
                type_consistency = ((total_fields - type_issues) / total_fields) * 100
                score = min(score, type_consistency)
                
                if type_issues > 0:
                    issues.append(f"Inconsistência de tipos: {type_issues} campos")
                    recommendations.append("Verificar conversão de tipos na fonte")
                
                details["type_consistency"] = type_consistency
        
        metric = QualityMetrics.from_score(QualityDimension.CONSISTENCY, score, details)
        metric.issues.extend(issues)
        metric.recommendations.extend(recommendations)
        
        return metric
    
    def _check_timeliness(self, data: Any) -> QualityMetrics:
        """Verifica pontualidade dos dados."""
        score = 100.0
        details = {}
        issues = []
        recommendations = []
        
        timestamp = self._extract_timestamp(data)
        
        if timestamp:
            now = datetime.now(timezone.utc)
            age = now - timestamp
            age_minutes = age.total_seconds() / 60
            
            details["data_age_minutes"] = age_minutes
            details["timestamp"] = timestamp.isoformat()
            
            # Calcular score baseado na idade
            if age_minutes <= 5:  # Muito recente
                score = 100.0
            elif age_minutes <= 15:  # Recente
                score = 90.0
            elif age_minutes <= 60:  # Aceitável
                score = 70.0
            elif age_minutes <= 240:  # Desatualizado
                score = 40.0
            else:  # Muito desatualizado
                score = 10.0
            
            if age_minutes > 60:
                issues.append(f"Dados desatualizados: {age_minutes:.1f} minutos")
                recommendations.append("Verificar frequência de atualização da fonte")
        
        else:
            score = 0.0
            issues.append("Timestamp ausente nos dados")
            recommendations.append("Adicionar timestamp aos dados coletados")
        
        metric = QualityMetrics.from_score(QualityDimension.TIMELINESS, score, details)
        metric.issues.extend(issues)
        metric.recommendations.extend(recommendations)
        
        return metric
    
    def _check_validity(self, data: Any, data_type: str) -> QualityMetrics:
        """Verifica validade dos dados."""
        score = 100.0
        details = {}
        issues = []
        recommendations = []
        
        if isinstance(data, dict):
            # Verificar campos obrigatórios baseado no tipo
            required_fields = self._get_required_fields(data_type)
            missing_required = []
            
            for field in required_fields:
                if field not in data or data[field] is None:
                    missing_required.append(field)
            
            if missing_required:
                score = max(0, score - (len(missing_required) * 20))
                issues.append(f"Campos obrigatórios ausentes: {missing_required}")
                recommendations.append("Verificar mapeamento de campos da fonte")
            
            details["missing_required_fields"] = missing_required
            
            # Verificar valores válidos
            for key, value in data.items():
                if key in ['price', 'high', 'low', 'open', 'close'] and value is not None:
                    try:
                        num_value = float(value)
                        if num_value < 0:
                            score = min(score, 60.0)
                            issues.append(f"Valor negativo inválido para {key}: {num_value}")
                            recommendations.append(f"Verificar cálculo do campo {key}")
                    except (ValueError, TypeError):
                        score = min(score, 40.0)
                        issues.append(f"Valor não numérico para {key}: {value}")
                        recommendations.append(f"Verificar formato do campo {key}")
                
                elif key == 'volume' and value is not None:
                    try:
                        num_value = float(value)
                        if num_value < 0:
                            score = min(score, 70.0)
                            issues.append(f"Volume negativo: {num_value}")
                    except (ValueError, TypeError):
                        score = min(score, 50.0)
                        issues.append(f"Volume não numérico: {value}")
        
        metric = QualityMetrics.from_score(QualityDimension.VALIDITY, score, details)
        metric.issues.extend(issues)
        metric.recommendations.extend(recommendations)
        
        return metric
    
    def _check_reliability(self, source: str, symbol: str, 
                          historical_data: List[Any] = None) -> QualityMetrics:
        """Verifica confiabilidade da fonte."""
        score = 100.0
        details = {}
        issues = []
        recommendations = []
        
        # Verificar histórico de qualidade da fonte
        source_key = f"{source}:{symbol}"
        
        if source_key in self.source_profiles:
            profile = self.source_profiles[source_key]
            
            # Calcular taxa de sucesso
            total_checks = profile.get('total_checks', 0)
            successful_checks = profile.get('successful_checks', 0)
            
            if total_checks > 0:
                success_rate = (successful_checks / total_checks) * 100
                score = min(score, success_rate)
                
                details["success_rate"] = success_rate
                details["total_checks"] = total_checks
                
                if success_rate < 80:
                    issues.append(f"Taxa de sucesso baixa: {success_rate:.1f}%")
                    recommendations.append("Considerar fonte alternativa")
            
            # Verificar estabilidade temporal
            recent_failures = profile.get('recent_failures', 0)
            if recent_failures > 5:
                score = min(score, 60.0)
                issues.append(f"Falhas recentes: {recent_failures}")
                recommendations.append("Monitorar fonte de perto")
        
        # Verificar consistência dos dados históricos
        if historical_data and len(historical_data) >= 10:
            # Verificar gaps nos dados
            timestamps = []
            for data in historical_data[-20:]:
                ts = self._extract_timestamp(data)
                if ts:
                    timestamps.append(ts)
            
            if len(timestamps) >= 2:
                timestamps.sort()
                gaps = []
                
                for i in range(1, len(timestamps)):
                    gap = (timestamps[i] - timestamps[i-1]).total_seconds() / 60
                    gaps.append(gap)
                
                if gaps:
                    avg_gap = statistics.mean(gaps)
                    max_gap = max(gaps)
                    
                    details["average_gap_minutes"] = avg_gap
                    details["max_gap_minutes"] = max_gap
                    
                    # Penalizar gaps muito grandes
                    if max_gap > 60:  # Gap maior que 1 hora
                        score = min(score, 70.0)
                        issues.append(f"Gap grande nos dados: {max_gap:.1f} min")
                        recommendations.append("Verificar estabilidade da fonte")
        
        metric = QualityMetrics.from_score(QualityDimension.RELIABILITY, score, details)
        metric.issues.extend(issues)
        metric.recommendations.extend(recommendations)
        
        return metric
    
    def _get_required_fields(self, data_type: str) -> List[str]:
        """Obtém campos obrigatórios baseado no tipo de dados."""
        field_map = {
            'price': ['price'],
            'quote': ['price', 'symbol'],
            'ticker': ['symbol', 'price'],
            'ohlcv': ['open', 'high', 'low', 'close', 'volume'],
            'market_data': ['symbol', 'price']
        }
        
        return field_map.get(data_type, ['price'])
    
    def _extract_numeric_value(self, data: Any) -> Optional[float]:
        """Extrai valor numérico dos dados."""
        if isinstance(data, (int, float)):
            return float(data)
        
        if isinstance(data, dict):
            for field in ['price', 'value', 'close', 'last']:
                if field in data and isinstance(data[field], (int, float)):
                    return float(data[field])
        
        return None
    
    def _extract_timestamp(self, data: Any) -> Optional[datetime]:
        """Extrai timestamp dos dados."""
        if isinstance(data, dict):
            for field in ['timestamp', 'time', 'date', 'updated_at']:
                if field in data and data[field] is not None:
                    value = data[field]
                    
                    if isinstance(value, datetime):
                        return value
                    
                    if isinstance(value, str):
                        try:
                            return datetime.fromisoformat(value.replace('Z', '+00:00'))
                        except Exception:
                            continue
        
        return None
    
    def _add_general_recommendations(self, report: QualityReport):
        """Adiciona recomendações gerais baseadas no relatório."""
        if report.overall_score < 50:
            report.add_recommendation("Qualidade crítica: considerar desabilitar fonte temporariamente")
        elif report.overall_score < 70:
            report.add_recommendation("Qualidade baixa: aumentar frequência de monitoramento")
        
        critical_metrics = report.get_critical_issues()
        if critical_metrics:
            report.add_recommendation(f"Resolver problemas críticos em: {[m.dimension.value for m in critical_metrics]}")
        
        if len(report.threshold_violations) > 3:
            report.add_recommendation("Múltiplas violações de limite: revisar configuração da fonte")
    
    def _record_quality_check(self, report: QualityReport):
        """Registra verificação de qualidade no histórico."""
        self.quality_history.append(report)
        
        # Atualizar perfil da fonte
        source_key = f"{report.source}:{report.symbol}"
        profile = self.source_profiles[source_key]
        
        profile['total_checks'] = profile.get('total_checks', 0) + 1
        
        if report.overall_level not in [QualityLevel.POOR, QualityLevel.CRITICAL]:
            profile['successful_checks'] = profile.get('successful_checks', 0) + 1
        else:
            profile['recent_failures'] = profile.get('recent_failures', 0) + 1
        
        profile['last_check'] = report.timestamp
        profile['last_score'] = report.overall_score
    
    async def _handle_quality_callbacks(self, report: QualityReport):
        """Processa callbacks de qualidade."""
        try:
            # Callback para degradação de qualidade
            if (report.overall_level in [QualityLevel.POOR, QualityLevel.FAIR] and 
                self.on_quality_degradation):
                await self.on_quality_degradation(report)
            
            # Callback para qualidade crítica
            if (report.overall_level == QualityLevel.CRITICAL and 
                self.on_critical_quality):
                await self.on_critical_quality(report)
                
        except Exception as e:
            logger.error(f"Erro nos callbacks de qualidade: {e}")
    
    def get_quality_statistics(self) -> Dict[str, Any]:
        """Obtém estatísticas de qualidade."""
        if not self.quality_history:
            return {"total_checks": 0}
        
        # Estatísticas dos últimos 24h
        now = datetime.now(timezone.utc)
        last_24h = now - timedelta(hours=24)
        
        recent_reports = [
            r for r in self.quality_history
            if r.timestamp >= last_24h
        ]
        
        if not recent_reports:
            return {"total_checks": len(self.quality_history), "recent_checks": 0}
        
        # Distribuição por nível
        level_counts = defaultdict(int)
        for report in recent_reports:
            level_counts[report.overall_level.value] += 1
        
        # Score médio por dimensão
        dimension_scores = defaultdict(list)
        for report in recent_reports:
            for dimension, metric in report.metrics.items():
                dimension_scores[dimension.value].append(metric.score)
        
        avg_dimension_scores = {
            dim: statistics.mean(scores)
            for dim, scores in dimension_scores.items()
        }
        
        # Fontes com problemas
        problematic_sources = defaultdict(int)
        for report in recent_reports:
            if report.overall_level in [QualityLevel.POOR, QualityLevel.CRITICAL]:
                problematic_sources[report.source] += 1
        
        return {
            "total_checks": len(self.quality_history),
            "recent_checks_24h": len(recent_reports),
            "level_distribution": dict(level_counts),
            "average_dimension_scores": avg_dimension_scores,
            "problematic_sources": dict(problematic_sources),
            "average_overall_score": statistics.mean([r.overall_score for r in recent_reports]),
            "active_thresholds": len([t for t in self.thresholds.values() if t.enabled])
        }
    
    def get_source_profile(self, source: str, symbol: str = None) -> Dict[str, Any]:
        """Obtém perfil de qualidade de uma fonte."""
        if symbol:
            source_key = f"{source}:{symbol}"
            return self.source_profiles.get(source_key, {})
        
        # Agregar dados de todos os símbolos da fonte
        source_profiles = {
            key: profile for key, profile in self.source_profiles.items()
            if key.startswith(f"{source}:")
        }
        
        if not source_profiles:
            return {}
        
        # Calcular estatísticas agregadas
        total_checks = sum(p.get('total_checks', 0) for p in source_profiles.values())
        successful_checks = sum(p.get('successful_checks', 0) for p in source_profiles.values())
        recent_failures = sum(p.get('recent_failures', 0) for p in source_profiles.values())
        
        last_scores = [p.get('last_score', 0) for p in source_profiles.values() if 'last_score' in p]
        avg_score = statistics.mean(last_scores) if last_scores else 0
        
        return {
            "total_checks": total_checks,
            "successful_checks": successful_checks,
            "recent_failures": recent_failures,
            "success_rate": (successful_checks / total_checks * 100) if total_checks > 0 else 0,
            "average_score": avg_score,
            "symbols_count": len(source_profiles)
        }
    
    async def batch_quality_check(self, requests: List[Dict[str, Any]]) -> List[QualityReport]:
        """Executa verificação de qualidade em lote."""
        results = []
        
        for request in requests:
            try:
                report = await self.check_data_quality(
                    request['source'],
                    request['symbol'],
                    request['data_type'],
                    request['data'],
                    request.get('historical_data')
                )
                results.append(report)
            except Exception as e:
                logger.error(f"Erro na verificação de qualidade para {request.get('source')}: {e}")
                # Criar relatório de erro
                error_report = QualityReport(
                    source=request.get('source', 'unknown'),
                    symbol=request.get('symbol', 'unknown'),
                    data_type=request.get('data_type', 'unknown'),
                    overall_score=0.0,
                    overall_level=QualityLevel.CRITICAL
                )
                results.append(error_report)
        
        return results