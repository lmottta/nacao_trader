from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from datetime import datetime, timezone, timedelta
from enum import Enum
from dataclasses import dataclass, field
import asyncio
import logging
import statistics
import math
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

def _get_utc_now() -> datetime:
    """Função auxiliar para obter timestamp UTC atual."""
    return datetime.now(timezone.utc)

class ValidationStatus(Enum):
    """Status de validação."""
    VALID = "valid"                      # Dados válidos
    INVALID = "invalid"                  # Dados inválidos
    SUSPICIOUS = "suspicious"            # Dados suspeitos
    INSUFFICIENT_DATA = "insufficient_data"  # Dados insuficientes
    CONFLICTING = "conflicting"          # Dados conflitantes
    PENDING = "pending"                  # Validação pendente

class ValidationSeverity(Enum):
    """Severidade de problemas de validação."""
    LOW = "low"                          # Baixa severidade
    MEDIUM = "medium"                    # Média severidade
    HIGH = "high"                        # Alta severidade
    CRITICAL = "critical"                # Severidade crítica

@dataclass
class ValidationIssue:
    """Representa um problema encontrado na validação."""
    type: str                            # Tipo do problema
    severity: ValidationSeverity         # Severidade
    message: str                         # Mensagem descritiva
    source: str                          # Fonte que causou o problema
    data_field: str = None               # Campo específico
    expected_value: Any = None           # Valor esperado
    actual_value: Any = None             # Valor atual
    timestamp: datetime = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)

@dataclass
class ValidationResult:
    """Resultado de uma validação cruzada."""
    symbol: str                          # Símbolo validado
    data_type: str                       # Tipo de dados
    status: ValidationStatus             # Status da validação
    confidence: float                    # Confiança no resultado (0-1)
    consensus_value: Any = None          # Valor de consenso
    source_count: int = 0                # Número de fontes consultadas
    agreement_percentage: float = 0.0    # Percentual de concordância
    issues: List[ValidationIssue] = field(default_factory=list)
    source_data: Dict[str, Any] = field(default_factory=dict)  # Dados por fonte
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
    
    def add_issue(self, issue: ValidationIssue):
        """Adiciona um problema à validação."""
        self.issues.append(issue)
        
        # Ajustar status baseado na severidade
        if issue.severity == ValidationSeverity.CRITICAL:
            self.status = ValidationStatus.INVALID
        elif issue.severity == ValidationSeverity.HIGH and self.status == ValidationStatus.VALID:
            self.status = ValidationStatus.SUSPICIOUS
    
    def get_issues_by_severity(self, severity: ValidationSeverity) -> List[ValidationIssue]:
        """Obtém problemas por severidade."""
        return [issue for issue in self.issues if issue.severity == severity]
    
    def has_critical_issues(self) -> bool:
        """Verifica se há problemas críticos."""
        return any(issue.severity == ValidationSeverity.CRITICAL for issue in self.issues)

class ValidationRule(ABC):
    """Classe base para regras de validação."""
    
    def __init__(self, name: str, enabled: bool = True, weight: float = 1.0):
        self.name = name
        self.enabled = enabled
        self.weight = weight  # Peso da regra no cálculo de confiança
    
    @abstractmethod
    async def validate(self, symbol: str, data_type: str, 
                      source_data: Dict[str, Any]) -> List[ValidationIssue]:
        """Executa a validação e retorna lista de problemas encontrados."""
        pass
    
    def is_applicable(self, symbol: str, data_type: str) -> bool:
        """Verifica se a regra se aplica ao símbolo/tipo de dados."""
        return True

class PriceRangeValidationRule(ValidationRule):
    """Regra que valida se preços estão dentro de faixas aceitáveis."""
    
    def __init__(self, max_deviation_percent: float = 10.0):
        super().__init__("price_range_validation")
        self.max_deviation_percent = max_deviation_percent
    
    async def validate(self, symbol: str, data_type: str, 
                      source_data: Dict[str, Any]) -> List[ValidationIssue]:
        issues = []
        
        if data_type not in ['price', 'quote', 'ticker']:
            return issues
        
        # Extrair preços de todas as fontes
        prices = []
        for source, data in source_data.items():
            price = self._extract_price(data)
            if price is not None:
                prices.append((source, price))
        
        if len(prices) < 2:
            return issues
        
        # Calcular estatísticas
        price_values = [p[1] for p in prices]
        median_price = statistics.median(price_values)
        
        # Verificar desvios
        for source, price in prices:
            deviation_percent = abs(price - median_price) / median_price * 100
            
            if deviation_percent > self.max_deviation_percent:
                severity = ValidationSeverity.HIGH if deviation_percent > 20 else ValidationSeverity.MEDIUM
                
                issues.append(ValidationIssue(
                    type="price_deviation",
                    severity=severity,
                    message=f"Preço da fonte {source} desvia {deviation_percent:.2f}% da mediana",
                    source=source,
                    data_field="price",
                    expected_value=median_price,
                    actual_value=price,
                    metadata={"deviation_percent": deviation_percent}
                ))
        
        return issues
    
    def _extract_price(self, data: Any) -> Optional[float]:
        """Extrai preço dos dados."""
        if isinstance(data, (int, float)):
            return float(data)
        
        if isinstance(data, dict):
            # Tentar diferentes campos comuns
            for field in ['price', 'close', 'last', 'value', 'quote']:
                if field in data and data[field] is not None:
                    try:
                        return float(data[field])
                    except (ValueError, TypeError):
                        continue
        
        return None

class TimestampValidationRule(ValidationRule):
    """Regra que valida timestamps dos dados."""
    
    def __init__(self, max_age_minutes: int = 60):
        super().__init__("timestamp_validation")
        self.max_age_minutes = max_age_minutes
    
    async def validate(self, symbol: str, data_type: str, 
                      source_data: Dict[str, Any]) -> List[ValidationIssue]:
        issues = []
        now = datetime.now(timezone.utc)
        
        for source, data in source_data.items():
            timestamp = self._extract_timestamp(data)
            
            if timestamp is None:
                issues.append(ValidationIssue(
                    type="missing_timestamp",
                    severity=ValidationSeverity.MEDIUM,
                    message=f"Timestamp ausente na fonte {source}",
                    source=source,
                    data_field="timestamp"
                ))
                continue
            
            # Verificar idade dos dados
            age = now - timestamp
            age_minutes = age.total_seconds() / 60
            
            if age_minutes > self.max_age_minutes:
                severity = ValidationSeverity.HIGH if age_minutes > 120 else ValidationSeverity.MEDIUM
                
                issues.append(ValidationIssue(
                    type="stale_data",
                    severity=severity,
                    message=f"Dados da fonte {source} estão desatualizados ({age_minutes:.1f} min)",
                    source=source,
                    data_field="timestamp",
                    actual_value=timestamp,
                    metadata={"age_minutes": age_minutes}
                ))
        
        return issues
    
    def _extract_timestamp(self, data: Any) -> Optional[datetime]:
        """Extrai timestamp dos dados."""
        if isinstance(data, dict):
            for field in ['timestamp', 'time', 'date', 'updated_at', 'last_updated']:
                if field in data and data[field] is not None:
                    value = data[field]
                    
                    if isinstance(value, datetime):
                        return value
                    
                    if isinstance(value, str):
                        try:
                            # Tentar diferentes formatos
                            for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%dT%H:%M:%SZ']:
                                try:
                                    return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
                                except ValueError:
                                    continue
                        except Exception:
                            continue
        
        return None

class ConsistencyValidationRule(ValidationRule):
    """Regra que verifica consistência entre fontes."""
    
    def __init__(self, min_sources: int = 2, agreement_threshold: float = 0.7):
        super().__init__("consistency_validation")
        self.min_sources = min_sources
        self.agreement_threshold = agreement_threshold
    
    async def validate(self, symbol: str, data_type: str, 
                      source_data: Dict[str, Any]) -> List[ValidationIssue]:
        issues = []
        
        if len(source_data) < self.min_sources:
            issues.append(ValidationIssue(
                type="insufficient_sources",
                severity=ValidationSeverity.HIGH,
                message=f"Apenas {len(source_data)} fontes disponíveis, mínimo {self.min_sources}",
                source="validator",
                metadata={"available_sources": len(source_data), "required_sources": self.min_sources}
            ))
            return issues
        
        # Verificar consistência de valores numéricos
        numeric_values = self._extract_numeric_values(source_data)
        if numeric_values:
            agreement = self._calculate_agreement(numeric_values)
            
            if agreement < self.agreement_threshold:
                issues.append(ValidationIssue(
                    type="low_agreement",
                    severity=ValidationSeverity.MEDIUM,
                    message=f"Baixa concordância entre fontes: {agreement:.2%}",
                    source="validator",
                    metadata={"agreement": agreement, "threshold": self.agreement_threshold}
                ))
        
        return issues
    
    def _extract_numeric_values(self, source_data: Dict[str, Any]) -> List[Tuple[str, float]]:
        """Extrai valores numéricos das fontes."""
        values = []
        
        for source, data in source_data.items():
            if isinstance(data, (int, float)):
                values.append((source, float(data)))
            elif isinstance(data, dict):
                for field in ['price', 'value', 'close', 'last']:
                    if field in data and isinstance(data[field], (int, float)):
                        values.append((source, float(data[field])))
                        break
        
        return values
    
    def _calculate_agreement(self, values: List[Tuple[str, float]]) -> float:
        """Calcula percentual de concordância entre valores."""
        if len(values) < 2:
            return 1.0
        
        numeric_values = [v[1] for v in values]
        median_value = statistics.median(numeric_values)
        
        # Contar quantos valores estão dentro de 5% da mediana
        tolerance = 0.05  # 5%
        agreeing_count = 0
        
        for value in numeric_values:
            if median_value == 0:
                if value == 0:
                    agreeing_count += 1
            else:
                deviation = abs(value - median_value) / median_value
                if deviation <= tolerance:
                    agreeing_count += 1
        
        return agreeing_count / len(numeric_values)

class CrossValidator:
    """Validador cruzado principal que coordena validações entre múltiplas fontes."""
    
    def __init__(self):
        self.rules: List[ValidationRule] = []
        self.validation_history: List[ValidationResult] = []
        self.max_history_size = 1000
        
        # Configurações
        self.min_sources_for_validation = 2
        self.default_confidence_threshold = 0.7
        
        # Callbacks
        self.on_validation_completed: Optional[Callable] = None
        self.on_critical_issue_detected: Optional[Callable] = None
        
        # Configurar regras padrão
        self._setup_default_rules()
        
        logger.info("CrossValidator inicializado")
    
    def _setup_default_rules(self):
        """Configura regras padrão de validação."""
        self.add_rule(PriceRangeValidationRule(max_deviation_percent=10.0))
        self.add_rule(TimestampValidationRule(max_age_minutes=60))
        self.add_rule(ConsistencyValidationRule(min_sources=2, agreement_threshold=0.7))
    
    def add_rule(self, rule: ValidationRule):
        """Adiciona uma regra de validação."""
        self.rules.append(rule)
        logger.info(f"Regra de validação '{rule.name}' adicionada")
    
    def remove_rule(self, rule_name: str):
        """Remove uma regra de validação."""
        self.rules = [r for r in self.rules if r.name != rule_name]
        logger.info(f"Regra de validação '{rule_name}' removida")
    
    def enable_rule(self, rule_name: str):
        """Habilita uma regra de validação."""
        for rule in self.rules:
            if rule.name == rule_name:
                rule.enabled = True
                logger.info(f"Regra '{rule_name}' habilitada")
                break
    
    def disable_rule(self, rule_name: str):
        """Desabilita uma regra de validação."""
        for rule in self.rules:
            if rule.name == rule_name:
                rule.enabled = False
                logger.info(f"Regra '{rule_name}' desabilitada")
                break
    
    async def validate_cross_source(self, symbol: str, data_type: str, 
                                   source_data: Dict[str, Any]) -> ValidationResult:
        """Executa validação cruzada entre múltiplas fontes."""
        result = ValidationResult(
            symbol=symbol,
            data_type=data_type,
            status=ValidationStatus.VALID,
            confidence=1.0,
            source_count=len(source_data),
            source_data=source_data.copy()
        )
        
        # Verificar se há dados suficientes
        if len(source_data) < self.min_sources_for_validation:
            result.status = ValidationStatus.INSUFFICIENT_DATA
            result.confidence = 0.0
            result.add_issue(ValidationIssue(
                type="insufficient_data",
                severity=ValidationSeverity.HIGH,
                message=f"Apenas {len(source_data)} fontes disponíveis para validação",
                source="validator"
            ))
            return result
        
        # Executar todas as regras aplicáveis
        all_issues = []
        
        for rule in self.rules:
            if not rule.enabled or not rule.is_applicable(symbol, data_type):
                continue
            
            try:
                issues = await rule.validate(symbol, data_type, source_data)
                all_issues.extend(issues)
            except Exception as e:
                logger.error(f"Erro ao executar regra {rule.name}: {e}")
                all_issues.append(ValidationIssue(
                    type="rule_execution_error",
                    severity=ValidationSeverity.MEDIUM,
                    message=f"Erro ao executar regra {rule.name}: {e}",
                    source="validator"
                ))
        
        # Adicionar problemas ao resultado
        for issue in all_issues:
            result.add_issue(issue)
        
        # Calcular consenso e confiança
        result.consensus_value = self._calculate_consensus(source_data, data_type)
        result.agreement_percentage = self._calculate_agreement_percentage(source_data)
        result.confidence = self._calculate_confidence(result)
        
        # Registrar no histórico
        self._record_validation(result)
        
        # Chamar callbacks
        if self.on_validation_completed:
            try:
                await self.on_validation_completed(result)
            except Exception as e:
                logger.error(f"Erro no callback de validação: {e}")
        
        if result.has_critical_issues() and self.on_critical_issue_detected:
            try:
                await self.on_critical_issue_detected(result)
            except Exception as e:
                logger.error(f"Erro no callback de problema crítico: {e}")
        
        logger.debug(f"Validação concluída para {symbol} ({data_type}): {result.status.value}")
        return result
    
    def _calculate_consensus(self, source_data: Dict[str, Any], data_type: str) -> Any:
        """Calcula valor de consenso entre as fontes."""
        # Extrair valores numéricos
        numeric_values = []
        for source, data in source_data.items():
            value = self._extract_numeric_value(data)
            if value is not None:
                numeric_values.append(value)
        
        if numeric_values:
            # Usar mediana como consenso (mais robusta a outliers)
            return statistics.median(numeric_values)
        
        # Para dados não numéricos, usar valor mais comum
        string_values = []
        for source, data in source_data.items():
            if isinstance(data, str):
                string_values.append(data)
            elif isinstance(data, dict) and 'value' in data:
                string_values.append(str(data['value']))
        
        if string_values:
            # Retornar valor mais frequente
            return max(set(string_values), key=string_values.count)
        
        return None
    
    def _extract_numeric_value(self, data: Any) -> Optional[float]:
        """Extrai valor numérico dos dados."""
        if isinstance(data, (int, float)):
            return float(data)
        
        if isinstance(data, dict):
            for field in ['price', 'value', 'close', 'last', 'quote']:
                if field in data and isinstance(data[field], (int, float)):
                    return float(data[field])
        
        return None
    
    def _calculate_agreement_percentage(self, source_data: Dict[str, Any]) -> float:
        """Calcula percentual de concordância entre fontes."""
        if len(source_data) < 2:
            return 100.0
        
        # Extrair valores numéricos
        numeric_values = []
        for source, data in source_data.items():
            value = self._extract_numeric_value(data)
            if value is not None:
                numeric_values.append(value)
        
        if len(numeric_values) < 2:
            return 100.0
        
        # Calcular concordância baseada na mediana
        median_value = statistics.median(numeric_values)
        tolerance = 0.05  # 5%
        agreeing_count = 0
        
        for value in numeric_values:
            if median_value == 0:
                if value == 0:
                    agreeing_count += 1
            else:
                deviation = abs(value - median_value) / median_value
                if deviation <= tolerance:
                    agreeing_count += 1
        
        return (agreeing_count / len(numeric_values)) * 100.0
    
    def _calculate_confidence(self, result: ValidationResult) -> float:
        """Calcula confiança no resultado da validação."""
        base_confidence = 1.0
        
        # Reduzir confiança baseado nos problemas
        for issue in result.issues:
            if issue.severity == ValidationSeverity.CRITICAL:
                base_confidence -= 0.5
            elif issue.severity == ValidationSeverity.HIGH:
                base_confidence -= 0.3
            elif issue.severity == ValidationSeverity.MEDIUM:
                base_confidence -= 0.1
            elif issue.severity == ValidationSeverity.LOW:
                base_confidence -= 0.05
        
        # Ajustar baseado no número de fontes
        source_factor = min(1.0, result.source_count / 3.0)  # Ideal: 3+ fontes
        
        # Ajustar baseado na concordância
        agreement_factor = result.agreement_percentage / 100.0
        
        # Calcular confiança final
        confidence = base_confidence * source_factor * agreement_factor
        
        return max(0.0, min(1.0, confidence))
    
    def _record_validation(self, result: ValidationResult):
        """Registra resultado de validação no histórico."""
        self.validation_history.append(result)
        
        # Limitar tamanho do histórico
        if len(self.validation_history) > self.max_history_size:
            self.validation_history = self.validation_history[-self.max_history_size:]
    
    def get_validation_statistics(self) -> Dict[str, Any]:
        """Obtém estatísticas de validação."""
        if not self.validation_history:
            return {"total_validations": 0}
        
        # Estatísticas dos últimos 24h
        now = datetime.now(timezone.utc)
        last_24h = now - timedelta(hours=24)
        
        recent_validations = [
            v for v in self.validation_history
            if v.timestamp >= last_24h
        ]
        
        if not recent_validations:
            return {"total_validations": len(self.validation_history), "recent_validations": 0}
        
        # Contar por status
        status_counts = {}
        for validation in recent_validations:
            status = validation.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Calcular confiança média
        avg_confidence = statistics.mean([v.confidence for v in recent_validations])
        
        # Contar problemas por severidade
        issue_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        for validation in recent_validations:
            for issue in validation.issues:
                issue_counts[issue.severity.value] += 1
        
        return {
            "total_validations": len(self.validation_history),
            "recent_validations_24h": len(recent_validations),
            "status_distribution": status_counts,
            "average_confidence": avg_confidence,
            "issue_counts": issue_counts,
            "active_rules": len([r for r in self.rules if r.enabled]),
            "total_rules": len(self.rules)
        }
    
    def get_validation_history(self, symbol: str = None, limit: int = 100) -> List[ValidationResult]:
        """Obtém histórico de validações."""
        history = self.validation_history
        
        if symbol:
            history = [v for v in history if v.symbol == symbol]
        
        return history[-limit:] if limit else history
    
    async def batch_validate(self, requests: List[Dict[str, Any]]) -> List[ValidationResult]:
        """Executa validação em lote para múltiplas requisições."""
        results = []
        
        for request in requests:
            try:
                result = await self.validate_cross_source(
                    request['symbol'],
                    request['data_type'],
                    request['source_data']
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Erro na validação em lote para {request.get('symbol')}: {e}")
                # Criar resultado de erro
                error_result = ValidationResult(
                    symbol=request.get('symbol', 'unknown'),
                    data_type=request.get('data_type', 'unknown'),
                    status=ValidationStatus.INVALID,
                    confidence=0.0
                )
                error_result.add_issue(ValidationIssue(
                    type="validation_error",
                    severity=ValidationSeverity.CRITICAL,
                    message=f"Erro durante validação: {e}",
                    source="validator"
                ))
                results.append(error_result)
        
        return results