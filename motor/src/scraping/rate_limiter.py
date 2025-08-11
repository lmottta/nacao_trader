import asyncio
import time
from typing import Dict, Optional, List
from dataclasses import dataclass, field
from collections import deque
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

@dataclass
class RateLimitConfig:
    """Configuração de rate limiting para um domínio."""
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    burst_limit: int = 10
    delay_between_requests: float = 1.0
    backoff_multiplier: float = 1.5
    max_backoff: float = 300.0  # 5 minutos
    respect_retry_after: bool = True

@dataclass
class RequestRecord:
    """Registro de uma requisição."""
    timestamp: float
    success: bool
    response_time: float = 0.0
    status_code: Optional[int] = None
    retry_after: Optional[int] = None

@dataclass
class DomainState:
    """Estado de rate limiting para um domínio."""
    config: RateLimitConfig
    requests_minute: deque = field(default_factory=deque)
    requests_hour: deque = field(default_factory=deque)
    last_request_time: float = 0.0
    consecutive_failures: int = 0
    current_backoff: float = 0.0
    blocked_until: float = 0.0
    total_requests: int = 0
    successful_requests: int = 0
    
    def __post_init__(self):
        if not isinstance(self.requests_minute, deque):
            self.requests_minute = deque()
        if not isinstance(self.requests_hour, deque):
            self.requests_hour = deque()

class IntelligentRateLimiter:
    """Rate limiter inteligente com configuração por domínio e backoff adaptativo."""
    
    def __init__(self):
        self.domains: Dict[str, DomainState] = {}
        self.global_semaphore = asyncio.Semaphore(100)  # Limite global
        self.default_configs = self._load_default_configs()
    
    def _load_default_configs(self) -> Dict[str, RateLimitConfig]:
        """Carrega configurações padrão para domínios conhecidos."""
        return {
            "finance.yahoo.com": RateLimitConfig(
                requests_per_minute=30,
                requests_per_hour=500,
                burst_limit=5,
                delay_between_requests=2.0,
                backoff_multiplier=2.0
            ),
            "www.google.com": RateLimitConfig(
                requests_per_minute=20,
                requests_per_hour=300,
                burst_limit=3,
                delay_between_requests=3.0,
                backoff_multiplier=2.5
            ),
            "www.marketwatch.com": RateLimitConfig(
                requests_per_minute=25,
                requests_per_hour=400,
                burst_limit=4,
                delay_between_requests=2.5,
                backoff_multiplier=2.0
            ),
            "investing.com": RateLimitConfig(
                requests_per_minute=20,
                requests_per_hour=350,
                burst_limit=3,
                delay_between_requests=3.0,
                backoff_multiplier=2.0
            ),
            "www.bloomberg.com": RateLimitConfig(
                requests_per_minute=15,
                requests_per_hour=200,
                burst_limit=2,
                delay_between_requests=4.0,
                backoff_multiplier=3.0
            ),
            "default": RateLimitConfig(
                requests_per_minute=40,
                requests_per_hour=600,
                burst_limit=6,
                delay_between_requests=1.5,
                backoff_multiplier=1.8
            )
        }
    
    def _get_domain_from_url(self, url: str) -> str:
        """Extrai o domínio de uma URL."""
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except Exception:
            return "unknown"
    
    def _get_domain_state(self, domain: str) -> DomainState:
        """Obtém ou cria o estado de um domínio."""
        if domain not in self.domains:
            config = self.default_configs.get(domain, self.default_configs["default"])
            self.domains[domain] = DomainState(config=config)
        return self.domains[domain]
    
    def _cleanup_old_requests(self, domain_state: DomainState):
        """Remove registros antigos de requisições."""
        current_time = time.time()
        
        # Limpar requisições de mais de 1 minuto
        while (domain_state.requests_minute and 
               current_time - domain_state.requests_minute[0].timestamp > 60):
            domain_state.requests_minute.popleft()
        
        # Limpar requisições de mais de 1 hora
        while (domain_state.requests_hour and 
               current_time - domain_state.requests_hour[0].timestamp > 3600):
            domain_state.requests_hour.popleft()
    
    def _calculate_delay(self, domain_state: DomainState) -> float:
        """Calcula o delay necessário antes da próxima requisição."""
        current_time = time.time()
        
        # Verificar se está em backoff
        if current_time < domain_state.blocked_until:
            return domain_state.blocked_until - current_time
        
        # Delay mínimo entre requisições
        time_since_last = current_time - domain_state.last_request_time
        min_delay = domain_state.config.delay_between_requests
        
        if time_since_last < min_delay:
            return min_delay - time_since_last
        
        # Verificar limites de rate
        self._cleanup_old_requests(domain_state)
        
        # Verificar limite por minuto
        if len(domain_state.requests_minute) >= domain_state.config.requests_per_minute:
            oldest_request = domain_state.requests_minute[0]
            time_to_wait = 60 - (current_time - oldest_request.timestamp)
            if time_to_wait > 0:
                return time_to_wait
        
        # Verificar limite por hora
        if len(domain_state.requests_hour) >= domain_state.config.requests_per_hour:
            oldest_request = domain_state.requests_hour[0]
            time_to_wait = 3600 - (current_time - oldest_request.timestamp)
            if time_to_wait > 0:
                return time_to_wait
        
        # Verificar burst limit
        recent_requests = [
            req for req in domain_state.requests_minute
            if current_time - req.timestamp < 10  # Últimos 10 segundos
        ]
        
        if len(recent_requests) >= domain_state.config.burst_limit:
            return domain_state.config.delay_between_requests * 2
        
        return 0.0
    
    async def acquire(self, url: str) -> None:
        """Adquire permissão para fazer uma requisição."""
        domain = self._get_domain_from_url(url)
        domain_state = self._get_domain_state(domain)
        
        # Usar semáforo global
        await self.global_semaphore.acquire()
        
        try:
            # Calcular delay necessário
            delay = self._calculate_delay(domain_state)
            
            if delay > 0:
                logger.debug(f"Rate limit para {domain}: aguardando {delay:.2f}s")
                await asyncio.sleep(delay)
            
            # Registrar o momento da requisição
            domain_state.last_request_time = time.time()
            
        except Exception as e:
            self.global_semaphore.release()
            raise e
    
    def release(self, url: str, success: bool, response_time: float = 0.0, 
               status_code: Optional[int] = None, retry_after: Optional[int] = None):
        """Libera o rate limiter e registra o resultado da requisição."""
        try:
            domain = self._get_domain_from_url(url)
            domain_state = self._get_domain_state(domain)
            
            current_time = time.time()
            
            # Criar registro da requisição
            request_record = RequestRecord(
                timestamp=current_time,
                success=success,
                response_time=response_time,
                status_code=status_code,
                retry_after=retry_after
            )
            
            # Adicionar aos registros
            domain_state.requests_minute.append(request_record)
            domain_state.requests_hour.append(request_record)
            domain_state.total_requests += 1
            
            if success:
                domain_state.successful_requests += 1
                domain_state.consecutive_failures = 0
                domain_state.current_backoff = 0.0
            else:
                domain_state.consecutive_failures += 1
                self._apply_backoff(domain_state, retry_after)
            
            # Limpar registros antigos
            self._cleanup_old_requests(domain_state)
            
        finally:
            self.global_semaphore.release()
    
    def _apply_backoff(self, domain_state: DomainState, retry_after: Optional[int] = None):
        """Aplica backoff exponencial em caso de falhas."""
        if retry_after and domain_state.config.respect_retry_after:
            # Respeitar header Retry-After
            domain_state.blocked_until = time.time() + retry_after
            logger.info(f"Respeitando Retry-After: {retry_after}s")
            return
        
        # Backoff exponencial baseado em falhas consecutivas
        if domain_state.consecutive_failures >= 3:
            if domain_state.current_backoff == 0:
                domain_state.current_backoff = domain_state.config.delay_between_requests
            else:
                domain_state.current_backoff *= domain_state.config.backoff_multiplier
            
            # Limitar backoff máximo
            domain_state.current_backoff = min(
                domain_state.current_backoff, 
                domain_state.config.max_backoff
            )
            
            domain_state.blocked_until = time.time() + domain_state.current_backoff
            
            logger.warning(
                f"Backoff aplicado: {domain_state.current_backoff:.2f}s "
                f"após {domain_state.consecutive_failures} falhas consecutivas"
            )
    
    def get_domain_stats(self, domain: str) -> Dict:
        """Retorna estatísticas de um domínio específico."""
        if domain not in self.domains:
            return {}
        
        domain_state = self.domains[domain]
        self._cleanup_old_requests(domain_state)
        
        current_time = time.time()
        success_rate = 0.0
        if domain_state.total_requests > 0:
            success_rate = domain_state.successful_requests / domain_state.total_requests
        
        return {
            "domain": domain,
            "total_requests": domain_state.total_requests,
            "successful_requests": domain_state.successful_requests,
            "success_rate": success_rate,
            "requests_last_minute": len(domain_state.requests_minute),
            "requests_last_hour": len(domain_state.requests_hour),
            "consecutive_failures": domain_state.consecutive_failures,
            "current_backoff": domain_state.current_backoff,
            "blocked_until": domain_state.blocked_until,
            "is_blocked": current_time < domain_state.blocked_until,
            "config": {
                "requests_per_minute": domain_state.config.requests_per_minute,
                "requests_per_hour": domain_state.config.requests_per_hour,
                "delay_between_requests": domain_state.config.delay_between_requests
            }
        }
    
    def get_all_stats(self) -> Dict:
        """Retorna estatísticas de todos os domínios."""
        stats = {
            "total_domains": len(self.domains),
            "domains": {}
        }
        
        for domain in self.domains.keys():
            stats["domains"][domain] = self.get_domain_stats(domain)
        
        return stats
    
    def update_domain_config(self, domain: str, config: RateLimitConfig):
        """Atualiza a configuração de um domínio."""
        domain_state = self._get_domain_state(domain)
        domain_state.config = config
        logger.info(f"Configuração atualizada para domínio {domain}")
    
    def reset_domain(self, domain: str):
        """Reseta o estado de um domínio."""
        if domain in self.domains:
            del self.domains[domain]
            logger.info(f"Estado do domínio {domain} resetado")
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Cleanup se necessário
        pass