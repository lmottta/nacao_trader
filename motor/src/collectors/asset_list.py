"""
Lista de ativos para coleta de dados.

Este módulo define todos os ativos suportados para coleta de dados em tempo real,
incluindo símbolos e descrições.
"""
from typing import Dict, List, Optional, Tuple

# Símbolos organizados por categoria
# Formato: 
# CATEGORIA: List[Tuple[símbolo, nome, descrição]]

# Ações
STOCKS = [
    # Principais ações dos EUA
    ("AAPL", "Apple Inc.", "Empresa de tecnologia e fabricante do iPhone"),
    ("MSFT", "Microsoft Corporation", "Empresa de software e serviços de nuvem"),
    ("AMZN", "Amazon.com Inc.", "Comércio eletrônico e serviços de nuvem"),
    ("GOOGL", "Alphabet Inc. (Google)", "Motores de busca e tecnologia"),
    ("META", "Meta Platforms Inc.", "Redes sociais e realidade virtual"),
    ("TSLA", "Tesla Inc.", "Veículos elétricos e energia limpa"),
    ("NVDA", "NVIDIA Corporation", "Semicondutores e chips gráficos"),
    ("JPM", "JPMorgan Chase & Co.", "Banco e serviços financeiros"),
    ("V", "Visa Inc.", "Processamento de pagamentos"),
    ("WMT", "Walmart Inc.", "Varejo e e-commerce"),
    
    # Ações brasileiras
    ("PETR4.SA", "Petrobras PN", "Petróleo e gás"),
    ("VALE3.SA", "Vale SA", "Mineração"),
    ("ITUB4.SA", "Itaú Unibanco PN", "Banco e serviços financeiros"),
    ("BBDC4.SA", "Bradesco PN", "Banco e serviços financeiros"),
    ("ABEV3.SA", "Ambev SA", "Bebidas"),
    ("B3SA3.SA", "B3 SA", "Bolsa de valores"),
    ("WEGE3.SA", "WEG SA", "Equipamentos elétricos"),
    
    # Ações europeias
    ("SAP.DE", "SAP SE", "Software e serviços de TI"),
    ("ASML.AS", "ASML Holding", "Equipamentos para semicondutores"),
    ("LVMH.PA", "LVMH Moët Hennessy", "Produtos de luxo"),
    
    # Ativos solicitados específicos
    ("FTT-USD", "FTX Token", "Token nativo da exchange FTX"),
    ("5ST.L", "Five Star Travel & Tour", "Turismo e viagens"),
    ("DRT.L", "Directa Plus", "Materiais avançados e tecnologia de grafeno"),
]

# Índices
INDICES = [
    ("^GSPC", "S&P 500", "Índice das 500 maiores empresas dos EUA"),
    ("^DJI", "Dow Jones Industrial Average", "Índice de 30 grandes empresas dos EUA"),
    ("^IXIC", "NASDAQ Composite", "Índice de empresas de tecnologia"),
    ("^BVSP", "Ibovespa", "Principal índice da B3 (Brasil)"),
    ("^FTSE", "FTSE 100", "Índice das 100 maiores empresas do Reino Unido"),
    ("^GDAXI", "DAX", "Índice da bolsa de Frankfurt (Alemanha)"),
    ("^N225", "Nikkei 225", "Principal índice da bolsa de Tóquio (Japão)"),
]

# Forex (moedas)
FOREX = [
    ("EURUSD=X", "EUR/USD", "Euro / Dólar Americano"),
    ("GBPUSD=X", "GBP/USD", "Libra Esterlina / Dólar Americano"),
    ("USDJPY=X", "USD/JPY", "Dólar Americano / Iene Japonês"),
    ("USDCAD=X", "USD/CAD", "Dólar Americano / Dólar Canadense"),
    ("AUDUSD=X", "AUD/USD", "Dólar Australiano / Dólar Americano"),
    ("USDBRL=X", "USD/BRL", "Dólar Americano / Real Brasileiro"),
]

# Criptomoedas
CRYPTO = [
    ("BTC-USD", "Bitcoin", "Moeda digital descentralizada"),
    ("ETH-USD", "Ethereum", "Plataforma para contratos inteligentes"),
    ("XRP-USD", "XRP", "Criptomoeda da Ripple"),
    ("ADA-USD", "Cardano", "Plataforma blockchain de prova de participação"),
    ("SOL-USD", "Solana", "Blockchain de alta performance"),
    ("DOT-USD", "Polkadot", "Rede multicadeia"),
    ("DOGE-USD", "Dogecoin", "Criptomoeda baseada em meme"),
]

# Contratos por Diferença (CFDs)
CFDS = [
    # Commodities
    ("GC=F", "Gold", "Ouro - Future"),
    ("SI=F", "Silver", "Prata - Future"),
    ("CL=F", "Crude Oil", "Petróleo - Future"),
    ("NG=F", "Natural Gas", "Gás Natural - Future"),
    
    # Outros CFDs
    ("ES=F", "E-mini S&P 500", "Future do S&P 500"),
    ("YM=F", "Mini Dow Jones", "Future do Dow Jones"),
    ("NQ=F", "E-mini NASDAQ", "Future do NASDAQ"),
]

# Juntar todas as categorias
ALL_ASSETS = STOCKS + INDICES + FOREX + CRYPTO + CFDS

# Função para obter ativos de uma categoria específica
def get_assets_by_category(category: str) -> List[Tuple[str, str, str]]:
    """Retorna a lista de ativos de uma categoria específica.
    
    Args:
        category: Categoria dos ativos ('stocks', 'indices', 'forex', 'crypto', 'cfds')
    
    Returns:
        Lista de tuplas (símbolo, nome, descrição)
    """
    category = category.lower()
    if category == 'stocks':
        return STOCKS
    elif category == 'indices':
        return INDICES
    elif category == 'forex':
        return FOREX
    elif category == 'crypto':
        return CRYPTO
    elif category == 'cfds':
        return CFDS
    elif category == 'all':
        return ALL_ASSETS
    else:
        raise ValueError(f"Categoria desconhecida: {category}")

# Obter apenas os símbolos de uma categoria
def get_symbols_by_category(category: str) -> List[str]:
    """Retorna apenas os símbolos dos ativos de uma categoria.
    
    Args:
        category: Categoria dos ativos ('stocks', 'indices', 'forex', 'crypto', 'cfds')
    
    Returns:
        Lista de símbolos
    """
    assets = get_assets_by_category(category)
    return [asset[0] for asset in assets]

# Converter símbolo Yahoo Finance para formato da API
def get_api_symbol(yahoo_symbol: str) -> str:
    """Converte símbolo do Yahoo Finance para formato da API.
    
    Alguns símbolos precisam de conversão para uso em outras APIs.
    
    Args:
        yahoo_symbol: Símbolo no formato Yahoo Finance
    
    Returns:
        Símbolo no formato da API
    """
    # Remover sufixos específicos do Yahoo
    if yahoo_symbol.endswith("=X"):
        # Converter formato Forex do Yahoo (EURUSD=X) para formato usual (EUR/USD)
        base = yahoo_symbol[0:3]
        quote = yahoo_symbol[3:6]
        return f"{base}/{quote}"
    elif yahoo_symbol.endswith(".SA"):
        # Remover sufixo Brasil para API local
        return yahoo_symbol.replace(".SA", "")
    else:
        return yahoo_symbol

# Pesquisar um ativo por termo (símbolo ou nome)
def search_assets(term: str) -> List[Tuple[str, str, str]]:
    """Pesquisa ativos por símbolo ou nome.
    
    Args:
        term: Termo de pesquisa (parte do símbolo ou nome)
    
    Returns:
        Lista de tuplas (símbolo, nome, descrição) que correspondem ao termo
    """
    term = term.lower()
    results = []
    
    for asset in ALL_ASSETS:
        symbol, name, desc = asset
        if term in symbol.lower() or term in name.lower():
            results.append(asset)
    
    return results

# Obter informações de um ativo específico
def get_asset_info(symbol: str) -> Optional[Tuple[str, str, str]]:
    """Retorna informações de um ativo específico.
    
    Args:
        symbol: Símbolo do ativo
    
    Returns:
        Tupla (símbolo, nome, descrição) ou None se não encontrado
    """
    for asset in ALL_ASSETS:
        if asset[0] == symbol:
            return asset
    return None 