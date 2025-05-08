#!/usr/bin/env python
# motor/scripts/simplified_fetch_assets.py

import os
import json
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# Carregar variáveis de ambiente do .env na pasta motor/
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

# Diretório de cache
CACHE_DIR = os.path.join(os.path.dirname(__file__), '..', 'cache')
os.makedirs(CACHE_DIR, exist_ok=True)

# Ativos essenciais para um trader (independente de API)
ESSENTIAL_ASSETS = [
    # Ações de alta liquidez dos EUA (Blue Chips)
    {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "asset_type": "stock",
        "description": "Empresa líder em tecnologia conhecida por iPhones, MacBooks e serviços digitais.",
        "ticker": "AAPL",
        "active": True,
        "currency": "USD",
        "last_price": 191.45,
        "market_status": "open"
    },
    {
        "symbol": "MSFT",
        "name": "Microsoft Corporation",
        "asset_type": "stock",
        "description": "Gigante de software e serviços em nuvem, incluindo Office 365 e Azure.",
        "ticker": "MSFT",
        "active": True,
        "currency": "USD",
        "last_price": 416.38,
        "market_status": "open"
    },
    {
        "symbol": "NVDA",
        "name": "NVIDIA Corporation",
        "asset_type": "stock",
        "description": "Líder em GPUs avançadas usadas em IA, jogos e data centers.",
        "ticker": "NVDA",
        "active": True,
        "currency": "USD",
        "last_price": 116.21,
        "market_status": "open"
    },
    {
        "symbol": "AMZN",
        "name": "Amazon.com, Inc.",
        "asset_type": "stock",
        "description": "Maior varejista online do mundo e líder em serviços de nuvem AWS.",
        "ticker": "AMZN",
        "active": True,
        "currency": "USD",
        "last_price": 177.23,
        "market_status": "open"
    },
    {
        "symbol": "GOOGL",
        "name": "Alphabet Inc.",
        "asset_type": "stock",
        "description": "Empresa controladora do Google, YouTube e outros serviços digitais.",
        "ticker": "GOOGL",
        "active": True,
        "currency": "USD",
        "last_price": 163.42,
        "market_status": "open"
    },
    
    # Ações brasileiras importantes
    {
        "symbol": "PETR4.SA",
        "name": "Petrobras PN",
        "asset_type": "stock",
        "description": "Maior empresa de petróleo e gás do Brasil e uma das maiores do mundo.",
        "ticker": "PETR4.SA",
        "active": True,
        "currency": "BRL",
        "last_price": 38.95,
        "market_status": "open"
    },
    {
        "symbol": "VALE3.SA",
        "name": "Vale ON",
        "asset_type": "stock",
        "description": "Uma das maiores mineradoras do mundo, líder na produção de minério de ferro.",
        "ticker": "VALE3.SA",
        "active": True,
        "currency": "BRL",
        "last_price": 68.72,
        "market_status": "open"
    },
    {
        "symbol": "ITUB4.SA",
        "name": "Itaú Unibanco PN",
        "asset_type": "stock",
        "description": "Maior banco privado da América Latina, com forte presença no Brasil.",
        "ticker": "ITUB4.SA",
        "active": True,
        "currency": "BRL",
        "last_price": 33.44,
        "market_status": "open"
    },
    
    # As principais criptomoedas
    {
        "symbol": "BTC-USD",
        "name": "Bitcoin/USD",
        "asset_type": "crypto",
        "description": "A primeira e mais valiosa criptomoeda do mercado, criada em 2009.",
        "ticker": "BTC-USD",
        "active": True,
        "currency": "USD",
        "last_price": 67523.42,
        "market_status": "open"
    },
    {
        "symbol": "ETH-USD",
        "name": "Ethereum/USD",
        "asset_type": "crypto",
        "description": "Blockchain de contratos inteligentes que permite aplicações descentralizadas.",
        "ticker": "ETH-USD",
        "active": True,
        "currency": "USD",
        "last_price": 3415.65,
        "market_status": "open"
    },
    {
        "symbol": "SOL-USD",
        "name": "Solana/USD",
        "asset_type": "crypto",
        "description": "Blockchain de alta performance para DeFi, NFTs e aplicações escaláveis.",
        "ticker": "SOL-USD",
        "active": True, 
        "currency": "USD",
        "last_price": 149.87,
        "market_status": "open"
    },
    
    # Principais pares de forex
    {
        "symbol": "EURUSD=X",
        "name": "EUR/USD",
        "asset_type": "forex",
        "description": "Principal par de moedas do mundo, Euro contra Dólar Americano.",
        "ticker": "EURUSD=X",
        "active": True,
        "currency": "USD",
        "last_price": 1.0895,
        "market_status": "open"
    },
    {
        "symbol": "GBPUSD=X",
        "name": "GBP/USD",
        "asset_type": "forex",
        "description": "Libra Esterlina contra Dólar Americano, conhecido como 'Cable'.",
        "ticker": "GBPUSD=X",
        "active": True,
        "currency": "USD",
        "last_price": 1.2734,
        "market_status": "open"
    },
    {
        "symbol": "USDJPY=X",
        "name": "USD/JPY",
        "asset_type": "forex",
        "description": "Dólar Americano contra Iene Japonês, um dos pares mais negociados.",
        "ticker": "USDJPY=X",
        "active": True,
        "currency": "JPY",
        "last_price": 153.28,
        "market_status": "open"
    },
    {
        "symbol": "USDBRL=X",
        "name": "USD/BRL",
        "asset_type": "forex",
        "description": "Dólar Americano contra Real Brasileiro, par importante para o Brasil.",
        "ticker": "USDBRL=X",
        "active": True,
        "currency": "BRL",
        "last_price": 5.1245,
        "market_status": "open"
    }
]

def init_supabase():
    """Inicializa o cliente Supabase"""
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        print("✓ Cliente Supabase inicializado com sucesso.")
        return supabase
    except Exception as e:
        print(f"✗ Erro ao inicializar cliente Supabase: {e}")
        exit(1)

def load_from_cache():
    """Carrega todos os dados de ativos do cache local"""
    assets = []
    cache_files = list(Path(CACHE_DIR).glob('*.json'))
    
    print(f"Encontrados {len(cache_files)} arquivos de cache.")
    
    for cache_file in cache_files:
        if "failed_tickers" in cache_file.name:
            continue  # Pular o arquivo de falhas
        
        try:
            with open(cache_file, 'r') as f:
                asset_data = json.load(f)
                assets.append(asset_data)
        except Exception as e:
            print(f"✗ Erro ao carregar {cache_file.name}: {e}")
    
    print(f"Carregados {len(assets)} ativos do cache.")
    return assets

def insert_in_batches(supabase, assets, batch_size=3):
    """Insere os ativos em lotes pequenos"""
    total_count = len(assets)
    successful = 0
    failed = 0
    
    # Atualizar timestamp em todos os ativos
    now = datetime.now().isoformat()
    for asset in assets:
        asset["last_update"] = now
        asset["last_status_update"] = now
    
    # Dividir em lotes
    for i in range(0, total_count, batch_size):
        batch = assets[i:i+batch_size]
        print(f"\nProcessando lote {i//batch_size + 1}/{(total_count + batch_size - 1)//batch_size} ({len(batch)} ativos)")
        
        try:
            response = supabase.table('assets').upsert(batch, on_conflict='symbol').execute()
            print(f"✓ Lote inserido com sucesso!")
            successful += len(batch)
        except Exception as e:
            print(f"✗ Erro ao inserir lote: {e}")
            failed += len(batch)
        
        # Pequena pausa entre lotes
        if i + batch_size < total_count:
            time.sleep(1)
    
    print(f"\nInserção concluída: {successful} bem-sucedidos, {failed} falhas.")
    return successful, failed

def ensure_seed_assets(supabase):
    """Garante que ativos essenciais existam na tabela"""
    try:
        # Verificar quantos ativos essenciais já existem
        response = supabase.table('assets').select('symbol').in_('symbol', [a['symbol'] for a in ESSENTIAL_ASSETS]).execute()
        existing = response.data
        existing_symbols = [a['symbol'] for a in existing]
        
        # Filtrar apenas ativos que não existem
        missing_assets = [a for a in ESSENTIAL_ASSETS if a['symbol'] not in existing_symbols]
        
        if missing_assets:
            print(f"\n📊 Adicionando {len(missing_assets)} ativos essenciais para traders...")
            insert_in_batches(supabase, missing_assets)
            print("✅ Ativos essenciais adicionados com sucesso!")
        else:
            print("\n✅ Todos os ativos essenciais já estão presentes no banco.")
            
    except Exception as e:
        print(f"❌ Erro ao verificar/adicionar ativos essenciais: {e}")

def main():
    print("\n=== IMPORTAÇÃO SIMPLIFICADA DE ATIVOS ===")
    print("Este script garante que os ativos essenciais de trading estejam disponíveis.")
    
    # Inicializar Supabase
    supabase = init_supabase()
    
    # Primeiro garantir que ativos essenciais existam
    ensure_seed_assets(supabase)
    
    # Tentar carregar dados do cache se existirem
    cached_assets = load_from_cache()
    
    if cached_assets:
        print(f"\nEncontrados {len(cached_assets)} ativos adicionais no cache.")
        confirm = input("Deseja adicionar estes ativos também? (s/N): ").lower() == 's'
        
        if confirm:
            # Inserir dados do cache
            start_time = time.time()
            insert_in_batches(supabase, cached_assets)
            end_time = time.time()
            print(f"\nTempo total de execução: {end_time - start_time:.2f} segundos.")
    else:
        print("\nNenhum ativo adicional encontrado no cache.")
        print("Apenas os ativos essenciais foram garantidos.")
    
    print("\n✅ Operação concluída com sucesso!")
    print("Agora o sistema deve mostrar ativos nas telas de Favoritos, Sinais e Lista de Ativos.")

if __name__ == "__main__":
    main() 