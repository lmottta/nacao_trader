#!/usr/bin/env python
"""
Script de instalação de dependências para o Motor de Sinais ML.

Este script:
1. Verifica se pip está disponível
2. Instala as dependências básicas necessárias para o projeto
3. Oferece opções para instalar dependências opcionais

Uso:
    python install_deps.py [--all] [--core] [--ml] [--viz]
"""
import subprocess
import sys
import argparse
import os
import platform
from pathlib import Path

# Cores para terminal
class TermColors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# Verificar se cores são suportadas no terminal atual
def supports_color():
    """Verifica se o terminal suporta cores ANSI."""
    if platform.system() == 'Windows':
        # No Windows, as cores ANSI são suportadas a partir do Windows 10
        # No entanto, alguns terminais (cmd.exe) não suportam
        return False
    return True

# Se não suporta cores, redefinir para strings vazias
if not supports_color():
    for attr in dir(TermColors):
        if not attr.startswith('__'):
            setattr(TermColors, attr, '')

def print_color(text, color=TermColors.BLUE, bold=False):
    """Imprime texto colorido no terminal."""
    prefix = TermColors.BOLD if bold else ''
    print(f"{prefix}{color}{text}{TermColors.ENDC}")

def check_pip():
    """Verifica se pip está instalado e funcionando corretamente."""
    try:
        subprocess.run([sys.executable, "-m", "pip", "--version"], 
                       check=True, capture_output=True, text=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        print_color("Erro: pip não encontrado ou não está funcionando corretamente.", TermColors.RED, True)
        print("Por favor, instale ou atualize o pip: https://pip.pypa.io/en/stable/installation/")
        return False

def install_package(package, verbose=True):
    """Instala um pacote Python usando pip."""
    if verbose:
        print_color(f"Instalando {package}...", TermColors.BLUE)
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", package],
            check=True,
            capture_output=not verbose,
            text=True
        )
        if verbose:
            print_color(f"{package} instalado com sucesso!", TermColors.GREEN)
        return True
    except subprocess.SubprocessError as e:
        print_color(f"Erro ao instalar {package}: {e}", TermColors.RED)
        if not verbose and hasattr(e, 'stdout'):
            print(e.stdout)
        if not verbose and hasattr(e, 'stderr'):
            print(e.stderr)
        return False

def install_from_requirements(req_file, verbose=True):
    """Instala pacotes a partir de um arquivo requirements.txt."""
    if verbose:
        print_color(f"Instalando dependências de {req_file}...", TermColors.BLUE, True)
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", req_file],
            check=True,
            capture_output=not verbose,
            text=True
        )
        if verbose:
            print_color("Todas as dependências instaladas com sucesso!", TermColors.GREEN, True)
        return True
    except subprocess.SubprocessError as e:
        print_color(f"Erro ao instalar dependências de {req_file}: {e}", TermColors.RED, True)
        if not verbose and hasattr(e, 'stdout'):
            print(e.stdout)
        if not verbose and hasattr(e, 'stderr'):
            print(e.stderr)
        return False

def create_requirements_subset(source_file, dest_file, categories):
    """
    Cria um subconjunto do arquivo requirements.txt com apenas as categorias especificadas.
    
    Args:
        source_file: Caminho para o arquivo requirements.txt original
        dest_file: Caminho para o arquivo de saída
        categories: Lista de categorias a incluir
    """
    current_category = None
    include_lines = []
    
    with open(source_file, 'r') as f:
        lines = f.readlines()
    
    for line in lines:
        line = line.rstrip()
        
        # Pular linhas vazias
        if not line.strip():
            continue
            
        # Verificar se é uma linha de comentário que define uma categoria
        if line.startswith('# ') and not line.startswith('# Versão:'):
            current_category = line[2:].split()[0].lower()  # Extrair nome da categoria
            
        # Se estamos em uma categoria de interesse, incluir a linha
        if current_category and any(cat.lower() in current_category.lower() for cat in categories):
            include_lines.append(line)
    
    # Escrever as linhas selecionadas no arquivo de destino
    with open(dest_file, 'w') as f:
        f.write('\n'.join(include_lines))
        f.write('\n')

def install_core_dependencies():
    """Instala as dependências essenciais para o projeto."""
    print_color("Instalando dependências essenciais...", TermColors.BLUE, True)
    
    # Lista de pacotes essenciais que devem estar instalados
    essential_packages = [
        "httpx",         # Para requisições HTTP assíncronas
        "supabase",      # Cliente Supabase
        "pydantic>=2.0.0", # Validação de dados (v2)
        "pydantic-settings", # Configurações para Pydantic v2
        "python-dotenv", # Carregamento de variáveis de ambiente
        "loguru",        # Logging aprimorado
    ]
    
    failed = []
    for package in essential_packages:
        if not install_package(package):
            failed.append(package)
    
    if failed:
        print_color(f"Falha ao instalar os seguintes pacotes: {', '.join(failed)}", TermColors.RED)
        print_color("Tente instalar manualmente ou resolva os problemas de dependência.", TermColors.YELLOW)
        return False
    
    print_color("Dependências essenciais instaladas com sucesso!", TermColors.GREEN, True)
    return True

def main():
    """Função principal para instalar dependências."""
    parser = argparse.ArgumentParser(description="Instalador de dependências para o Motor de Sinais ML")
    parser.add_argument("--all", action="store_true", help="Instalar todas as dependências")
    parser.add_argument("--core", action="store_true", help="Instalar apenas dependências essenciais")
    parser.add_argument("--ml", action="store_true", help="Instalar dependências de machine learning")
    parser.add_argument("--viz", action="store_true", help="Instalar dependências de visualização")
    parser.add_argument("--no-interactive", action="store_true", help="Modo não interativo (sem perguntas)")
    
    args = parser.parse_args()
    
    print_color("=" * 70, TermColors.YELLOW)
    print_color("  Instalador de Dependências do Motor de Sinais ML", TermColors.BLUE, True)
    print_color("=" * 70, TermColors.YELLOW)
    
    # Verificar se o pip está funcionando
    if not check_pip():
        sys.exit(1)
    
    # Obter caminho do diretório do motor
    motor_dir = Path(__file__).parent
    requirements_file = motor_dir / "requirements.txt"
    
    if not requirements_file.exists():
        print_color(f"Erro: Arquivo requirements.txt não encontrado em {motor_dir}", TermColors.RED, True)
        sys.exit(1)
    
    # Instalar dependências essenciais primeiro, independentemente da opção
    install_core_dependencies()
    
    # Se nenhuma opção específica for fornecida e não estiver no modo não interativo, perguntar ao usuário
    if not (args.all or args.core or args.ml or args.viz) and not args.no_interactive:
        print_color("\nEscolha uma opção de instalação:", TermColors.YELLOW)
        print("1. Instalar todas as dependências (pode levar alguns minutos)")
        print("2. Instalar apenas dependências essenciais (básicas + integração Supabase)")
        print("3. Instalar dependências essenciais + ML (sem visualização e desenvolvimento)")
        print("4. Instalar dependências essenciais + visualização (sem ML)")
        print("5. Sair sem instalar mais dependências")
        
        try:
            choice = int(input("\nSua escolha [1-5]: "))
            if choice == 1:
                args.all = True
            elif choice == 2:
                args.core = True
            elif choice == 3:
                args.core = True
                args.ml = True
            elif choice == 4:
                args.core = True
                args.viz = True
            elif choice == 5:
                print_color("Instalação de dependências adicionais cancelada.", TermColors.YELLOW)
                print_color("Dependências essenciais já foram instaladas.", TermColors.GREEN)
                return
            else:
                print_color("Opção inválida. Usando apenas dependências essenciais.", TermColors.YELLOW)
                args.core = True
        except ValueError:
            print_color("Entrada inválida. Usando apenas dependências essenciais.", TermColors.YELLOW)
            args.core = True
    
    # Criar um arquivo requirements temporário baseado nas opções
    temp_req_file = motor_dir / "temp_requirements.txt"
    
    # Se apenas --core foi especificado e já instalamos as dependências essenciais, estamos prontos
    if args.core and not (args.all or args.ml or args.viz):
        print_color("\nInstalação concluída! Você já tem as dependências essenciais.", TermColors.GREEN, True)
        return
    
    # Instalar dependências de acordo com as opções
    if args.all:
        print_color("\nInstalando todas as dependências do projeto...", TermColors.BLUE, True)
        install_from_requirements(requirements_file)
    else:
        categories = []
        
        if args.ml:
            print_color("\nInstalando dependências de Machine Learning...", TermColors.BLUE)
            categories.extend([
                "Análise técnica",
                "Machine Learning",
                "Processamento Assíncrono"
            ])
        
        if args.viz:
            print_color("\nInstalando dependências de Visualização...", TermColors.BLUE)
            categories.extend([
                "Visualização"
            ])
        
        # Sempre incluir dependências de teste básicas
        categories.append("Testes")
        
        if categories:
            create_requirements_subset(requirements_file, temp_req_file, categories)
            install_from_requirements(temp_req_file)
            
            # Limpar arquivo temporário
            if temp_req_file.exists():
                os.remove(temp_req_file)
    
    print_color("\nDependências instaladas com sucesso!", TermColors.GREEN, True)
    print_color("Você pode agora executar 'python run_setup.py' para configurar o Motor de Sinais ML.", TermColors.BLUE)

if __name__ == "__main__":
    main() 