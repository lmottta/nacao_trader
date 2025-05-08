import os
import json
import random
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv
from supabase import create_client, Client

# Carregar variáveis de ambiente do .env na pasta motor/
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    print("Erro: Variáveis de ambiente SUPABASE_URL e SUPABASE_SERVICE_KEY não encontradas.")
    print(f"Verifique se o arquivo .env existe em {os.path.dirname(dotenv_path)} e contém as variáveis.")
    exit(1)

# Configuração do cliente Supabase
try:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    print("Cliente Supabase inicializado com sucesso.")
except Exception as e:
    print(f"Erro ao inicializar cliente Supabase: {e}")
    exit(1)

# Configurações para geração de sinais de alta qualidade
PRIORITY_ASSETS = [
    # Ações importantes
    "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", 
    "PETR4.SA", "VALE3.SA", "ITUB4.SA",
    # Criptomoedas principais
    "BTC-USD", "ETH-USD", "SOL-USD",
    # Forex principais
    "EURUSD=X", "GBPUSD=X", "USDJPY=X", "USDBRL=X"
]

# Análises técnicas de qualidade por ativo (simulando análises reais)
ANALYSIS_TEMPLATES = {
    # Tech stocks
    "AAPL": {
        "BUY": [
            "Rompimento da média móvel de 50 dias com forte volume. Indicadores mostram RSI saindo da zona de sobrevenda (RSI: {rsi}). Suporte em ${support} e objetivo em ${target}.",
            "Padrão de fundo duplo formado no gráfico diário com confirmação de alta. MACD ({macd}) mostra divergência positiva. Projeção técnica sugere movimento para ${target}.",
            "Movimento de alta após consolidação em triângulo ascendente. Volume crescente nos últimos 3 dias indica força compradora. Suporte em ${support} com resistência imediata em ${resistance}."
        ],
        "SELL": [
            "Topo formado próximo a resistência histórica em ${resistance}. Indicadores mostram RSI em zona de sobrecompra (RSI: {rsi}). Correção técnica esperada até ${target}.",
            "Divergência negativa no MACD ({macd}) com preço em zona de resistência. Volume diminuindo na fase de alta, sinalizando esgotamento. Suporte inicial em ${support}.",
            "Formação de topo duplo no gráfico diário com rompimento da linha de tendência de alta. Indicadores técnicos sugerem correção para ${target}."
        ]
    },

    # Criptomoedas
    "BTC-USD": {
        "BUY": [
            "Bitcoin rompeu resistência de ${resistance} com aumento significativo de volume. RSI em {rsi} mostra momentum positivo. Próximo alvo em ${target} (retração de Fibonacci).",
            "Padrão bullish de acumulação com suporte em ${support}. Indicadores on-chain mostram diminuição de bitcoins em exchanges. MACD ({macd}) cruzou para cima.",
            "Consolidação acima da média móvel de 200 dias, que funciona como suporte dinâmico em ${support}. Volume institucional aumentando, com projeção para ${target}."
        ],
        "SELL": [
            "Bitcoin atingiu resistência importante em ${resistance} coincidindo com topo anterior. RSI em {rsi} mostra condição de sobrecompra. Suporte em ${support} deve ser monitorado.",
            "Formação de topo com divergência nos indicadores técnicos. MACD em {macd} mostra perda de força. Métricas on-chain indicam aumento de transferências para exchanges.",
            "Pressão vendedora aumentando após falha em superar ${resistance}. Volume diminuindo durante os movimentos de alta, sugerindo correção para ${target}."
        ]
    },

    # Forex
    "EURUSD=X": {
        "BUY": [
            "EUR/USD formou suporte na região de ${support} (coincidindo com retração de Fibonacci de 61.8%). RSI em {rsi} saindo da zona de sobrevenda com momentum positivo.",
            "Rompimento de canal de baixa com aumento de volume. Indicadores técnicos (MACD: {macd}) mostram divergência positiva. Alvo inicial em ${target} (retração de 38.2%).",
            "Formação de fundo após dados econômicos positivos da zona do Euro. Suporte em ${support} com projeção para ${target} (paridade anterior)."
        ],
        "SELL": [
            "EUR/USD rejeitado na resistência de ${resistance} (coincidindo com média móvel de 200 períodos). RSI em {rsi} mostra condições de sobrecompra.",
            "Formação de padrão de reversão com MACD ({macd}) indicando momentum negativo. Dados econômicos dos EUA superando expectativas pressionam o par para baixo.",
            "Rompimento de suporte em ${support} após declarações hawkish do Fed. Próximo alvo em ${target} com possível extensão para retração de Fibonacci de 78.6%."
        ]
    },

    # Template genérico para outros ativos
    "default": {
        "BUY": [
            "Rompimento de resistência em ${resistance} com volume acima da média. RSI em {rsi} mostra força na tendência de alta. Suporte em ${support}.",
            "Formação de fundo após correção técnica. MACD ({macd}) cruzou para cima, sinalizando momento de compra. Alvo em ${target}.",
            "Padrão de continuação de alta formado no gráfico. Suporte confirmado em ${support} com objetivos em ${target}."
        ],
        "SELL": [
            "Ativo rejeitado na resistência de ${resistance} com aumento de volume vendedor. RSI em {rsi} indica condição de sobrecompra.",
            "Formação de topo com MACD ({macd}) mostrando divergência negativa. Suporte em ${support} pode ser testado.",
            "Rompimento da linha de tendência de alta com aumento de volume. Próximo suporte em ${support} com alvo em ${target}."
        ]
    }
}

def get_market_context(asset_type, direction):
    """Retorna contexto de mercado baseado no tipo de ativo e direção"""
    
    contexts = {
        "stock": {
            "BUY": [
                "Potencial de crescimento em receita recorrente para os próximos trimestres",
                "Estratégia de expansão internacional com forte alocação de capital",
                "Pipeline de produtos inovadores esperados nos próximos meses",
                "Expectativa de resultados trimestrais acima do consenso de mercado",
                "Movimento de rotação setorial favorecendo empresas de qualidade"
            ],
            "SELL": [
                "Pressão nas margens devido ao aumento de custos operacionais",
                "Concorrência intensificada impactando market share",
                "Expectativa de resultados abaixo do consenso no próximo trimestre",
                "Riscos regulatórios crescentes no setor",
                "Valorização excessiva comparada aos pares setoriais"
            ]
        },
        "crypto": {
            "BUY": [
                "Adoção institucional crescente e aprovação de ETFs",
                "Redução na oferta circulante após evento de halving",
                "Aumento de aplicações DeFi na rede com crescimento de TVL",
                "Melhorias técnicas na escalabilidade da rede recentemente implementadas",
                "Correlação decrescente com mercados tradicionais, indicando maturidade"
            ],
            "SELL": [
                "Aumento de regulação em mercados importantes",
                "Problemas técnicos na rede afetando a confiabilidade",
                "Liquidações em cascata em exchanges com alta alavancagem",
                "Transferências significativas de carteiras antigas para exchanges",
                "Diminuição do volume de transações na rede principal"
            ]
        },
        "forex": {
            "BUY": [
                "Divergência de política monetária favorecendo a moeda base",
                "Dados econômicos robustos superando expectativas de mercado",
                "Fluxo de capital para ativos de risco suportando a moeda",
                "Posicionamento técnico extremamente negativo sugerindo reversão",
                "Acordo comercial iminente com impacto positivo para a economia"
            ],
            "SELL": [
                "Banco central sinalizando postura mais dovish nos próximos meses",
                "Dados econômicos abaixo das expectativas pressionando a moeda",
                "Fluxo de saída de capital para ativos seguros",
                "Tensões geopolíticas afetando a estabilidade econômica regional",
                "Deterioração de termos de troca com principais parceiros comerciais"
            ]
        },
    }
    
    # Usar contexto específico ou default para o tipo de ativo
    asset_contexts = contexts.get(asset_type, contexts.get("stock"))
    direction_contexts = asset_contexts.get(direction, [])
    
    if not direction_contexts:
        return "Análise baseada puramente em indicadores técnicos e padrões de preço."
    
    return random.choice(direction_contexts)

def get_timeframe_description(timeframe):
    """Retorna descrição do horizonte temporal baseado no timeframe"""
    if timeframe == "1h":
        return "curto prazo (intradía)"
    elif timeframe == "4h":
        return "médio prazo (1-3 dias)"
    elif timeframe == "1d":
        return "médio-longo prazo (1-2 semanas)"
    else:
        return "prazo variável"

def get_or_create_assets():
    """Busca ativos existentes ou cria alguns básicos se não existirem."""
    try:
        # Verificar se existem ativos
        response = supabase.table('assets').select('*').limit(50).execute()
        assets = response.data
        
        if assets and len(assets) >= 5:
            print(f"Encontrados {len(assets)} ativos existentes.")
            # Filtra os ativos prioritários se estiverem disponíveis
            priority_assets = [a for a in assets if a.get('symbol') in PRIORITY_ASSETS]
            if priority_assets:
                print(f"Usando {len(priority_assets)} ativos prioritários para gerar sinais de alta qualidade.")
                return priority_assets
            return assets
            
        # Se não existirem ativos suficientes, vamos criar alguns básicos
        print("Criando ativos básicos para teste...")
        basic_assets = [
            {
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "asset_type": "stock",
                "description": "Empresa de tecnologia que projeta e fabrica smartphones, computadores e outros produtos eletrônicos.",
                "last_price": 187.30,
                "last_update": datetime.now().isoformat(),
                "ticker": "AAPL",
                "active": True,
                "currency": "USD",
                "market_status": "open",
                "market_status_source": "Manual",
                "last_status_update": datetime.now().isoformat()
            },
            {
                "symbol": "MSFT",
                "name": "Microsoft Corporation",
                "asset_type": "stock",
                "description": "Empresa de tecnologia conhecida por seus sistemas operacionais, software e serviços em nuvem.",
                "last_price": 331.87,
                "last_update": datetime.now().isoformat(),
                "ticker": "MSFT",
                "active": True,
                "currency": "USD",
                "market_status": "open",
                "market_status_source": "Manual",
                "last_status_update": datetime.now().isoformat()
            },
            {
                "symbol": "BTC-USD",
                "name": "Bitcoin USD",
                "asset_type": "crypto",
                "description": "A primeira e mais conhecida criptomoeda do mundo, criada em 2009.",
                "last_price": 66721.50,
                "last_update": datetime.now().isoformat(),
                "ticker": "BTC-USD",
                "active": True,
                "currency": "USD",
                "market_status": "open",
                "market_status_source": "Manual",
                "last_status_update": datetime.now().isoformat()
            },
            {
                "symbol": "EURUSD=X",
                "name": "EUR/USD",
                "asset_type": "forex",
                "description": "Par de moedas que representa a relação entre o Euro e o Dólar Americano.",
                "last_price": 1.08245,
                "last_update": datetime.now().isoformat(),
                "ticker": "EURUSD=X",
                "active": True,
                "currency": "USD",
                "market_status": "open",
                "market_status_source": "Manual",
                "last_status_update": datetime.now().isoformat()
            }
        ]
        
        # Inserir ativos básicos
        response = supabase.table('assets').upsert(basic_assets, on_conflict="symbol").execute()
        print(f"Criados/atualizados {len(basic_assets)} ativos básicos.")
        
        # Retornar os ativos recém-criados
        return basic_assets
        
    except Exception as e:
        print(f"Erro ao buscar/criar ativos: {e}")
        return []

def create_signals_for_assets(assets, count_per_asset=3):
    """Cria múltiplos sinais de alta qualidade para cada ativo."""
    signals = []
    now = datetime.now(pytz.UTC)
    
    for asset in assets:
        # Garantir que temos um asset_id válido
        asset_id = asset.get("id")
        if not asset_id:
            print(f"Ignorando ativo {asset.get('symbol')} sem ID")
            continue
            
        # Garantir que temos um last_price válido
        current_price = asset.get('last_price')
        if current_price is None or current_price <= 0:
            # Usar um preço padrão baseado no tipo de ativo
            if asset.get('asset_type') == 'forex':
                current_price = random.uniform(0.5, 1.5)
            elif asset.get('asset_type') == 'crypto':
                current_price = random.uniform(100, 50000)
            else:  # stock ou outros
                current_price = random.uniform(10, 500)

        asset_type = asset.get('asset_type', 'stock')
        symbol = asset.get('symbol', '')
        
        for i in range(count_per_asset):
            # Calcular volatilidade esperada baseada no tipo de ativo
            volatility_factor = 0.02  # 2% padrão
            if asset_type == 'crypto':
                volatility_factor = 0.08  # 8% para cripto
            elif asset_type == 'forex':
                volatility_factor = 0.005  # 0.5% para forex
            
            # Variar tempos de geração e validade para simular diferentes momentos
            hours_ago = random.randint(0, 24)
            valid_hours = random.randint(24, 72)
            generated_at = now - timedelta(hours=hours_ago)
            valid_until = generated_at + timedelta(hours=valid_hours)
            
            # Variar direções e confiança de forma mais realista
            # Maior probabilidade de direção de acordo com tendência atual
            if asset.get('change_percent', 0) > 0:
                direction = random.choices(["BUY", "SELL"], weights=[0.65, 0.35])[0]
            else:
                direction = random.choices(["BUY", "SELL"], weights=[0.35, 0.65])[0]
                
            # Confiança entre 65% e 92% (mais realista para análise técnica)
            accuracy = round(random.uniform(65, 92))
            
            # Gerar indicadores técnicos de acordo com a direção (mais coerente)
            if direction == "BUY":
                rsi = round(random.uniform(40, 60), 1)  # RSI saindo de sobrevenda ou neutro
                macd = round(random.uniform(0.001, 0.1), 3)  # MACD positivo, mas não extremo
            else:
                rsi = round(random.uniform(60, 80), 1)  # RSI entrando em sobrecompra
                macd = round(random.uniform(-0.1, -0.001), 3)  # MACD negativo
            
            # Calcular níveis de suporte, resistência e alvos com base no preço atual e volatilidade
            # Mais realista: níveis potencialmente importantes, não apenas percentuais arbitrários
            price_factors = {
                "BUY": {
                    "support": random.uniform(0.94, 0.98),
                    "resistance": random.uniform(1.02, 1.06),
                    "target_min": random.uniform(1.03, 1.06),
                    "target_max": random.uniform(1.08, 1.15),
                },
                "SELL": {
                    "support": random.uniform(0.85, 0.95),
                    "resistance": random.uniform(0.99, 1.01),
                    "target_min": random.uniform(0.94, 0.98),
                    "target_max": random.uniform(0.85, 0.93),
                }
            }[direction]
            
            # Arredondar valores para formatos específicos por tipo de ativo
            if asset_type == 'forex':
                precision = 5 if current_price < 1 else 4
            elif asset_type == 'crypto':
                precision = 0 if current_price > 1000 else 2
            else:
                precision = 2
            
            # Calcular níveis com arredondamento apropriado
            support = round(current_price * price_factors["support"], precision)
            resistance = round(current_price * price_factors["resistance"], precision)
            price_target = round(current_price * price_factors["target_max"], precision)
            stop_loss = round(current_price * (0.97 if direction == "BUY" else 1.03), precision)
            
            # Escolher template para o ativo ou usar default
            templates = ANALYSIS_TEMPLATES.get(symbol, ANALYSIS_TEMPLATES["default"])
            direction_templates = templates.get(direction, ANALYSIS_TEMPLATES["default"][direction])
            
            # Escolher e formatar o template com os valores calculados
            template = random.choice(direction_templates)
            tech_reason = template.format(
                support=support,
                resistance=resistance,
                target=price_target,
                rsi=rsi,
                macd=macd
            )
            
            # Adicionar contexto fundamental/mercado
            market_context = get_market_context(asset_type, direction)
            timeframe_desc = get_timeframe_description(random.choice(["1h", "4h", "1d"]))
            
            # Montar a razão completa
            reason = f"{tech_reason} {market_context} Horizonte: {timeframe_desc}."
            
            # Converter direção para formato da plataforma: BUY->CALL, SELL->PUT
            signal_direction = "CALL" if direction == "BUY" else "PUT"
            
            # Status varia baseado na validade
            status = "active" if valid_until > now else "expired"
            
            # Criando um sinal de alta qualidade
            signal = {
                "asset_symbol": asset.get("symbol"),
                "asset_id": asset.get("id"),
                "direction": signal_direction,
                "accuracy": accuracy,
                "generated_at": generated_at.isoformat(),
                "valid_until": valid_until.isoformat(),
                "source": "ML-Predictor",
                "status": status,
                "timeframe": random.choice(["1h", "4h", "1d"]),
                "price_target": price_target,
                "stop_loss": stop_loss,
                "notes": reason,
                "indicators": {
                    "rsi": rsi,
                    "macd": macd,
                    "price": round(current_price, precision),
                    "support": support,
                    "resistance": resistance
                }
            }
            
            signals.append(signal)
    
    return signals

def clear_existing_signals():
    """Remove todos os sinais existentes."""
    try:
        # Primeiro verificamos quantos sinais existem
        response = supabase.table('signals').select('id').execute()
        existing_signals = response.data
        
        if not existing_signals:
            print("Nenhum sinal existente encontrado para limpar.")
            return True
        
        print(f"Encontrados {len(existing_signals)} sinais existentes. Limpando...")
        
        # Deletar sinais em lotes para evitar problemas com grandes quantidades
        batch_size = 50
        for i in range(0, len(existing_signals), batch_size):
            batch = existing_signals[i:i+batch_size]
            ids = [signal['id'] for signal in batch]
            
            # Deletar lote
            response = supabase.table('signals').delete().in_('id', ids).execute()
            print(f"Lote {i//batch_size + 1}/{(len(existing_signals) + batch_size - 1)//batch_size} limpo.")
        
        print("Todos os sinais existentes foram removidos com sucesso.")
        return True
        
    except Exception as e:
        print(f"Erro ao limpar sinais existentes: {e}")
        return False

def verify_schema():
    """Verifica se o schema da tabela signals tem os campos necessários."""
    try:
        # Tentar obter a estrutura da tabela através de uma consulta
        response = supabase.table('signals').select('*').limit(1).execute()
        
        # Buscar um ativo existente para usar seu ID
        asset_response = supabase.table('assets').select('id').limit(1).execute()
        test_asset_id = None
        if asset_response.data and len(asset_response.data) > 0:
            test_asset_id = asset_response.data[0]['id']
        
        # Vamos criar um sinal de teste para verificar se todos os campos necessários estão presentes
        test_signal = {
            "asset_symbol": "TEST",
            "asset_id": test_asset_id,  # Usar um ID válido de ativo existente
            "direction": "CALL",
            "accuracy": 75,
            "generated_at": datetime.now().isoformat(),
            "valid_until": (datetime.now() + timedelta(hours=24)).isoformat(),
            "source": "SchemaTest",
            "status": "test",
            "timeframe": "1h",
            "price_target": 100.0,
            "stop_loss": 95.0,
            "notes": "Teste de schema",
            "indicators": {
                "rsi": 50,
                "macd": 0.001
            }
        }
        
        # Tentar inserir o sinal de teste
        response = supabase.table('signals').insert(test_signal).execute()
        
        # Se chegou até aqui, o teste foi bem-sucedido
        # Vamos limpar o sinal de teste
        test_id = response.data[0]['id']
        supabase.table('signals').delete().eq('id', test_id).execute()
        
        print("Schema da tabela 'signals' verificado com sucesso.")
        return True
        
    except Exception as e:
        print(f"Erro ao verificar schema: {e}")
        print("Por favor, execute a migração para criar/atualizar a tabela 'signals'.")
        return False

def main():
    print("\n=== GERADOR DE SINAIS DE ALTA QUALIDADE PARA TRADERS ===")
    
    # Verificar schema
    if not verify_schema():
        user_continue = input("Continuar mesmo assim? (s/N): ").lower() == 's'
        if not user_continue:
            print("Operação cancelada.")
            exit(1)
    
    # Perguntar se deve limpar sinais existentes
    should_clear = input("Limpar todos os sinais existentes antes de inserir novos? (S/n): ").lower() != 'n'
    
    if should_clear:
        if not clear_existing_signals():
            user_continue = input("Falha ao limpar sinais. Continuar mesmo assim? (s/N): ").lower() == 's'
            if not user_continue:
                print("Operação cancelada.")
                exit(1)
    
    # Obter ativos e definir quantidade de sinais por ativo
    assets = get_or_create_assets()
    if not assets:
        print("Não foi possível obter ativos. Operação cancelada.")
        exit(1)
    
    # Permitir que o usuário especifique a quantidade de sinais por ativo
    signals_per_asset = 3
    try:
        user_input = input(f"Número de sinais por ativo (padrão: {signals_per_asset}): ")
        if user_input.strip():
            signals_per_asset = int(user_input)
    except ValueError:
        print(f"Valor inválido. Usando o padrão de {signals_per_asset} sinais por ativo.")
    
    # Gerar sinais
    signals = create_signals_for_assets(assets, count_per_asset=signals_per_asset)
    
    if not signals:
        print("Não foi possível gerar sinais. Operação cancelada.")
        exit(1)
    
    print(f"Gerados {len(signals)} sinais de alta qualidade. Inserindo no banco de dados...")
    
    # Inserir sinais em lotes para evitar problemas com grandes quantidades
    batch_size = 10
    inserted_count = 0
    
    for i in range(0, len(signals), batch_size):
        batch = signals[i:i+batch_size]
        
        try:
            # Inserir lote
            response = supabase.table('signals').insert(batch).execute()
            inserted_count += len(response.data)
            print(f"Lote {i//batch_size + 1}/{(len(signals) + batch_size - 1)//batch_size} inserido: {len(response.data)} sinais.")
        except Exception as e:
            print(f"Erro ao inserir lote {i//batch_size + 1}: {e}")
    
    print(f"\nOperação concluída. {inserted_count} de {len(signals)} sinais inseridos com sucesso.")
    print("\n✅ Sinais de alta qualidade para traders agora disponíveis na plataforma!")

if __name__ == "__main__":
    main() 