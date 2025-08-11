import asyncio
import aiohttp
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
import logging
from abc import ABC, abstractmethod
from enum import Enum

from ..resilience.circuit_breaker import AdvancedCircuitBreaker
from ..cache.intelligent_cache import IntelligentCache
from ..monitoring.metrics import MetricsCollector

logger = logging.getLogger(__name__)

class DataFrequency(Enum):
    """Frequência dos dados."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    REAL_TIME = "real_time"

@dataclass
class PublicDataResult:
    """Resultado de dados públicos coletados."""
    indicator: str
    data: List[Dict[str, Any]]
    source: str
    frequency: DataFrequency
    timestamp: datetime
    metadata: Dict[str, Any]
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    units: Optional[str] = None
    description: Optional[str] = None

class PublicDataException(Exception):
    """Exceção específica para erros de dados públicos."""
    pass

class PublicDataCollector(ABC):
    """Classe base para coletores de dados públicos."""
    
    def __init__(self, cache: IntelligentCache, metrics: MetricsCollector):
        self.cache = cache
        self.metrics = metrics
        self.session: Optional[aiohttp.ClientSession] = None
        
        # Circuit breaker
        from src.resilience.circuit_breaker import CircuitBreakerConfig
        
        cb_config = CircuitBreakerConfig(
            failure_threshold=3,
            open_timeout=600  # 10 minutos
        )
        self.circuit_breaker = AdvancedCircuitBreaker(f'{self.source_name}_public_data', cb_config)
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1.0  # 1 segundo entre requisições
        
        logger.info(f"{self.__class__.__name__} inicializado")
    
    @property
    @abstractmethod
    def base_url(self) -> str:
        """URL base da API."""
        pass
    
    @property
    @abstractmethod
    def source_name(self) -> str:
        """Nome da fonte de dados."""
        pass
    
    @property
    @abstractmethod
    def supported_indicators(self) -> List[str]:
        """Lista de indicadores suportados."""
        pass
    
    @abstractmethod
    async def fetch_indicator(self, indicator: str, start_date: datetime = None, 
                            end_date: datetime = None, **kwargs) -> PublicDataResult:
        """Busca dados de um indicador específico."""
        pass
    
    async def __aenter__(self):
        """Context manager entry."""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self._close_session()
    
    async def _ensure_session(self):
        """Garante que a sessão HTTP está ativa."""
        if not self.session or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            connector = aiohttp.TCPConnector(
                limit=10,
                ssl=False,  # Para desenvolvimento
                enable_cleanup_closed=True
            )
            
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    'User-Agent': 'Nacao-Trader-Data-Collector/1.0',
                    'Accept': 'application/json'
                }
            )
    
    async def _close_session(self):
        """Fecha a sessão HTTP."""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
    
    async def _make_request(self, url: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Faz uma requisição HTTP com rate limiting e circuit breaker."""
        # Rate limiting
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - time_since_last)
        
        await self._ensure_session()
        
        start_time = time.time()
        
        try:
            async with self.circuit_breaker:
                async with self.session.get(url, params=params) as response:
                    response_time = time.time() - start_time
                    self.last_request_time = time.time()
                    
                    if response.status == 200:
                        data = await response.json()
                        
                        # Registrar métricas de sucesso
                        await self.metrics.record_counter(
                            f"public_data_{self.source_name}_requests_total",
                            labels={"status": "success"}
                        )
                        await self.metrics.record_histogram(
                            f"public_data_{self.source_name}_request_duration_seconds",
                            response_time
                        )
                        
                        return data
                    
                    elif response.status == 429:  # Rate limited
                        retry_after = response.headers.get('Retry-After', '60')
                        await self.metrics.record_counter(
                            f"public_data_{self.source_name}_requests_total",
                            labels={"status": "rate_limited"}
                        )
                        raise PublicDataException(f"Rate limited. Retry after {retry_after} seconds")
                    
                    elif response.status == 404:
                        await self.metrics.record_counter(
                            f"public_data_{self.source_name}_requests_total",
                            labels={"status": "not_found"}
                        )
                        raise PublicDataException(f"Endpoint not found: {url}")
                    
                    else:
                        error_text = await response.text()
                        await self.metrics.record_counter(
                            f"public_data_{self.source_name}_requests_total",
                            labels={"status": "error", "code": str(response.status)}
                        )
                        raise PublicDataException(f"HTTP {response.status}: {error_text}")
        
        except asyncio.TimeoutError:
            await self.metrics.record_counter(
                f"public_data_{self.source_name}_requests_total",
                labels={"status": "timeout"}
            )
            raise PublicDataException(f"Timeout na requisição: {url}")
        
        except Exception as e:
            if not isinstance(e, PublicDataException):
                await self.metrics.record_counter(
                    f"public_data_{self.source_name}_requests_total",
                    labels={"status": "error", "error": type(e).__name__}
                )
                raise PublicDataException(f"Erro na requisição: {e}")
            raise
    
    async def fetch_multiple_indicators(self, indicators: List[str], 
                                      start_date: datetime = None,
                                      end_date: datetime = None,
                                      **kwargs) -> List[PublicDataResult]:
        """Busca múltiplos indicadores."""
        results = []
        
        # Verificar cache primeiro
        cached_results = []
        indicators_to_fetch = []
        
        for indicator in indicators:
            cache_key = self._get_cache_key(indicator, start_date, end_date, **kwargs)
            cached_data = await self.cache.get(cache_key)
            
            if cached_data:
                cached_results.append(cached_data)
                logger.debug(f"Dados encontrados no cache para {indicator}")
            else:
                indicators_to_fetch.append(indicator)
        
        # Buscar indicadores não encontrados no cache
        if indicators_to_fetch:
            tasks = [
                self.fetch_indicator(indicator, start_date, end_date, **kwargs)
                for indicator in indicators_to_fetch
            ]
            
            fetched_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(fetched_results):
                if isinstance(result, PublicDataResult):
                    # Cache o resultado
                    cache_key = self._get_cache_key(
                        indicators_to_fetch[i], start_date, end_date, **kwargs
                    )
                    await self.cache.set(cache_key, result, ttl=3600)  # 1 hora
                    results.append(result)
                else:
                    logger.error(f"Erro ao buscar {indicators_to_fetch[i]}: {result}")
        
        # Combinar resultados do cache e buscados
        results.extend(cached_results)
        
        return results
    
    def _get_cache_key(self, indicator: str, start_date: datetime = None,
                      end_date: datetime = None, **kwargs) -> str:
        """Gera chave de cache para um indicador."""
        key_parts = [f"public_data:{self.source_name}:{indicator}"]
        
        if start_date:
            key_parts.append(f"start:{start_date.strftime('%Y-%m-%d')}")
        if end_date:
            key_parts.append(f"end:{end_date.strftime('%Y-%m-%d')}")
        
        # Adicionar outros parâmetros
        for key, value in sorted(kwargs.items()):
            if value is not None:
                key_parts.append(f"{key}:{value}")
        
        return ":".join(key_parts)
    
    def _parse_date(self, date_str: str) -> datetime:
        """Converte string de data para datetime."""
        try:
            # Tentar diferentes formatos
            formats = [
                '%Y-%m-%d',
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%dT%H:%M:%SZ',
                '%Y-%m-%dT%H:%M:%S.%fZ'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
                except ValueError:
                    continue
            
            # Se nenhum formato funcionou, tentar parsing automático
            from dateutil import parser
            return parser.parse(date_str).replace(tzinfo=timezone.utc)
        
        except Exception as e:
            logger.error(f"Erro ao fazer parse da data '{date_str}': {e}")
            return datetime.now(timezone.utc)
    
    def _safe_float(self, value: Any) -> Optional[float]:
        """Converte valor para float de forma segura."""
        if value is None or value == '':
            return None
        
        try:
            if isinstance(value, str):
                # Remover caracteres não numéricos exceto ponto e sinal
                cleaned = ''.join(c for c in value if c.isdigit() or c in '.-')
                if cleaned:
                    return float(cleaned)
            else:
                return float(value)
        except (ValueError, TypeError):
            pass
        
        return None
    
    async def get_available_indicators(self) -> List[Dict[str, Any]]:
        """Retorna lista de indicadores disponíveis com metadados."""
        return [
            {
                'code': indicator,
                'source': self.source_name,
                'description': f'Indicador {indicator} da fonte {self.source_name}'
            }
            for indicator in self.supported_indicators
        ]
    
    async def get_indicator_metadata(self, indicator: str) -> Optional[Dict[str, Any]]:
        """Obtém metadados de um indicador específico."""
        if indicator not in self.supported_indicators:
            return None
        
        return {
            'code': indicator,
            'source': self.source_name,
            'base_url': self.base_url,
            'supported': True
        }
    
    async def test_connection(self) -> bool:
        """Testa a conexão com a API."""
        try:
            # Tentar buscar um indicador simples
            if self.supported_indicators:
                test_indicator = self.supported_indicators[0]
                end_date = datetime.now(timezone.utc)
                start_date = end_date - timedelta(days=30)
                
                result = await self.fetch_indicator(
                    test_indicator, start_date, end_date
                )
                
                return result is not None
            
            return False
        
        except Exception as e:
            logger.error(f"Erro no teste de conexão {self.source_name}: {e}")
            return False
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Retorna status de saúde do coletor."""
        connection_test = await self.test_connection()
        
        return {
            'healthy': connection_test,
            'source': self.source_name,
            'base_url': self.base_url,
            'supported_indicators_count': len(self.supported_indicators),
            'circuit_breaker': self.circuit_breaker.get_stats(),
            'session_active': self.session is not None and not self.session.closed
        }
    
    def __del__(self):
        """Destructor para limpar recursos."""
        if self.session and not self.session.closed:
            # Não podemos usar await aqui, então apenas logamos
            logger.warning(f"Sessão HTTP não foi fechada adequadamente para {self.source_name}")