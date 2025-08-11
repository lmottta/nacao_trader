import asyncio
import random
import time
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import aiohttp
import logging
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class ProxyStatus(Enum):
    ACTIVE = "active"
    FAILED = "failed"
    BANNED = "banned"
    TESTING = "testing"

@dataclass
class ProxyInfo:
    """Informações de um proxy."""
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    protocol: str = "http"
    status: ProxyStatus = ProxyStatus.ACTIVE
    success_count: int = 0
    failure_count: int = 0
    last_used: Optional[float] = None
    last_failure: Optional[float] = None
    response_time: float = 0.0
    banned_domains: List[str] = None
    
    def __post_init__(self):
        if self.banned_domains is None:
            self.banned_domains = []
    
    @property
    def url(self) -> str:
        """Retorna a URL completa do proxy."""
        if self.username and self.password:
            return f"{self.protocol}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol}://{self.host}:{self.port}"
    
    @property
    def success_rate(self) -> float:
        """Calcula a taxa de sucesso do proxy."""
        total = self.success_count + self.failure_count
        if total == 0:
            return 1.0
        return self.success_count / total
    
    def is_banned_for_domain(self, domain: str) -> bool:
        """Verifica se o proxy está banido para um domínio específico."""
        return domain in self.banned_domains
    
    def ban_for_domain(self, domain: str):
        """Bane o proxy para um domínio específico."""
        if domain not in self.banned_domains:
            self.banned_domains.append(domain)
            logger.warning(f"Proxy {self.host}:{self.port} banido para domínio {domain}")

class ProxyRotator:
    """Sistema de rotação de proxies com health check e balanceamento."""
    
    def __init__(self, test_url: str = "http://httpbin.org/ip", test_timeout: int = 10):
        self.proxies: List[ProxyInfo] = []
        self.test_url = test_url
        self.test_timeout = test_timeout
        self.current_index = 0
        self.health_check_interval = 300  # 5 minutos
        self.last_health_check = 0
        self.min_success_rate = 0.7
        self.max_failures_before_ban = 5
        
    def add_proxy(self, host: str, port: int, username: str = None, 
                  password: str = None, protocol: str = "http"):
        """Adiciona um proxy à lista."""
        proxy = ProxyInfo(
            host=host,
            port=port,
            username=username,
            password=password,
            protocol=protocol
        )
        self.proxies.append(proxy)
        logger.info(f"Proxy adicionado: {proxy.url}")
    
    def add_proxy_list(self, proxy_list: List[Dict]):
        """Adiciona uma lista de proxies."""
        for proxy_data in proxy_list:
            self.add_proxy(**proxy_data)
    
    async def get_proxy(self, domain: str = None) -> Optional[ProxyInfo]:
        """Obtém o melhor proxy disponível para um domínio."""
        if not self.proxies:
            return None
        
        # Executar health check se necessário
        if time.time() - self.last_health_check > self.health_check_interval:
            await self.health_check()
        
        # Filtrar proxies ativos e não banidos para o domínio
        available_proxies = [
            p for p in self.proxies 
            if p.status == ProxyStatus.ACTIVE and 
            (not domain or not p.is_banned_for_domain(domain))
        ]
        
        if not available_proxies:
            logger.warning(f"Nenhum proxy disponível para domínio {domain}")
            return None
        
        # Ordenar por taxa de sucesso e tempo de resposta
        available_proxies.sort(
            key=lambda p: (p.success_rate, -p.response_time),
            reverse=True
        )
        
        # Selecionar proxy com weighted random baseado na taxa de sucesso
        weights = [p.success_rate for p in available_proxies]
        selected_proxy = random.choices(available_proxies, weights=weights)[0]
        
        selected_proxy.last_used = time.time()
        logger.debug(f"Proxy selecionado: {selected_proxy.host}:{selected_proxy.port}")
        
        return selected_proxy
    
    async def mark_proxy_success(self, proxy: ProxyInfo, response_time: float = 0.0):
        """Marca um proxy como bem-sucedido."""
        proxy.success_count += 1
        proxy.response_time = response_time
        if proxy.status == ProxyStatus.FAILED:
            proxy.status = ProxyStatus.ACTIVE
            logger.info(f"Proxy {proxy.host}:{proxy.port} reativado")
    
    async def mark_proxy_failure(self, proxy: ProxyInfo, domain: str = None, 
                                ban_for_domain: bool = False):
        """Marca um proxy como falhado."""
        proxy.failure_count += 1
        proxy.last_failure = time.time()
        
        if ban_for_domain and domain:
            proxy.ban_for_domain(domain)
        
        # Marcar como falhado se muitas falhas consecutivas
        if proxy.failure_count >= self.max_failures_before_ban:
            proxy.status = ProxyStatus.FAILED
            logger.warning(f"Proxy {proxy.host}:{proxy.port} marcado como falhado")
    
    async def test_proxy(self, proxy: ProxyInfo) -> Tuple[bool, float]:
        """Testa se um proxy está funcionando."""
        start_time = time.time()
        
        try:
            connector = aiohttp.TCPConnector(limit=1)
            timeout = aiohttp.ClientTimeout(total=self.test_timeout)
            
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout
            ) as session:
                async with session.get(
                    self.test_url,
                    proxy=proxy.url
                ) as response:
                    if response.status == 200:
                        response_time = time.time() - start_time
                        return True, response_time
                    else:
                        return False, 0.0
        
        except Exception as e:
            logger.debug(f"Teste de proxy falhou {proxy.host}:{proxy.port}: {e}")
            return False, 0.0
    
    async def health_check(self):
        """Executa health check em todos os proxies."""
        logger.info("Iniciando health check dos proxies")
        
        tasks = []
        for proxy in self.proxies:
            if proxy.status != ProxyStatus.BANNED:
                proxy.status = ProxyStatus.TESTING
                tasks.append(self._test_and_update_proxy(proxy))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        self.last_health_check = time.time()
        
        # Log estatísticas
        active_count = len([p for p in self.proxies if p.status == ProxyStatus.ACTIVE])
        failed_count = len([p for p in self.proxies if p.status == ProxyStatus.FAILED])
        banned_count = len([p for p in self.proxies if p.status == ProxyStatus.BANNED])
        
        logger.info(f"Health check concluído: {active_count} ativos, "
                   f"{failed_count} falhados, {banned_count} banidos")
    
    async def _test_and_update_proxy(self, proxy: ProxyInfo):
        """Testa e atualiza o status de um proxy."""
        try:
            is_working, response_time = await self.test_proxy(proxy)
            
            if is_working:
                proxy.status = ProxyStatus.ACTIVE
                proxy.response_time = response_time
                logger.debug(f"Proxy {proxy.host}:{proxy.port} OK ({response_time:.2f}s)")
            else:
                proxy.status = ProxyStatus.FAILED
                logger.debug(f"Proxy {proxy.host}:{proxy.port} falhou no teste")
        
        except Exception as e:
            proxy.status = ProxyStatus.FAILED
            logger.error(f"Erro ao testar proxy {proxy.host}:{proxy.port}: {e}")
    
    def get_stats(self) -> Dict:
        """Retorna estatísticas dos proxies."""
        total = len(self.proxies)
        active = len([p for p in self.proxies if p.status == ProxyStatus.ACTIVE])
        failed = len([p for p in self.proxies if p.status == ProxyStatus.FAILED])
        banned = len([p for p in self.proxies if p.status == ProxyStatus.BANNED])
        
        avg_success_rate = 0.0
        if self.proxies:
            avg_success_rate = sum(p.success_rate for p in self.proxies) / total
        
        return {
            "total": total,
            "active": active,
            "failed": failed,
            "banned": banned,
            "avg_success_rate": avg_success_rate,
            "last_health_check": self.last_health_check
        }
    
    def load_free_proxies(self):
        """Carrega uma lista de proxies gratuitos para teste."""
        # Lista de proxies gratuitos para desenvolvimento/teste
        free_proxies = [
            {"host": "8.210.83.33", "port": 80},
            {"host": "47.74.152.29", "port": 8888},
            {"host": "103.149.162.194", "port": 80},
            {"host": "103.148.72.192", "port": 80},
            {"host": "154.236.168.179", "port": 1981},
        ]
        
        logger.warning("Carregando proxies gratuitos - apenas para desenvolvimento!")
        self.add_proxy_list(free_proxies)