from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
import logging

from .public_data_collector import PublicDataCollector, PublicDataResult, DataFrequency, PublicDataException
from ..cache.intelligent_cache import IntelligentCache
from ..monitoring.metrics import MetricsCollector

logger = logging.getLogger(__name__)

class WorldBankCollector(PublicDataCollector):
    """Coletor de dados do World Bank."""
    
    def __init__(self, cache: IntelligentCache, metrics: MetricsCollector):
        super().__init__(cache, metrics)
        
        # Rate limiting mais conservador para World Bank
        self.min_request_interval = 1.0  # 1 segundo entre requisições
        
        logger.info("WorldBankCollector inicializado")
    
    @property
    def base_url(self) -> str:
        """URL base da API do World Bank."""
        return "https://api.worldbank.org/v2"
    
    @property
    def source_name(self) -> str:
        """Nome da fonte de dados."""
        return "world_bank"
    
    @property
    def supported_indicators(self) -> List[str]:
        """Lista de indicadores econômicos suportados pelo World Bank."""
        return [
            # PIB e Crescimento
            'NY.GDP.MKTP.CD',        # GDP (current US$)
            'NY.GDP.MKTP.KD.ZG',     # GDP growth (annual %)
            'NY.GDP.PCAP.CD',        # GDP per capita (current US$)
            'NY.GDP.PCAP.KD.ZG',     # GDP per capita growth (annual %)
            
            # Inflação e Preços
            'FP.CPI.TOTL.ZG',        # Inflation, consumer prices (annual %)
            'PA.NUS.FCRF',           # Official exchange rate (LCU per US$)
            'PA.NUS.PPPC.RF',        # PPP conversion factor (GDP)
            
            # Comércio Internacional
            'NE.EXP.GNFS.ZS',        # Exports of goods and services (% of GDP)
            'NE.IMP.GNFS.ZS',        # Imports of goods and services (% of GDP)
            'BN.CAB.XOKA.CD',        # Current account balance (BoP, current US$)
            'BX.KLT.DINV.CD.WD',     # Foreign direct investment, net inflows (BoP, current US$)
            
            # População e Demografia
            'SP.POP.TOTL',           # Population, total
            'SP.POP.GROW',           # Population growth (annual %)
            'SP.URB.TOTL.IN.ZS',     # Urban population (% of total population)
            'SP.DYN.LE00.IN',        # Life expectancy at birth, total (years)
            
            # Emprego e Trabalho
            'SL.UEM.TOTL.ZS',        # Unemployment, total (% of total labor force)
            'SL.TLF.CACT.ZS',        # Labor force participation rate, total (% of total population ages 15+)
            'SL.AGR.EMPL.ZS',        # Employment in agriculture (% of total employment)
            'SL.IND.EMPL.ZS',        # Employment in industry (% of total employment)
            'SL.SRV.EMPL.ZS',        # Employment in services (% of total employment)
            
            # Educação
            'SE.ADT.LITR.ZS',        # Literacy rate, adult total (% of people ages 15 and above)
            'SE.PRM.NENR',           # School enrollment, primary (% net)
            'SE.SEC.NENR',           # School enrollment, secondary (% net)
            'SE.TER.ENRR',           # School enrollment, tertiary (% gross)
            
            # Saúde
            'SH.DYN.MORT',           # Mortality rate, under-5 (per 1,000 live births)
            'SH.STA.MMRT',           # Maternal mortality ratio (modeled estimate, per 100,000 live births)
            'SH.XPD.CHEX.GD.ZS',     # Current health expenditure (% of GDP)
            
            # Energia e Meio Ambiente
            'EG.USE.ELEC.KH.PC',     # Electric power consumption (kWh per capita)
            'EN.ATM.CO2E.PC',        # CO2 emissions (metric tons per capita)
            'AG.LND.FRST.ZS',        # Forest area (% of land area)
            'ER.H2O.FWTL.ZS',        # Annual freshwater withdrawals, total (% of internal resources)
            
            # Tecnologia e Inovação
            'IT.NET.USER.ZS',        # Individuals using the Internet (% of population)
            'IT.CEL.SETS.P2',        # Mobile cellular subscriptions (per 100 people)
            'GB.XPD.RSDV.GD.ZS',     # Research and development expenditure (% of GDP)
            
            # Finanças e Setor Bancário
            'FS.AST.DOMS.GD.ZS',     # Domestic credit to private sector (% of GDP)
            'FM.LBL.BMNY.GD.ZS',     # Broad money (% of GDP)
            'FR.INR.RINR',           # Real interest rate (%)
            'FS.AST.CGOV.GD.ZS',     # Claims on central government (% of GDP)
            
            # Governo e Instituições
            'GC.TAX.TOTL.GD.ZS',     # Tax revenue (% of GDP)
            'GC.XPN.TOTL.GD.ZS',     # Expense (% of GDP)
            'GC.BAL.CASH.GD.ZS',     # Cash surplus/deficit (% of GDP)
            'GC.DOD.TOTL.GD.ZS',     # Central government debt, total (% of GDP)
            
            # Pobreza e Desigualdade
            'SI.POV.DDAY',           # Poverty headcount ratio at $1.90 a day (2011 PPP) (% of population)
            'SI.POV.GINI',           # GINI index (World Bank estimate)
            'SI.DST.10TH.10',        # Income share held by highest 10%
            'SI.DST.FRST.10',        # Income share held by lowest 10%
        ]
    
    async def fetch_indicator(self, indicator: str, start_date: datetime = None,
                            end_date: datetime = None, country: str = 'WLD', **kwargs) -> PublicDataResult:
        """Busca dados de um indicador específico do World Bank."""
        if indicator not in self.supported_indicators:
            raise PublicDataException(f"Indicador {indicator} não suportado pelo World Bank")
        
        # Construir URL
        url = f"{self.base_url}/country/{country}/indicator/{indicator}"
        
        # Parâmetros da requisição
        params = {
            'format': 'json',
            'per_page': 1000  # Máximo permitido
        }
        
        # Adicionar filtro de data se fornecido
        if start_date and end_date:
            date_range = f"{start_date.year}:{end_date.year}"
            params['date'] = date_range
        elif start_date:
            params['date'] = f"{start_date.year}:{datetime.now().year}"
        elif end_date:
            params['date'] = f"1960:{end_date.year}"
        
        # Adicionar parâmetros extras
        params.update(kwargs)
        
        try:
            data = await self._make_request(url, params)
            
            # A API do World Bank retorna um array onde o primeiro elemento são metadados
            if not isinstance(data, list) or len(data) < 2:
                raise PublicDataException(f"Formato de resposta inválido para {indicator}")
            
            metadata = data[0]
            observations = data[1] if data[1] else []
            
            # Processar dados
            processed_data = []
            
            for obs in observations:
                if obs.get('value') is not None:
                    # Converter ano para data
                    year = obs.get('date')
                    if year:
                        try:
                            date_obj = datetime(int(year), 1, 1, tzinfo=timezone.utc)
                        except (ValueError, TypeError):
                            continue
                        
                        processed_data.append({
                            'date': date_obj,
                            'value': self._safe_float(obs.get('value')),
                            'country': obs.get('country', {}),
                            'countryiso3code': obs.get('countryiso3code'),
                            'decimal': obs.get('decimal'),
                            'unit': obs.get('unit')
                        })
            
            # Ordenar por data
            processed_data.sort(key=lambda x: x['date'])
            
            # Buscar metadados do indicador
            indicator_metadata = await self._fetch_indicator_metadata(indicator)
            
            return PublicDataResult(
                indicator=indicator,
                data=processed_data,
                source='world_bank',
                frequency=DataFrequency.YEARLY,  # World Bank é principalmente anual
                timestamp=datetime.now(timezone.utc),
                metadata={
                    'page': metadata.get('page'),
                    'pages': metadata.get('pages'),
                    'per_page': metadata.get('per_page'),
                    'total': metadata.get('total'),
                    'country': country,
                    'indicator_metadata': indicator_metadata
                },
                start_date=start_date,
                end_date=end_date,
                units=indicator_metadata.get('unit'),
                description=indicator_metadata.get('name')
            )
        
        except Exception as e:
            logger.error(f"Erro ao buscar dados do World Bank para {indicator}: {e}")
            raise PublicDataException(f"Falha ao buscar dados do World Bank: {e}")
    
    async def _fetch_indicator_metadata(self, indicator: str) -> Dict[str, Any]:
        """Busca metadados de um indicador."""
        url = f"{self.base_url}/indicator/{indicator}"
        params = {'format': 'json'}
        
        try:
            data = await self._make_request(url, params)
            
            if isinstance(data, list) and len(data) >= 2 and data[1]:
                return data[1][0]  # Primeiro indicador dos resultados
            
            return {}
        
        except Exception as e:
            logger.debug(f"Erro ao buscar metadados do indicador {indicator}: {e}")
            return {}
    
    async def get_countries(self) -> List[Dict[str, Any]]:
        """Obtém lista de países disponíveis."""
        url = f"{self.base_url}/country"
        params = {
            'format': 'json',
            'per_page': 500
        }
        
        try:
            data = await self._make_request(url, params)
            
            if isinstance(data, list) and len(data) >= 2:
                countries = data[1] or []
                
                return [
                    {
                        'id': country.get('id'),
                        'iso2Code': country.get('iso2Code'),
                        'name': country.get('name'),
                        'region': country.get('region', {}),
                        'adminregion': country.get('adminregion', {}),
                        'incomeLevel': country.get('incomeLevel', {}),
                        'lendingType': country.get('lendingType', {}),
                        'capitalCity': country.get('capitalCity'),
                        'longitude': country.get('longitude'),
                        'latitude': country.get('latitude')
                    }
                    for country in countries
                    if country.get('id') and country.get('name')
                ]
            
            return []
        
        except Exception as e:
            logger.error(f"Erro ao buscar países do World Bank: {e}")
            return []
    
    async def get_regions(self) -> List[Dict[str, Any]]:
        """Obtém lista de regiões disponíveis."""
        url = f"{self.base_url}/region"
        params = {
            'format': 'json',
            'per_page': 100
        }
        
        try:
            data = await self._make_request(url, params)
            
            if isinstance(data, list) and len(data) >= 2:
                regions = data[1] or []
                
                return [
                    {
                        'id': region.get('id'),
                        'code': region.get('code'),
                        'name': region.get('name')
                    }
                    for region in regions
                    if region.get('id') and region.get('name')
                ]
            
            return []
        
        except Exception as e:
            logger.error(f"Erro ao buscar regiões do World Bank: {e}")
            return []
    
    async def fetch_multiple_countries(self, indicator: str, countries: List[str],
                                     start_date: datetime = None,
                                     end_date: datetime = None) -> List[PublicDataResult]:
        """Busca dados de um indicador para múltiplos países."""
        results = []
        
        for country in countries:
            try:
                result = await self.fetch_indicator(
                    indicator, start_date, end_date, country=country
                )
                results.append(result)
            
            except Exception as e:
                logger.error(f"Erro ao buscar {indicator} para {country}: {e}")
        
        return results
    
    async def get_latest_values(self, indicators: List[str], country: str = 'WLD') -> Dict[str, Any]:
        """Obtém os valores mais recentes para uma lista de indicadores."""
        results = {}
        
        for indicator in indicators:
            try:
                # Buscar últimos 5 anos
                end_date = datetime.now(timezone.utc)
                start_date = end_date - timedelta(days=5*365)
                
                data = await self.fetch_indicator(indicator, start_date, end_date, country=country)
                
                if data.data:
                    # Pegar o valor mais recente
                    latest = max(data.data, key=lambda x: x['date'])
                    results[indicator] = {
                        'value': latest['value'],
                        'date': latest['date'],
                        'country': latest.get('country', {}),
                        'units': data.units,
                        'description': data.description
                    }
            
            except Exception as e:
                logger.error(f"Erro ao buscar valor mais recente para {indicator}: {e}")
                results[indicator] = None
        
        return results
    
    async def search_indicators(self, search_text: str) -> List[Dict[str, Any]]:
        """Busca indicadores por texto (busca local nos indicadores suportados)."""
        # Como a API do World Bank não tem busca direta, fazemos busca local
        search_lower = search_text.lower()
        
        results = []
        
        for indicator in self.supported_indicators:
            try:
                metadata = await self._fetch_indicator_metadata(indicator)
                
                name = metadata.get('name', '').lower()
                topics = str(metadata.get('topics', [])).lower()
                
                if (search_lower in indicator.lower() or 
                    search_lower in name or 
                    search_lower in topics):
                    
                    results.append({
                        'id': indicator,
                        'name': metadata.get('name'),
                        'unit': metadata.get('unit'),
                        'source': metadata.get('source', {}),
                        'topics': metadata.get('topics', []),
                        'sourceNote': metadata.get('sourceNote')
                    })
            
            except Exception as e:
                logger.debug(f"Erro ao buscar metadados para {indicator}: {e}")
        
        return results
    
    async def test_connection(self) -> bool:
        """Testa a conexão com a API do World Bank."""
        try:
            # Tentar buscar dados do PIB mundial
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=365)
            
            result = await self.fetch_indicator('NY.GDP.MKTP.CD', start_date, end_date)
            return result is not None and len(result.data) > 0
        
        except Exception as e:
            logger.error(f"Erro no teste de conexão World Bank: {e}")
            return False
    
    async def get_indicator_metadata(self, indicator: str) -> Optional[Dict[str, Any]]:
        """Obtém metadados detalhados de um indicador."""
        if indicator not in self.supported_indicators:
            return None
        
        try:
            metadata = await self._fetch_indicator_metadata(indicator)
            
            return {
                'code': indicator,
                'source': self.source_name,
                'name': metadata.get('name'),
                'unit': metadata.get('unit'),
                'source_organization': metadata.get('source', {}),
                'topics': metadata.get('topics', []),
                'sourceNote': metadata.get('sourceNote'),
                'sourceOrganization': metadata.get('sourceOrganization')
            }
        
        except Exception as e:
            logger.error(f"Erro ao buscar metadados para {indicator}: {e}")
            return None