from typing import Dict, List, Optional, Any
from datetime import datetime, timezone, timedelta
import logging

from .public_data_collector import PublicDataCollector, PublicDataResult, DataFrequency, PublicDataException
from ..cache.intelligent_cache import IntelligentCache
from ..monitoring.metrics import MetricsCollector

logger = logging.getLogger(__name__)

class BancoCentralCollector(PublicDataCollector):
    """Coletor de dados do Banco Central do Brasil (BCB)."""
    
    def __init__(self, cache: IntelligentCache, metrics: MetricsCollector):
        super().__init__(cache, metrics)
        
        # Rate limiting conservador para BCB
        self.min_request_interval = 0.5  # 500ms entre requisições
        
        logger.info("BancoCentralCollector inicializado")
    
    @property
    def base_url(self) -> str:
        """URL base da API do Banco Central do Brasil."""
        return "https://api.bcb.gov.br/dados/serie/bcdata.sgs"
    
    @property
    def source_name(self) -> str:
        """Nome da fonte de dados."""
        return "banco_central_brasil"
    
    @property
    def supported_indicators(self) -> List[str]:
        """Lista de séries temporais suportadas pelo BCB."""
        return [
            # Taxa Selic e Juros
            '432',    # Taxa Selic - % a.a.
            '4390',   # Taxa Selic - Meta definida pelo Copom
            '4189',   # Taxa de juros - DI - Over / Selic - % a.a.
            '25',     # Taxa de juros - LTN - % a.a.
            '226',    # Taxa de juros - NTN-B - % a.a.
            
            # Inflação e Índices de Preços
            '433',    # IPCA - Variação mensal - % a.m.
            '13522',  # IPCA - Variação acumulada em 12 meses - %
            '189',    # IGP-M - Variação mensal - % a.m.
            '190',    # IGP-M - Variação acumulada em 12 meses - %
            '188',    # IGP-DI - Variação mensal - % a.m.
            '193',    # IGP-DI - Variação acumulada em 12 meses - %
            '7478',   # INPC - Variação mensal - % a.m.
            '7479',   # INPC - Variação acumulada em 12 meses - %
            
            # Câmbio
            '1',      # Dólar americano (venda) - R$/US$
            '10813',  # Dólar americano (compra) - R$/US$
            '3698',   # Euro (venda) - R$/EUR
            '21619',  # Euro (compra) - R$/EUR
            '3694',   # Iene (venda) - R$/JPY
            '21621',  # Iene (compra) - R$/JPY
            '3700',   # Libra esterlina (venda) - R$/GBP
            '21623',  # Libra esterlina (compra) - R$/GBP
            
            # PIB e Atividade Econômica
            '4380',   # PIB mensal - Valores correntes (R$ milhões)
            '4381',   # PIB mensal - Variação % (mensal)
            '4382',   # PIB mensal - Variação % (interanual)
            '24364',  # IBC-Br - Índice de Atividade Econômica do BC
            '24365',  # IBC-Br - Variação mensal (%) - com ajuste sazonal
            '24366',  # IBC-Br - Variação interanual (%)
            
            # Emprego e Mercado de Trabalho
            '24369',  # Taxa de desocupação - %
            '24370',  # População na força de trabalho - Pessoas (milhões)
            '24371',  # População ocupada - Pessoas (milhões)
            '24372',  # População desocupada - Pessoas (milhões)
            
            # Setor Externo
            '22707',  # Balança comercial - Saldo - US$ milhões
            '22708',  # Exportações - US$ milhões
            '22709',  # Importações - US$ milhões
            '3546',   # Reservas internacionais - Conceito liquidez - US$ milhões
            '3547',   # Reservas internacionais - Conceito caixa - US$ milhões
            
            # Agregados Monetários
            '1785',   # M1 - R$ milhões
            '1786',   # M2 - R$ milhões
            '1787',   # M3 - R$ milhões
            '4390',   # M4 - R$ milhões
            '1636',   # Base monetária - R$ milhões
            '1637',   # Papel-moeda em poder do público - R$ milhões
            
            # Crédito
            '20542',  # Operações de crédito do SFN - Total - R$ milhões
            '20544',  # Operações de crédito - Pessoas físicas - R$ milhões
            '20545',  # Operações de crédito - Pessoas jurídicas - R$ milhões
            '20714',  # Taxa de inadimplência - Total - %
            '21082',  # Taxa de inadimplência - Pessoas físicas - %
            '21083',  # Taxa de inadimplência - Pessoas jurídicas - %
            
            # Finanças Públicas
            '5793',   # NFSP - Necessidade de financiamento do setor público - % PIB
            '4513',   # Dívida líquida do setor público - % PIB
            '4536',   # Dívida bruta do governo geral - % PIB
            '5794',   # Resultado primário do governo central - % PIB
            
            # Indicadores de Expectativas
            '4373',   # Expectativa de inflação - IPCA - 12 meses - %
            '4374',   # Expectativa de inflação - IPCA - Próximos 12 meses - %
            '4375',   # Expectativa - Taxa Selic - fim do ano - %
            '4376',   # Expectativa - Taxa de câmbio - fim do ano - R$/US$
            '4377',   # Expectativa - PIB - variação % anual
            
            # Indicadores Fiscais
            '5895',   # Receita líquida do governo central - R$ milhões
            '5896',   # Despesa total do governo central - R$ milhões
            '5897',   # Resultado nominal do governo central - R$ milhões
            '5898',   # Resultado primário do governo central - R$ milhões
            
            # Indicadores do Mercado de Capitais
            '7',      # Ibovespa - Fechamento
            '7809',   # Ibovespa - Variação % (diária)
            '7810',   # Ibovespa - Variação % (mensal)
            '7811',   # Ibovespa - Variação % (anual)
            
            # Indicadores Setoriais
            '1419',   # Produção industrial - Variação % (mensal)
            '1420',   # Produção industrial - Variação % (interanual)
            '1455',   # Vendas no varejo - Variação % (mensal)
            '1456',   # Vendas no varejo - Variação % (interanual)
            '7326',   # Confiança do consumidor - Índice
            '7327',   # Confiança da indústria - Índice
            '7328',   # Confiança dos serviços - Índice
        ]
    
    async def fetch_indicator(self, indicator: str, start_date: datetime = None,
                            end_date: datetime = None, **kwargs) -> PublicDataResult:
        """Busca dados de uma série temporal específica do BCB."""
        if indicator not in self.supported_indicators:
            raise PublicDataException(f"Série {indicator} não suportada pelo BCB")
        
        # Construir URL
        url = f"{self.base_url}/{indicator}/dados"
        
        # Parâmetros da requisição
        params = {'formato': 'json'}
        
        # Adicionar filtro de data se fornecido
        if start_date:
            params['dataInicial'] = start_date.strftime('%d/%m/%Y')
        if end_date:
            params['dataFinal'] = end_date.strftime('%d/%m/%Y')
        
        # Adicionar parâmetros extras
        params.update(kwargs)
        
        try:
            data = await self._make_request(url, params)
            
            if not isinstance(data, list):
                raise PublicDataException(f"Formato de resposta inválido para série {indicator}")
            
            # Processar dados
            processed_data = []
            
            for obs in data:
                if obs.get('valor') is not None and obs.get('valor') != '':
                    # Converter data
                    date_str = obs.get('data')
                    if date_str:
                        try:
                            # Formato esperado: DD/MM/YYYY
                            date_obj = datetime.strptime(date_str, '%d/%m/%Y')
                            date_obj = date_obj.replace(tzinfo=timezone.utc)
                        except ValueError:
                            continue
                        
                        # Converter valor
                        value = self._safe_float(obs.get('valor'))
                        if value is not None:
                            processed_data.append({
                                'date': date_obj,
                                'value': value,
                                'original_data': date_str
                            })
            
            # Ordenar por data
            processed_data.sort(key=lambda x: x['date'])
            
            # Buscar metadados da série
            series_metadata = await self._fetch_series_metadata(indicator)
            
            # Determinar frequência baseada nos dados
            frequency = self._determine_frequency(processed_data)
            
            return PublicDataResult(
                indicator=indicator,
                data=processed_data,
                source='banco_central_brasil',
                frequency=frequency,
                timestamp=datetime.now(timezone.utc),
                metadata={
                    'series_code': indicator,
                    'series_metadata': series_metadata,
                    'total_observations': len(processed_data)
                },
                start_date=start_date,
                end_date=end_date,
                units=series_metadata.get('unidadeMedida'),
                description=series_metadata.get('nomeCompleto')
            )
        
        except Exception as e:
            logger.error(f"Erro ao buscar dados do BCB para série {indicator}: {e}")
            raise PublicDataException(f"Falha ao buscar dados do BCB: {e}")
    
    async def _fetch_series_metadata(self, series_code: str) -> Dict[str, Any]:
        """Busca metadados de uma série temporal."""
        url = f"https://api.bcb.gov.br/dados/serie/bcdata.sgs/{series_code}"
        
        try:
            data = await self._make_request(url, {})
            
            if isinstance(data, dict):
                return data
            
            return {}
        
        except Exception as e:
            logger.debug(f"Erro ao buscar metadados da série {series_code}: {e}")
            return {}
    
    def _determine_frequency(self, data: List[Dict]) -> DataFrequency:
        """Determina a frequência dos dados baseada no intervalo entre observações."""
        if len(data) < 2:
            return DataFrequency.UNKNOWN
        
        # Calcular intervalos entre datas
        intervals = []
        for i in range(1, min(10, len(data))):
            interval = (data[i]['date'] - data[i-1]['date']).days
            intervals.append(interval)
        
        if not intervals:
            return DataFrequency.UNKNOWN
        
        avg_interval = sum(intervals) / len(intervals)
        
        # Classificar frequência baseada no intervalo médio
        if avg_interval <= 1:
            return DataFrequency.DAILY
        elif avg_interval <= 7:
            return DataFrequency.WEEKLY
        elif avg_interval <= 31:
            return DataFrequency.MONTHLY
        elif avg_interval <= 93:
            return DataFrequency.QUARTERLY
        elif avg_interval <= 366:
            return DataFrequency.YEARLY
        else:
            return DataFrequency.UNKNOWN
    
    async def get_latest_values(self, indicators: List[str]) -> Dict[str, Any]:
        """Obtém os valores mais recentes para uma lista de séries."""
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
                logger.error(f"Erro ao buscar valor mais recente para série {indicator}: {e}")
                results[indicator] = None
        
        return results
    
    async def get_economic_indicators(self) -> Dict[str, Any]:
        """Obtém principais indicadores econômicos brasileiros."""
        key_indicators = [
            '432',    # Taxa Selic
            '433',    # IPCA mensal
            '13522',  # IPCA 12 meses
            '1',      # Dólar
            '24364',  # IBC-Br
            '24369',  # Taxa de desocupação
        ]
        
        return await self.get_latest_values(key_indicators)
    
    async def get_exchange_rates(self) -> Dict[str, Any]:
        """Obtém taxas de câmbio atuais."""
        exchange_indicators = [
            '1',      # Dólar (venda)
            '10813',  # Dólar (compra)
            '3698',   # Euro (venda)
            '21619',  # Euro (compra)
            '3694',   # Iene (venda)
            '3700',   # Libra (venda)
        ]
        
        return await self.get_latest_values(exchange_indicators)
    
    async def get_interest_rates(self) -> Dict[str, Any]:
        """Obtém taxas de juros atuais."""
        interest_indicators = [
            '432',    # Taxa Selic
            '4390',   # Meta Selic
            '4189',   # DI Over
            '25',     # LTN
            '226',    # NTN-B
        ]
        
        return await self.get_latest_values(interest_indicators)
    
    async def get_inflation_data(self) -> Dict[str, Any]:
        """Obtém dados de inflação atuais."""
        inflation_indicators = [
            '433',    # IPCA mensal
            '13522',  # IPCA 12 meses
            '189',    # IGP-M mensal
            '190',    # IGP-M 12 meses
            '7478',   # INPC mensal
            '7479',   # INPC 12 meses
        ]
        
        return await self.get_latest_values(inflation_indicators)
    
    async def search_series(self, search_text: str) -> List[Dict[str, Any]]:
        """Busca séries por texto (busca local nas séries suportadas)."""
        # Mapeamento de códigos para descrições (simplificado)
        series_descriptions = {
            '432': 'Taxa Selic',
            '433': 'IPCA - Variação mensal',
            '13522': 'IPCA - Variação acumulada 12 meses',
            '1': 'Dólar americano (venda)',
            '24364': 'IBC-Br - Índice de Atividade Econômica',
            '24369': 'Taxa de desocupação',
            # Adicionar mais conforme necessário
        }
        
        search_lower = search_text.lower()
        results = []
        
        for series_code in self.supported_indicators:
            description = series_descriptions.get(series_code, f"Série {series_code}")
            
            if (search_lower in series_code.lower() or 
                search_lower in description.lower()):
                
                # Buscar metadados se disponível
                metadata = await self._fetch_series_metadata(series_code)
                
                results.append({
                    'code': series_code,
                    'description': description,
                    'metadata': metadata
                })
        
        return results
    
    async def test_connection(self) -> bool:
        """Testa a conexão com a API do BCB."""
        try:
            # Tentar buscar dados da Taxa Selic (série mais estável)
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=30)
            
            result = await self.fetch_indicator('432', start_date, end_date)
            return result is not None and len(result.data) > 0
        
        except Exception as e:
            logger.error(f"Erro no teste de conexão BCB: {e}")
            return False
    
    async def get_series_metadata(self, series_code: str) -> Optional[Dict[str, Any]]:
        """Obtém metadados detalhados de uma série."""
        if series_code not in self.supported_indicators:
            return None
        
        try:
            metadata = await self._fetch_series_metadata(series_code)
            
            return {
                'code': series_code,
                'source': self.source_name,
                'metadata': metadata
            }
        
        except Exception as e:
            logger.error(f"Erro ao buscar metadados para série {series_code}: {e}")
            return None
    
    async def fetch_multiple_series(self, series_codes: List[str],
                                  start_date: datetime = None,
                                  end_date: datetime = None) -> List[PublicDataResult]:
        """Busca dados de múltiplas séries."""
        results = []
        
        for series_code in series_codes:
            try:
                result = await self.fetch_indicator(series_code, start_date, end_date)
                results.append(result)
            
            except Exception as e:
                logger.error(f"Erro ao buscar série {series_code}: {e}")
        
        return results