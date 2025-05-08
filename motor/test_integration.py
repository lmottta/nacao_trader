#!/usr/bin/env python
"""
Testes de integração para o Motor de Sinais ML.

Este módulo verifica:
1. Conexão com o TimescaleDB
2. Acesso às funções edge do Supabase
3. Performance de consultas
4. Geração de dados de teste
"""
import asyncio
import time
import json
import datetime
import random
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

import httpx
# Importar pandas e numpy somente se necessário
try:
    import pandas as pd
    import numpy as np
except ImportError:
    pass  # Trataremos isso nas funções que precisam deles

from src.utils.config import settings
from src.utils.logger import get_logger

# Configurar logger
log = get_logger("integration_tests")

async def test_timescaledb() -> bool:
    """
    Testa se o TimescaleDB está corretamente configurado.
    
    Returns:
        bool: True se o TimescaleDB está funcionando corretamente
    """
    log.info("Testando configuração do TimescaleDB")
    
    try:
        # Importar cliente Supabase apenas quando necessário
        from src.db.client import get_supabase_client
        
        # Obter cliente Supabase
        supabase = await get_supabase_client()
        
        # Testar se podemos executar uma consulta TimescaleDB específica
        query = """
        SELECT extname FROM pg_extension 
        WHERE extname = 'timescaledb'
        """
        
        response = await supabase.rpc('execute_sql', {'query': query})
        
        if response and len(response) > 0:
            log.info("TimescaleDB está configurado corretamente")
            return True
        else:
            log.warning("TimescaleDB não foi encontrado nas extensões")
            return False
            
    except Exception as e:
        log.error(f"Erro ao testar TimescaleDB: {e}")
        return False


async def test_edge_functions() -> Dict[str, str]:
    """
    Testa o acesso às funções edge do Supabase.
    
    Returns:
        Dict[str, str]: Dicionário com nome da função e status
    """
    log.info("Testando funções edge do Supabase")
    
    # Funções edge a serem testadas
    functions = [
        "generate-signal",
        "signals-dashboard"
    ]
    
    results = {}
    
    try:
        # URL base para funções edge
        base_url = f"{settings.SUPABASE_URL}/functions/v1"
        
        # Configurar cliente HTTP
        async with httpx.AsyncClient(timeout=10.0) as client:
            for func_name in functions:
                try:
                    # Testar função com GET (só para verificar se está acessível)
                    response = await client.get(
                        f"{base_url}/{func_name}",
                        headers={
                            "Authorization": f"Bearer {settings.SUPABASE_ANON_KEY}"
                        }
                    )
                    
                    # Verificar se a função está disponível (pode retornar 404 ou outro erro, mas não 500)
                    if response.status_code != 500:
                        results[func_name] = "available"
                    else:
                        results[func_name] = "error"
                        
                except Exception as e:
                    log.warning(f"Erro ao testar função {func_name}: {e}")
                    results[func_name] = "unavailable"
        
        log.info(f"Resultados dos testes de funções edge: {results}")
        return results
        
    except Exception as e:
        log.error(f"Erro ao testar funções edge: {e}")
        return {}


async def insert_test_data() -> bool:
    """
    Insere dados de teste no banco de dados.
    
    Returns:
        bool: True se os dados foram inseridos com sucesso
    """
    log.info("Inserindo dados de teste")
    
    try:
        # Importar cliente Supabase apenas quando necessário
        from src.db.client import get_supabase_client
        
        # Obter cliente Supabase
        supabase = await get_supabase_client()
        
        # Verificar se já existem dados de teste
        check_query = """
        SELECT COUNT(*) FROM price_history WHERE symbol = 'TEST_ASSET'
        """
        
        response = await supabase.rpc('execute_sql', {'query': check_query})
        if response and response[0]['count'] > 0:
            log.info("Dados de teste já existem, pulando inserção")
            return True
        
        # Gerar dados de teste
        current_time = datetime.datetime.now()
        
        # Gerar 100 registros diários para um ativo fictício
        test_data = []
        for i in range(100):
            # Data decrescente (mais recente primeiro)
            timestamp = current_time - datetime.timedelta(days=i)
            
            # Gerar preços OHLCV realistas
            base_price = 100 + random.random() * 50
            open_price = base_price
            high_price = open_price * (1 + random.random() * 0.05)
            low_price = open_price * (1 - random.random() * 0.05)
            close_price = low_price + random.random() * (high_price - low_price)
            volume = random.randint(100000, 1000000)
            
            test_data.append({
                "symbol": "TEST_ASSET",
                "timestamp": timestamp.isoformat(),
                "timeframe": "1d",
                "open": open_price,
                "high": high_price,
                "low": low_price,
                "close": close_price,
                "volume": volume
            })
        
        # Inserir dados no banco
        for chunk in [test_data[i:i+20] for i in range(0, len(test_data), 20)]:
            insert_query = """
            INSERT INTO price_history (symbol, timestamp, timeframe, open, high, low, close, volume)
            VALUES 
            """
            
            values = []
            for record in chunk:
                values.append(
                    f"('{record['symbol']}', '{record['timestamp']}', '{record['timeframe']}', "
                    f"{record['open']}, {record['high']}, {record['low']}, {record['close']}, {record['volume']})"
                )
            
            insert_query += ", ".join(values)
            insert_query += " ON CONFLICT (symbol, timestamp, timeframe) DO NOTHING"
            
            await supabase.rpc('execute_sql', {'query': insert_query})
        
        log.info(f"Inseridos {len(test_data)} registros de teste")
        return True
        
    except Exception as e:
        log.error(f"Erro ao inserir dados de teste: {e}")
        return False


async def test_api_endpoint() -> bool:
    """
    Testa se a API está respondendo corretamente.
    
    Returns:
        bool: True se a API está funcionando
    """
    log.info("Testando API")
    
    try:
        # Testar API local se disponível
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                response = await client.get("http://localhost:8000/health")
                if response.status_code == 200:
                    log.info("API local está funcionando")
                    return True
            except Exception:
                log.warning("API local não está disponível. Verifique se está em execução.")
        
        return False
        
    except Exception as e:
        log.error(f"Erro ao testar API: {e}")
        return False


async def test_query_performance() -> Dict[str, float]:
    """
    Testa a performance de consultas com e sem TimescaleDB.
    
    Returns:
        Dict[str, float]: Dicionário com tempos de consulta
    """
    log.info("Testando performance de consultas")
    
    results = {}
    
    try:
        # Importar cliente Supabase apenas quando necessário
        from src.db.client import get_supabase_client
        
        # Obter cliente Supabase
        supabase = await get_supabase_client()
        
        # Consulta com TimescaleDB (usando funções específicas)
        timescale_query = """
        SELECT time_bucket('1 day', timestamp) AS bucket,
               first(open, timestamp) as open,
               max(high) as high,
               min(low) as low,
               last(close, timestamp) as close,
               sum(volume) as volume
        FROM price_history
        WHERE symbol = 'TEST_ASSET'
        AND timestamp >= NOW() - INTERVAL '90 days'
        GROUP BY bucket
        ORDER BY bucket DESC
        LIMIT 30;
        """
        
        # Consulta equivalente sem TimescaleDB
        simple_query = """
        SELECT 
            date_trunc('day', timestamp) AS bucket,
            open,
            high,
            low,
            close,
            volume
        FROM (
            SELECT 
                timestamp,
                open,
                high,
                low,
                close,
                volume,
                ROW_NUMBER() OVER (PARTITION BY date_trunc('day', timestamp) ORDER BY timestamp DESC) as rn
            FROM price_history
            WHERE symbol = 'TEST_ASSET'
            AND timestamp >= NOW() - INTERVAL '90 days'
        ) subq
        WHERE rn = 1
        ORDER BY bucket DESC
        LIMIT 30;
        """
        
        # Executar consulta TimescaleDB e medir tempo
        start_time = time.time()
        await supabase.rpc('execute_sql', {'query': timescale_query})
        timescale_time = time.time() - start_time
        results['timescale_query_time'] = timescale_time
        
        # Executar consulta simples e medir tempo
        start_time = time.time()
        await supabase.rpc('execute_sql', {'query': simple_query})
        simple_time = time.time() - start_time
        results['simple_query_time'] = simple_time
        
        log.info(f"Tempo de consulta TimescaleDB: {timescale_time:.4f}s")
        log.info(f"Tempo de consulta simples: {simple_time:.4f}s")
        
        return results
        
    except Exception as e:
        log.error(f"Erro ao testar performance de consultas: {e}")
        return {}


async def run_all_tests():
    """Executa todos os testes de integração em sequência."""
    log.info("Iniciando testes de integração")
    
    # Testar TimescaleDB
    timescale_ok = await test_timescaledb()
    
    # Testar funções edge
    edge_results = await test_edge_functions()
    
    # Inserir dados de teste se TimescaleDB estiver configurado
    if timescale_ok:
        data_ok = await insert_test_data()
    else:
        data_ok = False
        log.warning("Pulando inserção de dados de teste devido a falha no TimescaleDB")
    
    # Testar API
    api_ok = await test_api_endpoint()
    
    # Testar performance de consultas se os dados foram inseridos
    if data_ok:
        perf_results = await test_query_performance()
    else:
        perf_results = {}
        log.warning("Pulando testes de performance devido a falha na inserção de dados")
    
    # Mostrar resultados
    log.info("Resultados dos testes de integração:")
    log.info(f"- TimescaleDB: {'OK' if timescale_ok else 'FALHA'}")
    log.info(f"- Funções Edge: {', '.join([f'{f}:{s}' for f, s in edge_results.items()])}")
    log.info(f"- Dados de Teste: {'OK' if data_ok else 'FALHA'}")
    log.info(f"- API: {'OK' if api_ok else 'FALHA'}")
    
    if perf_results:
        log.info(f"- Performance (TimescaleDB): {perf_results.get('timescale_query_time', 'N/A'):.4f}s")
        log.info(f"- Performance (Simples): {perf_results.get('simple_query_time', 'N/A'):.4f}s")


# Executar testes se rodado diretamente
if __name__ == "__main__":
    asyncio.run(run_all_tests()) 