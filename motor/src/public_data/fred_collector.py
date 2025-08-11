import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
import logging

from .public_data_collector import PublicDataCollector, PublicDataResult, DataFrequency, PublicDataException
from ..cache.intelligent_cache import IntelligentCache
from ..monitoring.metrics import MetricsCollector

logger = logging.getLogger(__name__)

class FREDCollector(PublicDataCollector):
    """Coletor de dados do FRED (Federal Reserve Economic Data)."""
    
    def __init__(self, cache: IntelligentCache, metrics: MetricsCollector, api_key: str = None):
        super().__init__(cache, metrics)
        self.api_key = api_key or os.getenv('FRED_API_KEY')
        
        if not self.api_key:
            logger.warning("API key do FRED não fornecida. Algumas funcionalidades podem ser limitadas.")
        
        # Rate limiting mais conservador para FRED
        self.min_request_interval = 0.5  # 500ms entre requisições
        
        logger.info("FREDCollector inicializado")
    
    @property
    def base_url(self) -> str:
        """URL base da API do FRED."""
        return "https://api.stlouisfed.org/fred"
    
    @property
    def source_name(self) -> str:
        """Nome da fonte de dados."""
        return "fred"
    
    @property
    def supported_indicators(self) -> List[str]:
        """Lista de indicadores econômicos suportados pelo FRED."""
        return [
            # Taxa de juros
            'FEDFUNDS',      # Federal Funds Rate
            'DGS10',         # 10-Year Treasury Rate
            'DGS2',          # 2-Year Treasury Rate
            'DGS30',         # 30-Year Treasury Rate
            'TB3MS',         # 3-Month Treasury Bill
            
            # Inflação
            'CPIAUCSL',      # Consumer Price Index
            'CPILFESL',      # Core CPI
            'PCEPI',         # PCE Price Index
            'PCEPILFE',      # Core PCE Price Index
            
            # Emprego
            'UNRATE',        # Unemployment Rate
            'PAYEMS',        # Nonfarm Payrolls
            'CIVPART',       # Labor Force Participation Rate
            'EMRATIO',       # Employment-Population Ratio
            
            # PIB e Produção
            'GDP',           # Gross Domestic Product
            'GDPC1',         # Real GDP
            'INDPRO',        # Industrial Production Index
            'HOUST',         # Housing Starts
            
            # Mercado Monetário
            'M1SL',          # M1 Money Stock
            'M2SL',          # M2 Money Stock
            'BOGMBASE',      # Monetary Base
            
            # Confiança e Sentimento
            'UMCSENT',       # University of Michigan Consumer Sentiment
            'CSCICP03USM665S',  # Consumer Confidence Index
            
            # Mercado Imobiliário
            'CSUSHPISA',     # Case-Shiller Home Price Index
            'MORTGAGE30US',  # 30-Year Fixed Rate Mortgage Average
            
            # Comércio Internacional
            'BOPGSTB',       # Trade Balance
            'IMPGS',         # Imports of Goods and Services
            'EXPGS',         # Exports of Goods and Services
            
            # Indicadores Financeiros
            'DEXUSEU',       # US/Euro Exchange Rate
            'DEXJPUS',       # Japan/US Exchange Rate
            'DEXCHUS',       # China/US Exchange Rate
            'VIXCLS',        # VIX Volatility Index
            
            # Energia
            'DCOILWTICO',    # WTI Crude Oil Price
            'DCOILBRENTEU',  # Brent Crude Oil Price
            'DHHNGSP',       # Natural Gas Price
            
            # Metais Preciosos
            'GOLDAMGBD228NLBM',  # Gold Price
            'SLVPRUSD',      # Silver Price
        ]
    
    async def fetch_indicator(self, indicator: str, start_date: datetime = None,
                            end_date: datetime = None, **kwargs) -> PublicDataResult:
        """Busca dados de um indicador específico do FRED."""
        if indicator not in self.supported_indicators:
            raise PublicDataException(f"Indicador {indicator} não suportado pelo FRED")
        
        # Parâmetros da requisição
        params = {
            'series_id': indicator,
            'file_type': 'json'
        }
        
        # Adicionar API key se disponível
        if self.api_key:
            params['api_key'] = self.api_key
        
        # Adicionar datas se fornecidas
        if start_date:
            params['observation_start'] = start_date.strftime('%Y-%m-%d')
        if end_date:
            params['observation_end'] = end_date.strftime('%Y-%m-%d')
        
        # Adicionar parâmetros extras
        params.update(kwargs)
        
        try:
            # Buscar metadados da série
            metadata = await self._fetch_series_metadata(indicator)
            
            # Buscar dados da série
            url = f"{self.base_url}/series/observations"
            data = await self._make_request(url, params)
            
            # Processar resposta
            if 'observations' not in data:
                raise PublicDataException(f"Dados não encontrados para {indicator}")
            
            observations = data['observations']
            processed_data = []
            
            for obs in observations:
                date_str = obs.get('date')
                value_str = obs.get('value')
                
                if date_str and value_str and value_str != '.':
                    processed_data.append({
                        'date': self._parse_date(date_str),
                        'value': self._safe_float(value_str),
                        'realtime_start': obs.get('realtime_start'),
                        'realtime_end': obs.get('realtime_end')
                    })
            
            # Determinar frequência dos dados
            frequency = self._determine_frequency(metadata.get('frequency', 'Unknown'))
            
            return PublicDataResult(
                indicator=indicator,
                data=processed_data,
                source='fred',
                frequency=frequency,
                timestamp=datetime.now(timezone.utc),
                metadata=metadata,
                start_date=start_date,
                end_date=end_date,
                units=metadata.get('units'),
                description=metadata.get('title')
            )
        
        except Exception as e:
            logger.error(f"Erro ao buscar dados do FRED para {indicator}: {e}")
            raise PublicDataException(f"Falha ao buscar dados do FRED: {e}")
    
    async def _fetch_series_metadata(self, series_id: str) -> Dict[str, Any]:
        """Busca metadados de uma série do FRED."""
        params = {
            'series_id': series_id,
            'file_type': 'json'
        }
        
        if self.api_key:
            params['api_key'] = self.api_key
        
        url = f"{self.base_url}/series"
        data = await self._make_request(url, params)
        
        if 'seriess' in data and data['seriess']:
            return data['seriess'][0]
        
        return {}
    
    def _determine_frequency(self, freq_str: str) -> DataFrequency:
        """Determina a frequência dos dados baseado na string do FRED."""
        freq_mapping = {
            'Daily': DataFrequency.DAILY,
            'Weekly': DataFrequency.WEEKLY,
            'Monthly': DataFrequency.MONTHLY,
            'Quarterly': DataFrequency.QUARTERLY,
            'Annual': DataFrequency.YEARLY,
            'Semiannual': DataFrequency.YEARLY
        }
        
        return freq_mapping.get(freq_str, DataFrequency.MONTHLY)
    
    async def search_indicators(self, search_text: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Busca indicadores por texto."""
        if not self.api_key:
            logger.warning("API key necessária para busca de indicadores")
            return []
        
        params = {
            'search_text': search_text,
            'limit': limit,
            'file_type': 'json',
            'api_key': self.api_key
        }
        
        try:
            url = f"{self.base_url}/series/search"
            data = await self._make_request(url, params)
            
            if 'seriess' in data:
                return [
                    {
                        'id': series.get('id'),
                        'title': series.get('title'),
                        'units': series.get('units'),
                        'frequency': series.get('frequency'),
                        'observation_start': series.get('observation_start'),
                        'observation_end': series.get('observation_end'),
                        'last_updated': series.get('last_updated'),
                        'popularity': series.get('popularity'),
                        'notes': series.get('notes')
                    }
                    for series in data['seriess']
                ]
            
            return []
        
        except Exception as e:
            logger.error(f"Erro ao buscar indicadores no FRED: {e}")
            return []
    
    async def get_categories(self) -> List[Dict[str, Any]]:
        """Obtém categorias de dados disponíveis."""
        if not self.api_key:
            return []
        
        params = {
            'file_type': 'json',
            'api_key': self.api_key
        }
        
        try:
            url = f"{self.base_url}/category"
            data = await self._make_request(url, params)
            
            if 'categories' in data:
                return [
                    {
                        'id': cat.get('id'),
                        'name': cat.get('name'),
                        'parent_id': cat.get('parent_id')
                    }
                    for cat in data['categories']
                ]
            
            return []
        
        except Exception as e:
            logger.error(f"Erro ao buscar categorias do FRED: {e}")
            return []
    
    async def get_releases(self) -> List[Dict[str, Any]]:
        """Obtém releases de dados disponíveis."""
        if not self.api_key:
            return []
        
        params = {
            'file_type': 'json',
            'api_key': self.api_key
        }
        
        try:
            url = f"{self.base_url}/releases"
            data = await self._make_request(url, params)
            
            if 'releases' in data:
                return [
                    {
                        'id': release.get('id'),
                        'name': release.get('name'),
                        'press_release': release.get('press_release'),
                        'link': release.get('link')
                    }
                    for release in data['releases']
                ]
            
            return []
        
        except Exception as e:
            logger.error(f"Erro ao buscar releases do FRED: {e}")
            return []
    
    async def get_latest_values(self, indicators: List[str]) -> Dict[str, Any]:
        """Obtém os valores mais recentes para uma lista de indicadores."""
        results = {}
        
        for indicator in indicators:
            try:
                # Buscar últimos 30 dias
                end_date = datetime.now(timezone.utc)
                start_date = end_date - timedelta(days=30)
                
                data = await self.fetch_indicator(indicator, start_date, end_date)
                
                if data.data:
                    # Pegar o valor mais recente
                    latest = max(data.data, key=lambda x: x['date'])
                    results[indicator] = {
                        'value': latest['value'],
                        'date': latest['date'],
                        'units': data.units,
                        'description': data.description
                    }
            
            except Exception as e:
                logger.error(f"Erro ao buscar valor mais recente para {indicator}: {e}")
                results[indicator] = None
        
        return results
    
    def set_api_key(self, api_key: str):
        """Define a API key do FRED."""
        self.api_key = api_key
        logger.info("API key do FRED atualizada")
    
    async def test_connection(self) -> bool:
        """Testa a conexão com a API do FRED."""
        try:
            # Tentar buscar dados do Federal Funds Rate
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=7)
            
            result = await self.fetch_indicator('FEDFUNDS', start_date, end_date)
            return result is not None and len(result.data) > 0
        
        except Exception as e:
            logger.error(f"Erro no teste de conexão FRED: {e}")
            return False
    
    async def get_indicator_metadata(self, indicator: str) -> Optional[Dict[str, Any]]:
        """Obtém metadados detalhados de um indicador."""
        if indicator not in self.supported_indicators:
            return None
        
        try:
            metadata = await self._fetch_series_metadata(indicator)
            
            return {
                'code': indicator,
                'source': self.source_name,
                'title': metadata.get('title'),
                'units': metadata.get('units'),
                'frequency': metadata.get('frequency'),
                'seasonal_adjustment': metadata.get('seasonal_adjustment'),
                'observation_start': metadata.get('observation_start'),
                'observation_end': metadata.get('observation_end'),
                'last_updated': metadata.get('last_updated'),
                'popularity': metadata.get('popularity'),
                'notes': metadata.get('notes')
            }
        
        except Exception as e:
            logger.error(f"Erro ao buscar metadados para {indicator}: {e}")
            return None