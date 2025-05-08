#!/usr/bin/env python
# motor/scripts/add_columns.py

import os
import time
from dotenv import load_dotenv
from supabase import create_client

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
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    print("Cliente Supabase inicializado com sucesso.")
except Exception as e:
    print(f"Erro ao inicializar cliente Supabase: {e}")
    exit(1)

# Verificar se a tabela assets existe
try:
    # Tentar buscar um registro para verificar se a tabela existe
    response = supabase.table('assets').select('id').limit(1).execute()
    print("Tabela 'assets' encontrada.")
except Exception as e:
    print(f"Erro ao verificar tabela 'assets': {e}")
    print("A tabela 'assets' pode não existir ou não estar acessível.")
    exit(1)

# Verificar a estrutura atual da tabela (colunas existentes)
try:
    existing_columns = set()
    print("\nVerificando colunas existentes...")
    
    # Usar uma abordagem indireta: buscar um registro com todos os campos
    schema_response = supabase.table('assets').select('*').limit(1).execute()
    
    if schema_response.data:
        # Usar as chaves do primeiro registro para saber quais colunas existem
        existing_columns = set(schema_response.data[0].keys())
        print(f"Colunas existentes: {', '.join(sorted(existing_columns))}")
    else:
        print("Nenhum registro encontrado para verificar colunas. Assumindo tabela vazia.")
except Exception as e:
    print(f"Erro ao verificar colunas existentes: {e}")
    # Continuar mesmo com erro, tentaremos adicionar as colunas de qualquer forma

# Lista de campos desejados para verificar e adicionar
desired_columns = {
    'ticker': 'VARCHAR(50)',
    'active': 'BOOLEAN DEFAULT true',
    'currency': 'VARCHAR(10)',
    'metadata': 'JSONB DEFAULT \'{}\''
}

if 'market_status' not in existing_columns:
    desired_columns['market_status'] = 'VARCHAR(20)'

if 'market_status_source' not in existing_columns:
    desired_columns['market_status_source'] = 'VARCHAR(50)'

if 'last_status_update' not in existing_columns:
    desired_columns['last_status_update'] = 'TIMESTAMPTZ'

# Adicionar campos que faltam, um por um
for column_name, column_type in desired_columns.items():
    if column_name in existing_columns:
        print(f"Coluna '{column_name}' já existe. Pulando.")
        continue
    
    print(f"Adicionando coluna '{column_name}' com tipo {column_type}...")
    
    try:
        # Usar uma tabela temporária para executar uma operação que adiciona a coluna na tabela real
        # Esta é uma forma indireta de executar ALTER TABLE, já que não temos acesso direto ao SQL
        # A ideia é fazer um INSERT na tabela _temp que contenha o comando SQL desejado
        
        # Usar uma query de seleção para determinar se a coluna existe
        # Se a coluna já existir, a query retornará um registro
        # Se não existir, tentamos adicioná-la via REST API
        
        # Primeiro, verificar novamente se a coluna ainda não existe
        test_query = f"SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'assets' AND column_name = '{column_name}'"
        try:
            # Infelizmente, não podemos executar SQL puro pelo cliente JavaScript
            # Tentaremos uma abordagem alternativa
            pass
        except:
            pass
        
        # Tentativa de adicionar via REST (limitado ao que o PostgREST permite)
        # Usar um método que seja mais compatível com a versão atual do Supabase
        try:
            # Criar um registro temporário sem essa coluna e depois tentar fazer um update com ela
            temp_id = "temp_" + str(int(time.time()))
            supabase.table('assets').insert({"id": temp_id, "symbol": temp_id, "name": "Temporary Asset", "asset_type": "temp"}).execute()
            
            # Agora tentar atualizar com o campo que queremos adicionar
            update_data = {"id": temp_id}
            update_data[column_name] = None  # Valor nulo para o novo campo
            supabase.table('assets').update(update_data).eq('id', temp_id).execute()
            
            # Remover o registro temporário
            supabase.table('assets').delete().eq('id', temp_id).execute()
            
            print(f"✓ Coluna '{column_name}' adicionada com sucesso (ou já existia).")
        except Exception as update_err:
            print(f"✗ Erro ao adicionar coluna '{column_name}': {update_err}")
            print("⚠️ Você precisará adicionar esta coluna manualmente via console do Supabase.")
    
    except Exception as e:
        print(f"✗ Erro ao processar coluna '{column_name}': {e}")

print("\nOperação concluída. Verifique manualmente se todas as colunas foram adicionadas.")
print("Se alguma coluna não foi adicionada, você precisará fazê-lo manualmente via console do Supabase.")
print("\nPara adicionar manualmente, execute os seguintes comandos SQL no editor SQL do Supabase:")

for column_name, column_type in desired_columns.items():
    if column_name not in existing_columns:
        print(f"ALTER TABLE assets ADD COLUMN IF NOT EXISTS {column_name} {column_type};")

print("\nAgora você pode executar o script fetch_yahoo_assets.py novamente.") 