from typing import Dict, List, Optional, Any, Callable, Union
from datetime import datetime, timezone, timedelta
from enum import Enum
from dataclasses import dataclass, field
import asyncio
import logging
from abc import ABC, abstractmethod

from .source_rotator import SourceInfo, SourceStatus, SourceRotator

logger = logging.getLogger(__name__)

class FailoverTrigger(Enum):
    """Tipos de gatilhos para failover."""
    CONSECUTIVE_FAILURES = "consecutive_failures"    # Falhas consecutivas
    ERROR_RATE = "error_rate"                        # Taxa de erro alta
    RESPONSE_TIME = "response_time"                  # Tempo de resposta alto
    AVAILABILITY = "availability"                    # Baixa disponibilidade
    MANUAL = "manual"                                # Failover manual
    CIRCUIT_BREAKER = "circuit_breaker"              # Circuit breaker ativado
    HEALTH_CHECK = "health_check"                    # Falha no health check

class FailoverAction(Enum):
    """Ações de failover."""
    SWITCH_SOURCE = "switch_source"                  # Trocar para outra fonte
    MARK_DEGRADED = "mark_degraded"                  # Marcar como degradada
    MARK_FAILED = "mark_failed"                      # Marcar como falha
    DISABLE_SOURCE = "disable_source"                # Desabilitar fonte
    REDUCE_WEIGHT = "reduce_weight"                  # Reduzir peso da fonte
    INCREASE_TIMEOUT = "increase_timeout"            # Aumentar timeout
    TRIGGER_ALERT = "trigger_alert"                  # Disparar alerta

@dataclass
class FailoverRule:
    """Regra de failover."""
    name: str                                        # Nome da regra
    trigger: FailoverTrigger                         # Gatilho
    threshold: Union[int, float]                     # Limite para ativar
    time_window: timedelta                           # Janela de tempo para avaliação
    action: FailoverAction                           # Ação a ser tomada
    target_sources: List[str] = field(default_factory=list)  # Fontes alvo (vazio = todas)
    enabled: bool = True                             # Se a regra está ativa
    cooldown: timedelta = timedelta(minutes=5)       # Tempo entre ativações
    last_triggered: Optional[datetime] = None        # Última vez que foi ativada
    priority: int = 1                                # Prioridade da regra (1=alta)
    conditions: Dict[str, Any] = field(default_factory=dict)  # Condições adicionais
    
    def can_trigger(self) -> bool:
        """Verifica se a regra pode ser ativada (cooldown)."""
        if not self.enabled:
            return False
        
        if self.last_triggered is None:
            return True
        
        return datetime.now(timezone.utc) - self.last_triggered >= self.cooldown
    
    def should_apply_to_source(self, source_name: str) -> bool:
        """Verifica se a regra se aplica a uma fonte específica."""
        if not self.target_sources:
            return True  # Aplica a todas as fontes
        
        return source_name in self.target_sources

class FailoverManager:
    """Gerenciador de failover automático."""
    
    def __init__(self, source_rotator: SourceRotator):
        self.source_rotator = source_rotator
        self.rules: List[FailoverRule] = []
        self.failover_history: List[Dict] = []
        self.max_history_size = 500
        self.monitoring_enabled = True
        self.check_interval = timedelta(seconds=30)  # Intervalo de verificação
        self.last_check = datetime.now(timezone.utc)
        
        # Callbacks para eventos
        self.on_failover_triggered: Optional[Callable] = None
        self.on_source_recovered: Optional[Callable] = None
        
        # Configurar regras padrão
        self._setup_default_rules()
        
        logger.info("FailoverManager inicializado")
    
    def _setup_default_rules(self):
        """Configura regras padrão de failover."""
        # Regra para falhas consecutivas
        self.add_rule(FailoverRule(
            name="consecutive_failures",
            trigger=FailoverTrigger.CONSECUTIVE_FAILURES,
            threshold=5,
            time_window=timedelta(minutes=10),
            action=FailoverAction.MARK_FAILED,
            priority=1
        ))
        
        # Regra para taxa de erro alta
        self.add_rule(FailoverRule(
            name="high_error_rate",
            trigger=FailoverTrigger.ERROR_RATE,
            threshold=0.5,  # 50% de erro
            time_window=timedelta(minutes=5),
            action=FailoverAction.MARK_DEGRADED,
            priority=2
        ))
        
        # Regra para tempo de resposta alto
        self.add_rule(FailoverRule(
            name="high_response_time",
            trigger=FailoverTrigger.RESPONSE_TIME,
            threshold=10000,  # 10 segundos
            time_window=timedelta(minutes=3),
            action=FailoverAction.REDUCE_WEIGHT,
            priority=3
        ))
        
        # Regra para baixa disponibilidade
        self.add_rule(FailoverRule(
            name="low_availability",
            trigger=FailoverTrigger.AVAILABILITY,
            threshold=0.8,  # 80% de uptime
            time_window=timedelta(hours=1),
            action=FailoverAction.MARK_DEGRADED,
            priority=2
        ))
    
    def add_rule(self, rule: FailoverRule):
        """Adiciona uma regra de failover."""
        self.rules.append(rule)
        # Ordenar por prioridade
        self.rules.sort(key=lambda r: r.priority)
        
        logger.info(f"Regra de failover '{rule.name}' adicionada")
    
    def remove_rule(self, rule_name: str):
        """Remove uma regra de failover."""
        self.rules = [r for r in self.rules if r.name != rule_name]
        logger.info(f"Regra de failover '{rule_name}' removida")
    
    def enable_rule(self, rule_name: str):
        """Habilita uma regra de failover."""
        for rule in self.rules:
            if rule.name == rule_name:
                rule.enabled = True
                logger.info(f"Regra '{rule_name}' habilitada")
                break
    
    def disable_rule(self, rule_name: str):
        """Desabilita uma regra de failover."""
        for rule in self.rules:
            if rule.name == rule_name:
                rule.enabled = False
                logger.info(f"Regra '{rule_name}' desabilitada")
                break
    
    async def check_failover_conditions(self):
        """Verifica condições de failover para todas as fontes."""
        if not self.monitoring_enabled:
            return
        
        now = datetime.now(timezone.utc)
        
        # Verificar se é hora de fazer a verificação
        if now - self.last_check < self.check_interval:
            return
        
        self.last_check = now
        
        # Verificar cada fonte
        for source_name, source in self.source_rotator.sources.items():
            await self._check_source_failover(source_name, source)
    
    async def _check_source_failover(self, source_name: str, source: SourceInfo):
        """Verifica condições de failover para uma fonte específica."""
        for rule in self.rules:
            if not rule.can_trigger():
                continue
            
            if not rule.should_apply_to_source(source_name):
                continue
            
            should_trigger = await self._evaluate_rule(rule, source_name, source)
            
            if should_trigger:
                await self._execute_failover_action(rule, source_name, source)
                rule.last_triggered = datetime.now(timezone.utc)
    
    async def _evaluate_rule(self, rule: FailoverRule, source_name: str, source: SourceInfo) -> bool:
        """Avalia se uma regra deve ser ativada."""
        try:
            if rule.trigger == FailoverTrigger.CONSECUTIVE_FAILURES:
                return source.metrics.consecutive_failures >= rule.threshold
            
            elif rule.trigger == FailoverTrigger.ERROR_RATE:
                if source.metrics.total_requests == 0:
                    return False
                error_rate = source.metrics.error_count / source.metrics.total_requests
                return error_rate >= rule.threshold
            
            elif rule.trigger == FailoverTrigger.RESPONSE_TIME:
                return source.metrics.avg_response_time >= rule.threshold
            
            elif rule.trigger == FailoverTrigger.AVAILABILITY:
                return source.metrics.uptime_percentage / 100.0 < rule.threshold
            
            elif rule.trigger == FailoverTrigger.CIRCUIT_BREAKER:
                return source.metrics.consecutive_failures >= source.circuit_breaker_threshold
            
            elif rule.trigger == FailoverTrigger.HEALTH_CHECK:
                # Executar health check se o coletor suportar
                if hasattr(source.collector, 'test_connection'):
                    try:
                        is_healthy = await source.collector.test_connection()
                        return not is_healthy
                    except Exception:
                        return True  # Falha no health check
                return False
            
            return False
        
        except Exception as e:
            logger.error(f"Erro ao avaliar regra {rule.name} para fonte {source_name}: {e}")
            return False
    
    async def _execute_failover_action(self, rule: FailoverRule, source_name: str, source: SourceInfo):
        """Executa a ação de failover."""
        try:
            logger.warning(f"Executando failover: regra '{rule.name}' para fonte '{source_name}' - ação '{rule.action.value}'")
            
            if rule.action == FailoverAction.SWITCH_SOURCE:
                # Marcar fonte atual como degradada e forçar seleção de outra
                source.status = SourceStatus.DEGRADED
            
            elif rule.action == FailoverAction.MARK_DEGRADED:
                source.status = SourceStatus.DEGRADED
            
            elif rule.action == FailoverAction.MARK_FAILED:
                source.status = SourceStatus.FAILED
            
            elif rule.action == FailoverAction.DISABLE_SOURCE:
                source.status = SourceStatus.DISABLED
            
            elif rule.action == FailoverAction.REDUCE_WEIGHT:
                source.weight = max(0.1, source.weight * 0.5)  # Reduzir peso pela metade
            
            elif rule.action == FailoverAction.INCREASE_TIMEOUT:
                source.timeout = min(120.0, source.timeout * 1.5)  # Aumentar timeout
            
            elif rule.action == FailoverAction.TRIGGER_ALERT:
                await self._trigger_alert(rule, source_name, source)
            
            # Registrar no histórico
            self._record_failover(rule, source_name, source)
            
            # Chamar callback se configurado
            if self.on_failover_triggered:
                try:
                    await self.on_failover_triggered(rule, source_name, source)
                except Exception as e:
                    logger.error(f"Erro no callback de failover: {e}")
        
        except Exception as e:
            logger.error(f"Erro ao executar ação de failover {rule.action.value}: {e}")
    
    async def _trigger_alert(self, rule: FailoverRule, source_name: str, source: SourceInfo):
        """Dispara um alerta de failover."""
        alert_data = {
            'timestamp': datetime.now(timezone.utc),
            'rule': rule.name,
            'source': source_name,
            'trigger': rule.trigger.value,
            'threshold': rule.threshold,
            'current_metrics': {
                'success_rate': source.metrics.success_rate,
                'avg_response_time': source.metrics.avg_response_time,
                'consecutive_failures': source.metrics.consecutive_failures,
                'uptime_percentage': source.metrics.uptime_percentage
            }
        }
        
        logger.critical(f"ALERTA DE FAILOVER: {alert_data}")
        
        # Aqui você pode integrar com sistemas de alertas externos
        # como Slack, email, PagerDuty, etc.
    
    def _record_failover(self, rule: FailoverRule, source_name: str, source: SourceInfo):
        """Registra um evento de failover no histórico."""
        record = {
            'timestamp': datetime.now(timezone.utc),
            'rule_name': rule.name,
            'trigger': rule.trigger.value,
            'action': rule.action.value,
            'source_name': source_name,
            'threshold': rule.threshold,
            'metrics_snapshot': {
                'success_rate': source.metrics.success_rate,
                'avg_response_time': source.metrics.avg_response_time,
                'error_count': source.metrics.error_count,
                'consecutive_failures': source.metrics.consecutive_failures,
                'uptime_percentage': source.metrics.uptime_percentage
            }
        }
        
        self.failover_history.append(record)
        
        # Limitar tamanho do histórico
        if len(self.failover_history) > self.max_history_size:
            self.failover_history = self.failover_history[-self.max_history_size:]
    
    async def manual_failover(self, source_name: str, action: FailoverAction, reason: str = ""):
        """Executa um failover manual."""
        if source_name not in self.source_rotator.sources:
            raise ValueError(f"Fonte {source_name} não encontrada")
        
        source = self.source_rotator.sources[source_name]
        
        # Criar regra temporária para o failover manual
        manual_rule = FailoverRule(
            name=f"manual_{datetime.now(timezone.utc).isoformat()}",
            trigger=FailoverTrigger.MANUAL,
            threshold=0,
            time_window=timedelta(seconds=1),
            action=action
        )
        
        await self._execute_failover_action(manual_rule, source_name, source)
        
        logger.info(f"Failover manual executado para {source_name}: {action.value} - {reason}")
    
    async def recover_source(self, source_name: str):
        """Tenta recuperar uma fonte que falhou."""
        if source_name not in self.source_rotator.sources:
            raise ValueError(f"Fonte {source_name} não encontrada")
        
        source = self.source_rotator.sources[source_name]
        
        # Tentar health check
        if hasattr(source.collector, 'test_connection'):
            try:
                is_healthy = await source.collector.test_connection()
                
                if is_healthy:
                    # Resetar métricas e status
                    source.metrics.consecutive_failures = 0
                    source.status = SourceStatus.ACTIVE
                    source.weight = min(1.0, source.weight * 2.0)  # Restaurar peso gradualmente
                    
                    logger.info(f"Fonte {source_name} recuperada com sucesso")
                    
                    # Chamar callback se configurado
                    if self.on_source_recovered:
                        try:
                            await self.on_source_recovered(source_name, source)
                        except Exception as e:
                            logger.error(f"Erro no callback de recuperação: {e}")
                    
                    return True
                else:
                    logger.warning(f"Fonte {source_name} ainda não está saudável")
                    return False
            
            except Exception as e:
                logger.error(f"Erro ao testar recuperação da fonte {source_name}: {e}")
                return False
        
        return False
    
    async def auto_recovery_check(self):
        """Verifica automaticamente se fontes falhadas podem ser recuperadas."""
        failed_sources = [
            name for name, source in self.source_rotator.sources.items()
            if source.status in [SourceStatus.FAILED, SourceStatus.DEGRADED]
        ]
        
        for source_name in failed_sources:
            try:
                await self.recover_source(source_name)
                await asyncio.sleep(1)  # Pequena pausa entre tentativas
            except Exception as e:
                logger.debug(f"Falha na tentativa de recuperação de {source_name}: {e}")
    
    def get_failover_statistics(self) -> Dict[str, Any]:
        """Obtém estatísticas de failover."""
        now = datetime.now(timezone.utc)
        last_24h = now - timedelta(hours=24)
        
        recent_failovers = [
            f for f in self.failover_history
            if f['timestamp'] >= last_24h
        ]
        
        # Contar por tipo de trigger
        trigger_counts = {}
        for failover in recent_failovers:
            trigger = failover['trigger']
            trigger_counts[trigger] = trigger_counts.get(trigger, 0) + 1
        
        # Contar por fonte
        source_counts = {}
        for failover in recent_failovers:
            source = failover['source_name']
            source_counts[source] = source_counts.get(source, 0) + 1
        
        return {
            'total_failovers_24h': len(recent_failovers),
            'failovers_by_trigger': trigger_counts,
            'failovers_by_source': source_counts,
            'active_rules': len([r for r in self.rules if r.enabled]),
            'total_rules': len(self.rules),
            'monitoring_enabled': self.monitoring_enabled,
            'last_check': self.last_check
        }
    
    def get_failover_history(self, source_name: str = None, limit: int = 100) -> List[Dict]:
        """Obtém histórico de failovers."""
        history = self.failover_history
        
        if source_name:
            history = [f for f in history if f['source_name'] == source_name]
        
        return history[-limit:] if limit else history
    
    def enable_monitoring(self):
        """Habilita o monitoramento de failover."""
        self.monitoring_enabled = True
        logger.info("Monitoramento de failover habilitado")
    
    def disable_monitoring(self):
        """Desabilita o monitoramento de failover."""
        self.monitoring_enabled = False
        logger.info("Monitoramento de failover desabilitado")
    
    def set_check_interval(self, interval: timedelta):
        """Define o intervalo de verificação de failover."""
        self.check_interval = interval
        logger.info(f"Intervalo de verificação de failover definido para {interval}")