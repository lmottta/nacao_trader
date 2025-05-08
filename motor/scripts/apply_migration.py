#!/usr/bin/env python
# motor/scripts/apply_migration.py

import os
import sys
import time
import argparse
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client, Client

# Configurações
MIGRATIONS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'migrations')
ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')

# Carregar variáveis de ambiente
load_dotenv(dotenv_path=ENV_PATH)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

def init_supabase():
    """Inicializa o cliente Supabase"""
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        print("Erro: Variáveis de ambiente SUPABASE_URL e SUPABASE_SERVICE_KEY não encontradas.")
        print(f"Verifique se o arquivo .env existe em {os.path.dirname(ENV_PATH)} e contém as variáveis.")
        sys.exit(1)
    
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        print("✓ Cliente Supabase inicializado com sucesso.")
        return supabase
    except Exception as e:
        print(f"✗ Erro ao inicializar cliente Supabase: {e}")
        sys.exit(1)

def apply_migration(migration_file, supabase):
    """Aplica uma migração SQL no banco de dados"""
    print(f"\n🔄 Aplicando migração: {migration_file.name}")
    
    try:
        # Ler o arquivo SQL
        with open(migration_file, 'r') as f:
            sql = f.read()
        
        # Executar o SQL diretamente usando o cliente REST
        start_time = time.time()
        # supabase.table("_none_").rpc("pg_query", {"query": sql}).execute()
        
        # Usar método alternativo para executar SQL bruto
        result = supabase.postgrest.schema("public").execute(sql)
        end_time = time.time()
        
        print(f"✅ Migração {migration_file.name} aplicada com sucesso! ({end_time - start_time:.2f}s)")
        return True
    except Exception as e:
        print(f"❌ Erro ao aplicar migração {migration_file.name}:")
        print(f"   {type(e).__name__}: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Aplica migrações SQL no banco de dados Supabase")
    parser.add_argument('--file', '-f', help="Nome específico do arquivo de migração para aplicar")
    parser.add_argument('--all', '-a', action='store_true', help="Aplicar todas as migrações disponíveis")
    args = parser.parse_args()
    
    supabase = init_supabase()
    
    if not os.path.exists(MIGRATIONS_DIR):
        print(f"✗ Diretório de migrações não encontrado: {MIGRATIONS_DIR}")
        sys.exit(1)
    
    migrations = sorted([f for f in Path(MIGRATIONS_DIR).glob('*.sql')])
    if not migrations:
        print("✗ Nenhum arquivo de migração encontrado.")
        sys.exit(1)
    
    print(f"📁 Encontradas {len(migrations)} migrações:")
    for i, m in enumerate(migrations):
        print(f"   {i+1}. {m.name}")
    
    if args.file:
        # Aplicar migração específica
        target_file = os.path.join(MIGRATIONS_DIR, args.file)
        if not os.path.exists(target_file):
            print(f"✗ Arquivo de migração não encontrado: {args.file}")
            sys.exit(1)
        
        success = apply_migration(Path(target_file), supabase)
        sys.exit(0 if success else 1)
    
    elif args.all:
        # Aplicar todas as migrações
        applied = 0
        failed = 0
        
        for migration in migrations:
            if apply_migration(migration, supabase):
                applied += 1
            else:
                failed += 1
        
        print(f"\n📊 Resumo: {applied} migrações aplicadas, {failed} falharam.")
        sys.exit(1 if failed > 0 else 0)
    
    else:
        # Modo interativo
        print("\nSelecione uma migração para aplicar:")
        for i, m in enumerate(migrations):
            print(f"{i+1}. {m.name}")
        
        print("\n0. Sair")
        print("A. Aplicar todas")
        
        choice = input("\nEscolha uma opção: ").strip()
        
        if choice.lower() == 'a':
            # Aplicar todas
            applied = 0
            failed = 0
            
            for migration in migrations:
                if apply_migration(migration, supabase):
                    applied += 1
                else:
                    failed += 1
            
            print(f"\n📊 Resumo: {applied} migrações aplicadas, {failed} falharam.")
            sys.exit(1 if failed > 0 else 0)
        
        elif choice == '0':
            print("Operação cancelada.")
            sys.exit(0)
        
        else:
            try:
                index = int(choice) - 1
                if 0 <= index < len(migrations):
                    success = apply_migration(migrations[index], supabase)
                    sys.exit(0 if success else 1)
                else:
                    print("✗ Opção inválida.")
                    sys.exit(1)
            except ValueError:
                print("✗ Opção inválida.")
                sys.exit(1)

if __name__ == "__main__":
    main() 