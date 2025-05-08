#!/usr/bin/env python
"""
Script para configuração e verificação do Motor de Sinais ML.

Este script:
1. Configura o TimescaleDB no Supabase
2. Verifica as funções edge
3. Executa testes de integração básicos
4. Gera dados iniciais para teste

Uso:
    python run_setup.py
"""
import os
import sys
import asyncio
import argparse
import importlib.util
from pathlib import Path
import logging
import subprocess
import yfinance as yf

# Configurar logging padrão como fallback
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("setup")

# Verificar e importar dependências
def check_dependencies():
    """Verifica se as dependências necessárias estão instaladas."""
    # Declarar variável global no início da função
    global logger
    
    dependencies = {
        'loguru': False,
        'httpx': False,
        'pandas': False,
        'numpy': False,
        'supabase': False,
        'pydantic': False,
    }
    
    for dep in dependencies:
        try:
            importlib.import_module(dep)
            dependencies[dep] = True
        except ImportError:
            dependencies[dep] = False
    
    # Verificação especial para pydantic-settings
    try:
        importlib.import_module('pydantic_settings')
        dependencies['pydantic_settings'] = True
    except ImportError:
        dependencies['pydantic_settings'] = False
        
    missing = [dep for dep, installed in dependencies.items() if not installed]
    
    if missing:
        logger.warning(f"Dependências faltando: {', '.join(missing)}")
        logger.info("Para instalar as dependências necessárias, execute:")
        logger.info("python install_deps.py")
        
        choice = input("Deseja instalar as dependências automaticamente? (S/n): ").lower() or 's'
        if choice == 's':
            try:
                # Tenta executar o script de instalação
                subprocess.run([sys.executable, "install_deps.py", "--core"], check=True)
                logger.info("Dependências básicas instaladas. Continuando...")
                
                # Recarregar as dependências instaladas
                for dep in dependencies:
                    try:
                        if dep in sys.modules:
                            # Se já carregado, recarregar
                            importlib.reload(sys.modules[dep])
                        else:
                            # Tentar importar novamente
                            importlib.import_module(dep)
                    except ImportError:
                        pass
            except Exception as e:
                logger.error(f"Erro ao instalar dependências: {e}")
                logger.info("Por favor, instale as dependências manualmente e tente novamente.")
                sys.exit(1)
        else:
            logger.info("Configuração abortada. Instale as dependências e tente novamente.")
            sys.exit(1)
    else:
        logger.info("Todas as dependências básicas estão instaladas")
    
    # Tentar usar loguru se disponível
    try:
        from loguru import logger as loguru_logger
        # Sobrescrever o logger padrão com o loguru
        logger = loguru_logger
        logger.info("Usando loguru para logging")
    except ImportError:
        logger.info("Usando logging padrão do Python (loguru não encontrado)")

# Verificar dependências antes de continuar
check_dependencies()

# Função para importar dinamicamente um módulo a partir do arquivo
def import_module_from_file(module_name, file_path):
    """Importa um módulo Python dinamicamente a partir do caminho do arquivo."""
    try:
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None:
            logger.error(f"Não foi possível carregar o módulo de {file_path}")
            return None
            
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        logger.error(f"Erro ao importar módulo {module_name} de {file_path}: {e}")
        return None

# Caminhos para os arquivos necessários
MOTOR_ROOT = Path(__file__).parent
TIMESCALE_MIGRATION_PATH = MOTOR_ROOT / "src" / "db" / "migrations" / "002_setup_timescaledb.py"
TEST_INTEGRATION_PATH = MOTOR_ROOT / "test_integration.py"

# Adicionar diretório raiz ao sys.path para facilitar importações
sys.path.insert(0, str(MOTOR_ROOT))

# Importar os módulos dinamicamente
logger.info("Importando módulos...")

# Importar módulo de migração TimescaleDB
# Usamos um nome que não começa com número para evitar problemas
timescale_module = import_module_from_file("timescale_setup_module", TIMESCALE_MIGRATION_PATH)
if timescale_module:
    setup_timescaledb = timescale_module.run_migration
    logger.info("Módulo de migração TimescaleDB importado com sucesso")
else:
    logger.error("Falha ao importar módulo de migração TimescaleDB. Abortando.")
    sys.exit(1)

# Importar módulo de testes de integração
test_integration = import_module_from_file("test_integration", TEST_INTEGRATION_PATH)
if test_integration:
    test_timescaledb = test_integration.test_timescaledb
    test_edge_functions = test_integration.test_edge_functions
    test_api_endpoint = test_integration.test_api_endpoint
    insert_test_data = test_integration.insert_test_data
    test_query_performance = test_integration.test_query_performance
    logger.info("Módulo de testes de integração importado com sucesso")
else:
    logger.error("Falha ao importar módulo de testes de integração. Abortando.")
    sys.exit(1)

# Importar configurações
try:
    # Tentar importar as configurações
    from src.utils.config import settings
    logger.info("Configurações importadas com sucesso")
except ImportError as e:
    logger.error(f"Erro ao importar configurações: {e}")
    logger.info("Tentando importar dinamicamente...")
    
    # Alternativa: tentar importar dinamicamente
    config_path = MOTOR_ROOT / "src" / "utils" / "config.py"
    config_module = import_module_from_file("config_module", config_path)
    
    if config_module:
        settings = config_module.settings
        logger.info("Configurações importadas dinamicamente com sucesso")
    else:
        logger.error("Falha ao importar configurações. Abortando.")
        sys.exit(1)

# Função para importar get_logger se estiver disponível, ou criar uma função substituta
try:
    from src.utils.logger import get_logger
    log = get_logger("setup")
    logger.info("Função get_logger importada com sucesso")
except ImportError:
    # Criar uma função substituta que retorna o logger padrão
    def get_logger(name):
        return logger.bind(component=name) if hasattr(logger, "bind") else logging.getLogger(name)
    
    log = get_logger("setup")
    logger.info("Usando função get_logger substituta")

async def verify_environment():
    """Verifica se o ambiente está corretamente configurado."""
    log.info("Verificando configuração de ambiente")
    
    # Verificar variáveis de ambiente necessárias
    required_vars = [
        "SUPABASE_URL",
        "SUPABASE_ANON_KEY",
        "SUPABASE_SERVICE_KEY"
    ]
    
    # Verificar primeiro se settings tem os atributos necessários
    missing_vars = []
    for var in required_vars:
        if not hasattr(settings, var) or not getattr(settings, var, None):
            missing_vars.append(var)
    
    if missing_vars:
        log.error(f"Variáveis de ambiente ausentes: {', '.join(missing_vars)}")
        log.info("Configure estas variáveis no arquivo .env ou variáveis de ambiente do sistema")
        
        # Verificar se existe um arquivo .env
        env_file = MOTOR_ROOT / ".env"
        env_example_file = MOTOR_ROOT / ".env.example"
        
        if not env_file.exists():
            log.warning("Arquivo .env não encontrado")
            
            # Copiar do .env.example se existir
            if env_example_file.exists():
                create_env = input("Deseja criar um arquivo .env a partir do .env.example? (S/n): ").lower() or 's'
                if create_env == 's':
                    with open(env_example_file, 'r') as src, open(env_file, 'w') as dest:
                        content = src.read()
                        dest.write(content)
                    log.info(f"Arquivo .env criado a partir de .env.example")
                    log.info("Edite o arquivo com suas configurações e execute novamente")
            else:
                # Criar um modelo de arquivo .env
                create_env = input("Deseja criar um arquivo .env modelo? (S/n): ").lower() or 's'
                if create_env == 's':
                    with open(env_file, 'w') as f:
                        f.write("# Configurações do Motor de Sinais ML\n\n")
                        f.write("# Supabase\n")
                        f.write("SUPABASE_URL=https://seu-projeto.supabase.co\n")
                        f.write("SUPABASE_ANON_KEY=sua-chave-anonima\n")
                        f.write("SUPABASE_SERVICE_KEY=sua-chave-de-servico\n\n")
                        f.write("# Configurações de API\n")
                        f.write("API_KEY=chave-api-secreta\n")
                    log.info(f"Arquivo .env criado em {env_file}")
                    log.info("Edite o arquivo com suas configurações e execute novamente")
        
        return False
    
    log.info("Configuração de ambiente verificada com sucesso")
    return True


async def setup_database():
    """Configura o banco de dados com TimescaleDB."""
    log.info("Iniciando configuração do banco de dados")
    
    try:
        # Executar migração TimescaleDB
        await setup_timescaledb()
        
        # Verificar se a configuração foi bem-sucedida
        is_configured = await test_timescaledb()
        
        if is_configured:
            log.info("Banco de dados configurado com sucesso")
        else:
            log.warning("Configuração do banco de dados pode estar incompleta")
        
        return is_configured
    except Exception as e:
        log.error(f"Erro ao configurar banco de dados: {e}")
        return False


async def deploy_edge_functions():
    """Verifica as funções edge do Supabase."""
    log.info("Verificando funções edge")
    
    try:
        # Testar funções edge
        results = await test_edge_functions()
        
        if not results:  # Se results é vazio ou None
            log.warning("Não foi possível verificar funções edge")
            return False
        
        all_available = all(status == "available" for status in results.values())
        
        if all_available:
            log.info("Todas as funções edge estão disponíveis")
        else:
            log.warning("Algumas funções edge podem não estar disponíveis ou corretamente configuradas")
            log.info("Verifique a documentação do Supabase para implantar funções edge")
        
        return all_available
    except Exception as e:
        log.error(f"Erro ao verificar funções edge: {e}")
        return False


async def populate_test_data():
    """Popula o banco de dados com dados de teste."""
    log.info("Inserindo dados de teste")
    
    try:
        # Inserir dados de teste
        success = await insert_test_data()
        
        if success:
            log.info("Dados de teste inseridos com sucesso")
        else:
            log.warning("Falha ao inserir dados de teste")
        
        return success
    except Exception as e:
        log.error(f"Erro ao inserir dados de teste: {e}")
        return False


async def run_performance_tests():
    """Executa testes de performance do banco de dados."""
    log.info("Executando testes de performance")
    
    try:
        # Testar performance de consultas
        results = await test_query_performance()
        
        if not results:  # Se results é vazio ou None
            log.warning("Não foi possível executar testes de performance")
            return False
        
        if results.get("timescale_query_time"):
            log.info(f"Tempo de consulta TimescaleDB: {results['timescale_query_time']:.4f}s")
            log.info(f"Tempo de consulta simples: {results['simple_query_time']:.4f}s")
            
            # Comparar tempos para ver se TimescaleDB está otimizando
            if results['timescale_query_time'] < results['simple_query_time'] * 2:
                log.info("TimescaleDB está funcionando eficientemente")
            else:
                log.warning("TimescaleDB pode precisar de otimização adicional")
        else:
            log.warning("Não foi possível executar consulta TimescaleDB")
        
        return True  # Retornar True mesmo se TimescaleDB não estiver disponível
    except Exception as e:
        log.error(f"Erro ao executar testes de performance: {e}")
        return False


async def main():
    """Função principal para executar a configuração."""
    parser = argparse.ArgumentParser(description="Configuração do Motor de Sinais ML")
    parser.add_argument("--skip-db", action="store_true", help="Pular configuração do banco de dados")
    parser.add_argument("--skip-edge", action="store_true", help="Pular verificação de funções edge")
    parser.add_argument("--skip-data", action="store_true", help="Pular inserção de dados de teste")
    parser.add_argument("--skip-tests", action="store_true", help="Pular testes de performance")
    parser.add_argument("--env-only", action="store_true", help="Verificar apenas as variáveis de ambiente")
    
    args = parser.parse_args()
    
    log.info("Iniciando configuração do Motor de Sinais ML")
    
    # Verificar ambiente
    env_ok = await verify_environment()
    if not env_ok:
        log.error("Configuração de ambiente falhou. Abortando.")
        return
    
    # Se a opção --env-only for passada, parar após verificar o ambiente
    if args.env_only:
        log.info("Verificação de ambiente concluída. Saindo conforme solicitado.")
        return
    
    # Configurar banco de dados
    if not args.skip_db:
        db_ok = await setup_database()
        if not db_ok:
            log.warning("Configuração do banco de dados incompleta")
            # Perguntar se deseja continuar
            choice = input("Continuar mesmo com a configuração do banco incompleta? (S/n): ").lower() or 's'
            if choice != 's':
                log.info("Configuração abortada pelo usuário.")
                return
    
    # Verificar funções edge
    if not args.skip_edge:
        edge_ok = await deploy_edge_functions()
        if not edge_ok:
            log.warning("Verificação de funções edge incompleta")
    
    # Inserir dados de teste
    if not args.skip_data:
        data_ok = await populate_test_data()
        if not data_ok:
            log.warning("Inserção de dados de teste incompleta")
    
    # Executar testes de performance
    if not args.skip_tests:
        test_ok = await run_performance_tests()
        if not test_ok:
            log.warning("Testes de performance incompletos")
    
    log.info("Configuração do Motor de Sinais ML concluída")
    log.info("Execute 'python -m src.api.main' para iniciar a API")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Configuração interrompida pelo usuário.")
    except Exception as e:
        logger.error(f"Erro fatal durante a configuração: {e}")
        import traceback
        logger.error(traceback.format_exc()) 