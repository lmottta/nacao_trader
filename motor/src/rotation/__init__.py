"""Sistema de rotação automática entre fontes de dados."""

from .source_rotator import SourceRotator, SourceInfo, RotationStrategy
from .failover_manager import FailoverManager, FailoverRule
from .load_balancer import LoadBalancer, LoadBalancingStrategy

__all__ = [
    'SourceRotator',
    'SourceInfo', 
    'RotationStrategy',
    'FailoverManager',
    'FailoverRule',
    'LoadBalancer',
    'LoadBalancingStrategy'
]