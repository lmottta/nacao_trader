"""Sistema Principal Integrado - Fase 2 do Nação Trader.

Este módulo integra todos os componentes da Fase 2:
- Web Scraping
- WebSockets
- Dados Públicos
- Validação Cruzada
- Sistema de Fallback
- Rate Limiting Inteligente
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from loguru import logger

# Adicionar o diretório raiz ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.collectors.collector_manager import get_collector_manager, CollectorType
from src.utils.config import settings
from src.monitoring.metrics import get_metrics_collector
from src.cache.intelligent_cache import get_cache
from src.resilience.fallback_system import get_fallback_system


class IntegratedSystem:
    """Sistema integrado que coordena todos os componentes da Fase 2."""
    
    def __init__(self):
        self.collector_manager = None
        self.metrics = None
        self.cache = None
        self.fallback_system = None
        self.is_running = False
        
    async def initialize(self):
        """Inicializa todos os componentes do sistema."""
        try:
            logger.info("Inicializando Sistema Integrado - Fase 2")
            
            # Inicializar componentes principais
            self.collector_manager = await get_collector_manager()
            
            self.metrics = get_metrics_collector()
            self.cache = await get_cache()
            self.fallback_system = await get_fallback_system()
            
            # Configurar coletores da Fase 2
            await self._configure_phase2_collectors()
            
            logger.info("Sistema Integrado inicializado com sucesso")
            
        except Exception as e:
            logger.error(f"Erro na inicialização do sistema: {e}")
            raise
    
    async def _configure_phase2_collectors(self):
        """Configura todos os coletores da Fase 2."""
        try:
            # Habilitar todos os coletores
            collectors_to_enable = [
                CollectorType.YAHOO_FINANCE,
                CollectorType.FINNHUB,
                CollectorType.REALTIME,
                CollectorType.WEB_SCRAPING,
                CollectorType.BINANCE_WEBSOCKET,
                CollectorType.FRED,
                CollectorType.BANCO_CENTRAL
            ]
            
            for collector_type in collectors_to_enable:
                try:
                    await self.collector_manager.enable_collector(collector_type)
                    logger.info(f"Coletor {collector_type.value} habilitado")
                except Exception as e:
                    logger.warning(f"Erro ao habilitar coletor {collector_type.value}: {e}")
            
            # Habilitar validação cruzada
            await self.collector_manager.enable_validation()
            
            # Habilitar sistema de fallback
            await self.collector_manager.enable_fallback()
            
            logger.info("Configuração dos coletores da Fase 2 concluída")
            
        except Exception as e:
            logger.error(f"Erro na configuração dos coletores: {e}")
            raise
    
    async def collect_comprehensive_data(self, symbols: List[str]) -> Dict[str, Any]:
        """Coleta dados abrangentes usando todos os coletores disponíveis."""
        try:
            logger.info(f"Iniciando coleta abrangente para {len(symbols)} símbolos")
            
            results = {}
            
            # Coletar dados de múltiplas fontes
            for symbol in symbols:
                symbol_results = {}
                
                # Yahoo Finance (dados históricos)
                try:
                    yahoo_data = await self.collector_manager.collect_data(
                        CollectorType.YAHOO_FINANCE,
                        symbol=symbol,
                        period="1y",
                        interval="1d"
                    )
                    symbol_results['yahoo_finance'] = yahoo_data
                except Exception as e:
                    logger.warning(f"Erro ao coletar dados do Yahoo Finance para {symbol}: {e}")
                
                # Finnhub (dados fundamentais)
                try:
                    finnhub_data = await self.collector_manager.collect_data(
                        CollectorType.FINNHUB,
                        symbol=symbol
                    )
                    symbol_results['finnhub'] = finnhub_data
                except Exception as e:
                    logger.warning(f"Erro ao coletar dados do Finnhub para {symbol}: {e}")
                
                # Web Scraping (notícias e sentimentos)
                try:
                    scraping_data = await self.collector_manager.collect_data(
                        CollectorType.WEB_SCRAPING,
                        symbol=symbol,
                        data_type="news"
                    )
                    symbol_results['web_scraping'] = scraping_data
                except Exception as e:
                    logger.warning(f"Erro ao coletar dados de web scraping para {symbol}: {e}")
                
                # Dados em tempo real (se disponível)
                try:
                    realtime_data = await self.collector_manager.collect_data(
                        CollectorType.REALTIME,
                        symbol=symbol
                    )
                    symbol_results['realtime'] = realtime_data
                except Exception as e:
                    logger.warning(f"Erro ao coletar dados em tempo real para {symbol}: {e}")
                
                results[symbol] = symbol_results
            
            logger.info(f"Coleta abrangente concluída para {len(symbols)} símbolos")
            return results
            
        except Exception as e:
            logger.error(f"Erro na coleta abrangente: {e}")
            raise
    
    async def collect_economic_indicators(self) -> Dict[str, Any]:
        """Coleta indicadores econômicos de fontes públicas."""
        try:
            logger.info("Iniciando coleta de indicadores econômicos")
            
            results = {}
            
            # FRED (Federal Reserve Economic Data)
            try:
                fred_indicators = [
                    "GDP",  # PIB
                    "UNRATE",  # Taxa de desemprego
                    "FEDFUNDS",  # Taxa de juros federal
                    "CPIAUCSL",  # Índice de preços ao consumidor
                    "DGS10"  # Taxa de títulos do tesouro 10 anos
                ]
                
                for indicator in fred_indicators:
                    try:
                        fred_data = await self.collector_manager.collect_data(
                            CollectorType.FRED,
                            series_id=indicator,
                            start_date=(datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
                        )
                        results[f'fred_{indicator}'] = fred_data
                    except Exception as e:
                        logger.warning(f"Erro ao coletar indicador FRED {indicator}: {e}")
            
            except Exception as e:
                logger.warning(f"Erro geral na coleta FRED: {e}")
            
            # Banco Central do Brasil
            try:
                bc_indicators = [
                    "432",  # Taxa Selic
                    "433",  # IPCA
                    "1",    # Taxa de câmbio USD/BRL
                ]
                
                for indicator in bc_indicators:
                    try:
                        bc_data = await self.collector_manager.collect_data(
                            CollectorType.BANCO_CENTRAL,
                            series_code=indicator,
                            start_date=(datetime.now() - timedelta(days=365)).strftime("%d/%m/%Y")
                        )
                        results[f'bc_{indicator}'] = bc_data
                    except Exception as e:
                        logger.warning(f"Erro ao coletar indicador BC {indicator}: {e}")
            
            except Exception as e:
                logger.warning(f"Erro geral na coleta Banco Central: {e}")
            
            logger.info(f"Coleta de indicadores econômicos concluída. {len(results)} indicadores coletados")
            return results
            
        except Exception as e:
            logger.error(f"Erro na coleta de indicadores econômicos: {e}")
            return {}
    
    async def start_continuous_collection(self, interval_minutes: int = 60):
        """Inicia coleta contínua de dados."""
        try:
            logger.info(f"Iniciando coleta contínua com intervalo de {interval_minutes} minutos")
            
            self.is_running = True
            
            # Símbolos principais para monitoramento
            main_symbols = [
                "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA",  # Tech
                "SPY", "QQQ", "IWM",  # ETFs
                "EURUSD=X", "GBPUSD=X", "USDJPY=X",  # Forex
                "GC=F", "CL=F", "BTC-USD"  # Commodities e Crypto
            ]
            
            while self.is_running:
                try:
                    # Coletar dados abrangentes
                    await self.collect_comprehensive_data(main_symbols)
                    
                    # Coletar indicadores econômicos (menos frequente)
                    if datetime.now().hour % 6 == 0:  # A cada 6 horas
                        await self.collect_economic_indicators()
                    
                    # Obter status do sistema
                    status = await self.get_system_status()
                    logger.info(f"Status do sistema: {status['summary']}")
                    
                    # Aguardar próximo ciclo
                    await asyncio.sleep(interval_minutes * 60)
                    
                except Exception as e:
                    logger.error(f"Erro no ciclo de coleta contínua: {e}")
                    await asyncio.sleep(300)  # Aguardar 5 minutos antes de tentar novamente
            
        except Exception as e:
            logger.error(f"Erro na coleta contínua: {e}")
            raise
    
    def stop_continuous_collection(self):
        """Para a coleta contínua."""
        self.is_running = False
        logger.info("Coleta contínua interrompida")
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Obtém status completo do sistema."""
        try:
            # Status do CollectorManager
            orchestration_status = await self.collector_manager.get_orchestration_status()
            
            # Métricas do sistema
            system_metrics = self.metrics.get_system_metrics()
            
            # Status do cache
            cache_stats = self.cache.get_stats()
            
            # Status do fallback
            fallback_status = await self.fallback_system.get_fallback_status()
            
            return {
                "timestamp": datetime.now().isoformat(),
                "orchestration": orchestration_status,
                "system_metrics": system_metrics,
                "cache_stats": cache_stats,
                "fallback_status": fallback_status,
                "summary": {
                    "total_collectors": len(orchestration_status.get("collectors", {})),
                    "active_collectors": len([c for c in orchestration_status.get("collectors", {}).values() if c.get("status") == "running"]),
                    "cache_hit_rate": cache_stats.get("hit_rate", 0),
                    "fallback_sources": len(fallback_status.get("sources", [])),
                    "system_health": "healthy" if system_metrics.get("cpu_percent", 0) < 80 else "warning"
                }
            }
            
        except Exception as e:
            logger.error(f"Erro ao obter status do sistema: {e}")
            return {"error": str(e)}
    
    async def close(self):
        """Encerra o sistema de forma limpa."""
        try:
            logger.info("Encerrando Sistema Integrado")
            
            self.stop_continuous_collection()
            
            if self.collector_manager:
                await self.collector_manager.close()
            
            if self.fallback_system:
                await self.fallback_system.close()
            
            logger.info("Sistema Integrado encerrado com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao encerrar sistema: {e}")


# Instância global do sistema
_integrated_system: Optional[IntegratedSystem] = None


def get_integrated_system() -> IntegratedSystem:
    """Obtém a instância global do sistema integrado."""
    global _integrated_system
    if _integrated_system is None:
        _integrated_system = IntegratedSystem()
    return _integrated_system


async def close_integrated_system():
    """Encerra a instância global do sistema integrado."""
    global _integrated_system
    if _integrated_system:
        await _integrated_system.close()
        _integrated_system = None


async def main():
    """Função principal para execução do sistema integrado."""
    # Configurar logger
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level=settings.LOG_LEVEL,
    )
    logger.add(
        "logs/integrated_system.log",
        rotation="10 MB",
        retention="1 week",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        level=settings.LOG_LEVEL,
    )
    
    # Criar diretório de logs
    os.makedirs("logs", exist_ok=True)
    
    # Inicializar sistema
    system = get_integrated_system()
    
    try:
        await system.initialize()
        
        # Verificar argumentos de linha de comando
        if len(sys.argv) > 1:
            if sys.argv[1] == "status":
                # Mostrar status do sistema
                status = await system.get_system_status()
                print("\n=== STATUS DO SISTEMA INTEGRADO ===")
                if 'error' in status:
                    print(f"Erro: {status['error']}")
                else:
                    print(f"Timestamp: {status.get('timestamp', 'N/A')}")
                    summary = status.get('summary', {})
                    print(f"Coletores Ativos: {summary.get('active_collectors', 0)}/{summary.get('total_collectors', 0)}")
                    print(f"Taxa de Hit do Cache: {summary.get('cache_hit_rate', 0):.2%}")
                    print(f"Fontes de Fallback: {summary.get('fallback_sources', 0)}")
                    print(f"Saúde do Sistema: {summary.get('system_health', 'unknown')}")
                
            elif sys.argv[1] == "collect":
                # Executar coleta única
                symbols = ["AAPL", "MSFT", "GOOGL", "SPY", "EURUSD=X"]
                results = await system.collect_comprehensive_data(symbols)
                logger.info(f"Coleta única concluída para {len(results)} símbolos")
                
            elif sys.argv[1] == "economic":
                # Coletar indicadores econômicos
                indicators = await system.collect_economic_indicators()
                logger.info(f"Coleta de indicadores econômicos concluída: {len(indicators)} indicadores")
                
            elif sys.argv[1] == "continuous":
                # Executar coleta contínua
                interval = int(sys.argv[2]) if len(sys.argv) > 2 else 60
                await system.start_continuous_collection(interval)
                
            else:
                logger.error(f"Argumento inválido: {sys.argv[1]}")
                logger.info("Uso: python -m src.main_integrated [status|collect|economic|continuous] [interval_minutes]")
        else:
            # Por padrão, mostrar status
            status = await system.get_system_status()
            logger.info(f"Sistema inicializado. Status: {status['summary']}")
    
    except KeyboardInterrupt:
        logger.info("Interrupção pelo usuário")
    except Exception as e:
        logger.error(f"Erro na execução: {e}")
    finally:
        await close_integrated_system()


if __name__ == "__main__":
    asyncio.run(main())