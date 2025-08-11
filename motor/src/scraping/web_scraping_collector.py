import asyncio
import aiohttp
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime, timezone
import logging
from urllib.parse import urljoin, urlparse

from .proxy_rotator import ProxyRotator, ProxyInfo
from .user_agent_rotator import UserAgentRotator, DeviceType, BrowserType
from .rate_limiter import IntelligentRateLimiter
from ..resilience.circuit_breaker import AdvancedCircuitBreaker
from ..cache.intelligent_cache import IntelligentCache
from ..monitoring.metrics import MetricsCollector

logger = logging.getLogger(__name__)

@dataclass
class ScrapingResult:
    """Resultado de uma operação de scraping."""
    symbol: str
    data: Dict[str, Any]
    source: str
    timestamp: datetime
    success: bool
    error: Optional[str] = None
    response_time: float = 0.0
    status_code: Optional[int] = None

class ScrapingException(Exception):
    """Exceção específica para erros de scraping."""
    pass

class WebScrapingCollector:
    """Coletor de dados via web scraping com anti-detecção avançada."""
    
    def __init__(self, cache: IntelligentCache, metrics: MetricsCollector):
        self.proxy_rotator = ProxyRotator()
        self.user_agent_rotator = UserAgentRotator()
        self.rate_limiter = IntelligentRateLimiter()
        self.cache = cache
        self.metrics = metrics
        
        # Circuit breakers por fonte
        from src.resilience.circuit_breaker import CircuitBreakerConfig
        
        yahoo_config = CircuitBreakerConfig(
            failure_threshold=5,
            open_timeout=300
        )
        google_config = CircuitBreakerConfig(
            failure_threshold=3,
            open_timeout=600
        )
        marketwatch_config = CircuitBreakerConfig(
            failure_threshold=4,
            open_timeout=450
        )
        
        self.circuit_breakers = {
            'yahoo': AdvancedCircuitBreaker('yahoo_scraping', yahoo_config),
            'google': AdvancedCircuitBreaker('google_scraping', google_config),
            'marketwatch': AdvancedCircuitBreaker('marketwatch_scraping', marketwatch_config)
        }
        
        # Configurações por fonte
        self.source_configs = {
            'yahoo': {
                'base_url': 'https://finance.yahoo.com',
                'quote_url': 'https://finance.yahoo.com/quote/{symbol}',
                'timeout': 15,
                'retry_attempts': 3
            },
            'google': {
                'base_url': 'https://www.google.com',
                'quote_url': 'https://www.google.com/finance/quote/{symbol}',
                'timeout': 12,
                'retry_attempts': 2
            },
            'marketwatch': {
                'base_url': 'https://www.marketwatch.com',
                'quote_url': 'https://www.marketwatch.com/investing/stock/{symbol}',
                'timeout': 20,
                'retry_attempts': 3
            }
        }
        
        # Carregar proxies gratuitos para desenvolvimento
        self.proxy_rotator.load_free_proxies()
        
        logger.info("WebScrapingCollector inicializado")
    
    async def collect_data(self, symbol: str, sources: List[str] = None) -> List[ScrapingResult]:
        """Coleta dados de múltiplas fontes para um símbolo."""
        if sources is None:
            sources = ['yahoo', 'google', 'marketwatch']
        
        # Verificar cache primeiro
        cache_key = f"scraping:{symbol}:all"
        cached_data = await self.cache.get(cache_key)
        if cached_data:
            logger.debug(f"Dados encontrados no cache para {symbol}")
            return cached_data
        
        results = []
        tasks = []
        
        for source in sources:
            if source in self.circuit_breakers:
                task = self._collect_from_source(symbol, source)
                tasks.append(task)
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filtrar resultados válidos
            valid_results = [
                result for result in results 
                if isinstance(result, ScrapingResult) and result.success
            ]
            
            # Cache apenas resultados válidos
            if valid_results:
                await self.cache.set(cache_key, valid_results, ttl=300)  # 5 minutos
            
            return valid_results
        
        return []
    
    async def _collect_from_source(self, symbol: str, source: str) -> ScrapingResult:
        """Coleta dados de uma fonte específica."""
        start_time = time.time()
        
        try:
            async with self.circuit_breakers[source]:
                if source == 'yahoo':
                    result = await self._scrape_yahoo_finance(symbol)
                elif source == 'google':
                    result = await self._scrape_google_finance(symbol)
                elif source == 'marketwatch':
                    result = await self._scrape_marketwatch(symbol)
                else:
                    raise ScrapingException(f"Fonte não suportada: {source}")
                
                response_time = time.time() - start_time
                result.response_time = response_time
                
                # Registrar métricas de sucesso
                await self.metrics.record_counter(
                    f"scraping_{source}_success_total",
                    labels={"symbol": symbol}
                )
                await self.metrics.record_histogram(
                    f"scraping_{source}_duration_seconds",
                    response_time,
                    labels={"symbol": symbol}
                )
                
                return result
        
        except Exception as e:
            response_time = time.time() - start_time
            error_msg = str(e)
            
            # Registrar métricas de erro
            await self.metrics.record_counter(
                f"scraping_{source}_error_total",
                labels={"symbol": symbol, "error": type(e).__name__}
            )
            
            logger.error(f"Erro ao coletar dados de {source} para {symbol}: {error_msg}")
            
            return ScrapingResult(
                symbol=symbol,
                data={},
                source=source,
                timestamp=datetime.now(timezone.utc),
                success=False,
                error=error_msg,
                response_time=response_time
            )
    
    async def _scrape_yahoo_finance(self, symbol: str) -> ScrapingResult:
        """Scraping específico do Yahoo Finance."""
        url = self.source_configs['yahoo']['quote_url'].format(symbol=symbol)
        
        html = await self._fetch_page(url, 'yahoo')
        data = await self._parse_yahoo_data(html, symbol)
        
        return ScrapingResult(
            symbol=symbol,
            data=data,
            source='yahoo_scraping',
            timestamp=datetime.now(timezone.utc),
            success=True
        )
    
    async def _parse_yahoo_data(self, html: str, symbol: str) -> Dict[str, Any]:
        """Parser para dados do Yahoo Finance."""
        soup = BeautifulSoup(html, 'html.parser')
        data = {'symbol': symbol}
        
        try:
            # Preço atual
            price_selectors = [
                'fin-streamer[data-field="regularMarketPrice"]',
                '[data-test="qsp-price"]',
                '.Trsdu\\(0\\.3s\\) .Fw\\(b\\) .Fz\\(36px\\)'
            ]
            
            for selector in price_selectors:
                price_element = soup.select_one(selector)
                if price_element:
                    price_text = price_element.get_text(strip=True)
                    data['current_price'] = self._parse_numeric_value(price_text)
                    break
            
            # Variação
            change_selectors = [
                'fin-streamer[data-field="regularMarketChange"]',
                '[data-test="qsp-price-change"]'
            ]
            
            for selector in change_selectors:
                change_element = soup.select_one(selector)
                if change_element:
                    change_text = change_element.get_text(strip=True)
                    data['change'] = self._parse_numeric_value(change_text)
                    break
            
            # Variação percentual
            change_percent_selectors = [
                'fin-streamer[data-field="regularMarketChangePercent"]',
                '[data-test="qsp-price-change-percent"]'
            ]
            
            for selector in change_percent_selectors:
                change_percent_element = soup.select_one(selector)
                if change_percent_element:
                    change_percent_text = change_percent_element.get_text(strip=True)
                    data['change_percent'] = self._parse_percentage_value(change_percent_text)
                    break
            
            # Dados adicionais da tabela de estatísticas
            stats_mapping = {
                'Previous Close': 'previous_close',
                'Open': 'open',
                'Bid': 'bid',
                'Ask': 'ask',
                'Day\'s Range': 'day_range',
                '52 Week Range': 'week_52_range',
                'Volume': 'volume',
                'Avg. Volume': 'avg_volume',
                'Market Cap': 'market_cap',
                'Beta (5Y Monthly)': 'beta',
                'PE Ratio (TTM)': 'pe_ratio',
                'EPS (TTM)': 'eps',
                'Earnings Date': 'earnings_date',
                'Forward Dividend & Yield': 'dividend_yield',
                'Ex-Dividend Date': 'ex_dividend_date',
                '1y Target Est': 'target_price'
            }
            
            # Buscar dados na tabela de estatísticas
            for label, field in stats_mapping.items():
                value = self._extract_table_value(soup, label)
                if value:
                    data[field] = value
            
            # Tentar extrair dados do JSON embutido
            json_data = self._extract_json_data(html)
            if json_data:
                data.update(json_data)
            
        except Exception as e:
            logger.error(f"Erro ao fazer parse dos dados do Yahoo para {symbol}: {e}")
            raise ScrapingException(f"Falha no parse do Yahoo Finance: {e}")
        
        return data
    
    async def _scrape_google_finance(self, symbol: str) -> ScrapingResult:
        """Scraping específico do Google Finance."""
        # Ajustar símbolo para formato do Google
        google_symbol = symbol.replace('.SA', '')
        if ':' not in google_symbol:
            google_symbol = f"NASDAQ:{google_symbol}"
        
        url = self.source_configs['google']['quote_url'].format(symbol=google_symbol)
        
        html = await self._fetch_page(url, 'google')
        data = await self._parse_google_data(html, symbol)
        
        return ScrapingResult(
            symbol=symbol,
            data=data,
            source='google_scraping',
            timestamp=datetime.now(timezone.utc),
            success=True
        )
    
    async def _parse_google_data(self, html: str, symbol: str) -> Dict[str, Any]:
        """Parser para dados do Google Finance."""
        soup = BeautifulSoup(html, 'html.parser')
        data = {'symbol': symbol}
        
        try:
            # Preço atual
            price_element = soup.select_one('[data-last-price]')
            if price_element:
                data['current_price'] = self._parse_numeric_value(
                    price_element.get('data-last-price', '')
                )
            
            # Variação
            change_element = soup.select_one('[data-last-change]')
            if change_element:
                data['change'] = self._parse_numeric_value(
                    change_element.get('data-last-change', '')
                )
            
            # Variação percentual
            change_percent_element = soup.select_one('[data-last-change-percentage]')
            if change_percent_element:
                data['change_percent'] = self._parse_percentage_value(
                    change_percent_element.get('data-last-change-percentage', '')
                )
            
        except Exception as e:
            logger.error(f"Erro ao fazer parse dos dados do Google para {symbol}: {e}")
            raise ScrapingException(f"Falha no parse do Google Finance: {e}")
        
        return data
    
    async def _scrape_marketwatch(self, symbol: str) -> ScrapingResult:
        """Scraping específico do MarketWatch."""
        url = self.source_configs['marketwatch']['quote_url'].format(symbol=symbol)
        
        html = await self._fetch_page(url, 'marketwatch')
        data = await self._parse_marketwatch_data(html, symbol)
        
        return ScrapingResult(
            symbol=symbol,
            data=data,
            source='marketwatch_scraping',
            timestamp=datetime.now(timezone.utc),
            success=True
        )
    
    async def _parse_marketwatch_data(self, html: str, symbol: str) -> Dict[str, Any]:
        """Parser para dados do MarketWatch."""
        soup = BeautifulSoup(html, 'html.parser')
        data = {'symbol': symbol}
        
        try:
            # Preço atual
            price_selectors = [
                '.intraday__price .value',
                '[data-module="InstrumentPrice"] .value',
                '.quote-price .value'
            ]
            
            for selector in price_selectors:
                price_element = soup.select_one(selector)
                if price_element:
                    data['current_price'] = self._parse_numeric_value(
                        price_element.get_text(strip=True)
                    )
                    break
            
            # Variação
            change_selectors = [
                '.intraday__change .value',
                '[data-module="InstrumentPrice"] .change .value'
            ]
            
            for selector in change_selectors:
                change_element = soup.select_one(selector)
                if change_element:
                    data['change'] = self._parse_numeric_value(
                        change_element.get_text(strip=True)
                    )
                    break
            
        except Exception as e:
            logger.error(f"Erro ao fazer parse dos dados do MarketWatch para {symbol}: {e}")
            raise ScrapingException(f"Falha no parse do MarketWatch: {e}")
        
        return data
    
    async def _fetch_page(self, url: str, source: str) -> str:
        """Busca uma página web com todas as proteções anti-detecção."""
        # Adquirir rate limit
        await self.rate_limiter.acquire(url)
        
        proxy = await self.proxy_rotator.get_proxy(urlparse(url).netloc)
        headers = self.user_agent_rotator.get_user_agent_with_headers(DeviceType.DESKTOP)
        
        config = self.source_configs[source]
        timeout = aiohttp.ClientTimeout(total=config['timeout'])
        
        start_time = time.time()
        
        try:
            connector = aiohttp.TCPConnector(
                limit=10,
                ssl=False,  # Para desenvolvimento
                enable_cleanup_closed=True
            )
            
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers=headers
            ) as session:
                
                proxy_url = proxy.url if proxy else None
                
                async with session.get(url, proxy=proxy_url) as response:
                    response_time = time.time() - start_time
                    
                    if response.status == 200:
                        html = await response.text()
                        
                        # Marcar sucesso
                        if proxy:
                            await self.proxy_rotator.mark_proxy_success(proxy, response_time)
                        
                        self.rate_limiter.release(
                            url, True, response_time, response.status
                        )
                        
                        self.user_agent_rotator.mark_success(headers['User-Agent'])
                        
                        return html
                    
                    elif response.status == 429:  # Rate limited
                        retry_after = response.headers.get('Retry-After')
                        if proxy:
                            await self.proxy_rotator.mark_proxy_failure(
                                proxy, urlparse(url).netloc, ban_for_domain=True
                            )
                        
                        self.rate_limiter.release(
                            url, False, response_time, response.status, 
                            int(retry_after) if retry_after else None
                        )
                        
                        raise ScrapingException(f"Rate limited (429): {url}")
                    
                    elif response.status in [403, 406]:  # Blocked
                        if proxy:
                            await self.proxy_rotator.mark_proxy_failure(
                                proxy, urlparse(url).netloc, ban_for_domain=True
                            )
                        
                        self.rate_limiter.release(url, False, response_time, response.status)
                        self.user_agent_rotator.mark_failure(headers['User-Agent'])
                        
                        raise ScrapingException(f"Blocked ({response.status}): {url}")
                    
                    else:
                        if proxy:
                            await self.proxy_rotator.mark_proxy_failure(proxy)
                        
                        self.rate_limiter.release(url, False, response_time, response.status)
                        
                        raise ScrapingException(f"HTTP {response.status}: {url}")
        
        except asyncio.TimeoutError:
            if proxy:
                await self.proxy_rotator.mark_proxy_failure(proxy)
            
            self.rate_limiter.release(url, False, time.time() - start_time)
            raise ScrapingException(f"Timeout: {url}")
        
        except Exception as e:
            if proxy:
                await self.proxy_rotator.mark_proxy_failure(proxy)
            
            self.rate_limiter.release(url, False, time.time() - start_time)
            raise ScrapingException(f"Erro na requisição: {e}")
    
    def _parse_numeric_value(self, text: str) -> Optional[float]:
        """Converte texto em valor numérico."""
        if not text:
            return None
        
        try:
            # Remover caracteres não numéricos exceto ponto, vírgula e sinal
            cleaned = re.sub(r'[^\d.,+-]', '', text.strip())
            
            if not cleaned:
                return None
            
            # Tratar vírgula como separador decimal se for o último
            if ',' in cleaned and '.' in cleaned:
                # Se tem ambos, vírgula é separador de milhares
                cleaned = cleaned.replace(',', '')
            elif ',' in cleaned and cleaned.count(',') == 1:
                # Se só tem vírgula, pode ser separador decimal
                parts = cleaned.split(',')
                if len(parts[1]) <= 2:  # Provavelmente decimal
                    cleaned = cleaned.replace(',', '.')
                else:  # Provavelmente separador de milhares
                    cleaned = cleaned.replace(',', '')
            
            return float(cleaned)
        
        except (ValueError, AttributeError):
            return None
    
    def _parse_percentage_value(self, text: str) -> Optional[float]:
        """Converte texto de porcentagem em valor numérico."""
        if not text:
            return None
        
        # Remover símbolo de porcentagem
        cleaned = text.replace('%', '').strip()
        return self._parse_numeric_value(cleaned)
    
    def _extract_table_value(self, soup: BeautifulSoup, label: str) -> Optional[str]:
        """Extrai valor de uma tabela baseado no label."""
        try:
            # Procurar por diferentes estruturas de tabela
            selectors = [
                f'td:contains("{label}") + td',
                f'span:contains("{label}") + span',
                f'div:contains("{label}") + div'
            ]
            
            for selector in selectors:
                elements = soup.select(selector)
                if elements:
                    return elements[0].get_text(strip=True)
            
            return None
        
        except Exception:
            return None
    
    def _extract_json_data(self, html: str) -> Dict[str, Any]:
        """Extrai dados JSON embutidos na página."""
        try:
            # Procurar por padrões comuns de JSON embutido
            patterns = [
                r'root\.App\.main\s*=\s*(\{.+?\});',
                r'window\.__INITIAL_STATE__\s*=\s*(\{.+?\});',
                r'QuoteSummaryStore":(\{.+?\}),"'
            ]
            
            for pattern in patterns:
                matches = re.search(pattern, html, re.DOTALL)
                if matches:
                    json_str = matches.group(1)
                    data = json.loads(json_str)
                    return self._extract_relevant_data(data)
            
            return {}
        
        except Exception as e:
            logger.debug(f"Erro ao extrair JSON embutido: {e}")
            return {}
    
    def _extract_relevant_data(self, json_data: Dict) -> Dict[str, Any]:
        """Extrai dados relevantes de estruturas JSON complexas."""
        relevant_data = {}
        
        try:
            # Navegar pela estrutura JSON procurando dados financeiros
            if isinstance(json_data, dict):
                for key, value in json_data.items():
                    if key in ['price', 'regularMarketPrice', 'currentPrice']:
                        relevant_data['current_price'] = self._safe_extract_number(value)
                    elif key in ['change', 'regularMarketChange']:
                        relevant_data['change'] = self._safe_extract_number(value)
                    elif key in ['changePercent', 'regularMarketChangePercent']:
                        relevant_data['change_percent'] = self._safe_extract_number(value)
                    elif key in ['volume', 'regularMarketVolume']:
                        relevant_data['volume'] = self._safe_extract_number(value)
                    elif key in ['marketCap']:
                        relevant_data['market_cap'] = self._safe_extract_number(value)
                    elif isinstance(value, dict):
                        # Recursão para objetos aninhados
                        nested_data = self._extract_relevant_data(value)
                        relevant_data.update(nested_data)
        
        except Exception as e:
            logger.debug(f"Erro ao extrair dados relevantes: {e}")
        
        return relevant_data
    
    def _safe_extract_number(self, value: Any) -> Optional[float]:
        """Extrai número de forma segura de diferentes tipos de dados."""
        try:
            if isinstance(value, (int, float)):
                return float(value)
            elif isinstance(value, str):
                return self._parse_numeric_value(value)
            elif isinstance(value, dict) and 'raw' in value:
                return float(value['raw'])
            elif isinstance(value, dict) and 'fmt' in value:
                return self._parse_numeric_value(value['fmt'])
            else:
                return None
        except (ValueError, TypeError):
            return None
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Retorna status de saúde do coletor."""
        return {
            'proxy_stats': self.proxy_rotator.get_stats(),
            'user_agent_stats': self.user_agent_rotator.get_stats(),
            'rate_limiter_stats': self.rate_limiter.get_all_stats(),
            'circuit_breaker_stats': {
                name: cb.get_stats() 
                for name, cb in self.circuit_breakers.items()
            }
        }