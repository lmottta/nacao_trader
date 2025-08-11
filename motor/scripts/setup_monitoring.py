#!/usr/bin/env python3
"""Script para configuração inicial do ambiente de monitoramento do Nação Trader."""

import os
import sys
import subprocess
import time
import requests
import json
from pathlib import Path
from typing import Dict, List, Optional


class MonitoringSetup:
    """Classe para configuração do ambiente de monitoramento."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.config_dir = self.project_root / "config"
        self.docker_compose_file = self.project_root / "docker-compose.monitoring.yml"
        
        # URLs dos serviços
        self.services = {
            "prometheus": "http://localhost:9090",
            "grafana": "http://localhost:3000",
            "alertmanager": "http://localhost:9093",
            "pushgateway": "http://localhost:9091",
            "redis": "redis://localhost:6379"
        }
    
    def check_prerequisites(self) -> bool:
        """Verifica se os pré-requisitos estão instalados."""
        print("🔍 Verificando pré-requisitos...")
        
        # Verificar Docker
        try:
            result = subprocess.run(["docker", "--version"], 
                                   capture_output=True, text=True, check=True)
            print(f"✅ Docker: {result.stdout.strip()}")
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ Docker não encontrado. Instale o Docker primeiro.")
            return False
        
        # Verificar Docker Compose
        try:
            result = subprocess.run(["docker", "compose", "version"], 
                                   capture_output=True, text=True, check=True)
            print(f"✅ Docker Compose: {result.stdout.strip()}")
        except subprocess.CalledProcessError:
            try:
                result = subprocess.run(["docker-compose", "--version"], 
                                       capture_output=True, text=True, check=True)
                print(f"✅ Docker Compose: {result.stdout.strip()}")
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("❌ Docker Compose não encontrado.")
                return False
        
        # Verificar arquivos de configuração
        required_files = [
            self.config_dir / "prometheus.yml",
            self.config_dir / "alert_rules.yml",
            self.config_dir / "alertmanager.yml",
            self.config_dir / "blackbox.yml",
            self.config_dir / "grafana_dashboard.json",
            self.docker_compose_file
        ]
        
        for file_path in required_files:
            if file_path.exists():
                print(f"✅ {file_path.name}")
            else:
                print(f"❌ {file_path.name} não encontrado")
                return False
        
        return True
    
    def create_directories(self) -> None:
        """Cria diretórios necessários."""
        print("📁 Criando diretórios...")
        
        directories = [
            self.project_root / "data" / "prometheus",
            self.project_root / "data" / "grafana",
            self.project_root / "data" / "alertmanager",
            self.project_root / "data" / "redis",
            self.project_root / "logs"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            print(f"✅ {directory}")
    
    def start_services(self) -> bool:
        """Inicia os serviços de monitoramento."""
        print("🚀 Iniciando serviços de monitoramento...")
        
        try:
            # Parar serviços existentes
            subprocess.run(["docker", "compose", "-f", str(self.docker_compose_file), "down"],
                          cwd=self.project_root, check=False)
            
            # Iniciar serviços
            result = subprocess.run(
                ["docker", "compose", "-f", str(self.docker_compose_file), "up", "-d"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            
            print("✅ Serviços iniciados com sucesso")
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"❌ Erro ao iniciar serviços: {e}")
            print(f"Saída: {e.stdout}")
            print(f"Erro: {e.stderr}")
            return False
    
    def wait_for_services(self) -> None:
        """Aguarda os serviços ficarem disponíveis."""
        print("⏳ Aguardando serviços ficarem disponíveis...")
        
        for service_name, url in self.services.items():
            if service_name == "redis":
                continue  # Redis será verificado separadamente
            
            print(f"Verificando {service_name}...")
            max_attempts = 30
            attempt = 0
            
            while attempt < max_attempts:
                try:
                    response = requests.get(f"{url}/api/v1/status/config" if service_name == "prometheus" 
                                          else f"{url}/api/health" if service_name == "grafana"
                                          else f"{url}/-/healthy" if service_name == "alertmanager"
                                          else url, timeout=5)
                    
                    if response.status_code in [200, 401]:  # 401 pode ser esperado para Grafana
                        print(f"✅ {service_name} está disponível")
                        break
                        
                except requests.exceptions.RequestException:
                    pass
                
                attempt += 1
                time.sleep(2)
            
            if attempt >= max_attempts:
                print(f"⚠️ {service_name} pode não estar totalmente disponível")
    
    def configure_grafana(self) -> bool:
        """Configura o Grafana com datasources e dashboards."""
        print("📊 Configurando Grafana...")
        
        grafana_url = self.services["grafana"]
        auth = ("admin", "admin123")
        
        # Aguardar Grafana estar pronto
        max_attempts = 30
        for attempt in range(max_attempts):
            try:
                response = requests.get(f"{grafana_url}/api/health", timeout=5)
                if response.status_code == 200:
                    break
            except requests.exceptions.RequestException:
                pass
            time.sleep(2)
        else:
            print("❌ Grafana não está respondendo")
            return False
        
        # Configurar datasource do Prometheus
        datasource_config = {
            "name": "Prometheus",
            "type": "prometheus",
            "url": self.services["prometheus"],
            "access": "proxy",
            "isDefault": True,
            "basicAuth": False
        }
        
        try:
            response = requests.post(
                f"{grafana_url}/api/datasources",
                json=datasource_config,
                auth=auth,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code in [200, 409]:  # 409 = já existe
                print("✅ Datasource Prometheus configurado")
            else:
                print(f"⚠️ Erro ao configurar datasource: {response.text}")
        
        except requests.exceptions.RequestException as e:
            print(f"❌ Erro ao conectar com Grafana: {e}")
            return False
        
        # Importar dashboard
        dashboard_file = self.config_dir / "grafana_dashboard.json"
        if dashboard_file.exists():
            try:
                with open(dashboard_file, 'r', encoding='utf-8') as f:
                    dashboard_data = json.load(f)
                
                import_data = {
                    "dashboard": dashboard_data["dashboard"],
                    "overwrite": True,
                    "inputs": [
                        {
                            "name": "DS_PROMETHEUS",
                            "type": "datasource",
                            "pluginId": "prometheus",
                            "value": "Prometheus"
                        }
                    ]
                }
                
                response = requests.post(
                    f"{grafana_url}/api/dashboards/import",
                    json=import_data,
                    auth=auth,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    print("✅ Dashboard importado com sucesso")
                else:
                    print(f"⚠️ Erro ao importar dashboard: {response.text}")
            
            except Exception as e:
                print(f"❌ Erro ao processar dashboard: {e}")
        
        return True
    
    def test_metrics_endpoint(self) -> bool:
        """Testa se o endpoint de métricas da aplicação está funcionando."""
        print("🧪 Testando endpoint de métricas...")
        
        try:
            # Tentar conectar no endpoint de métricas da aplicação
            response = requests.get("http://localhost:8000/metrics", timeout=5)
            
            if response.status_code == 200:
                print("✅ Endpoint de métricas da aplicação está funcionando")
                return True
            else:
                print(f"⚠️ Endpoint retornou status {response.status_code}")
                
        except requests.exceptions.RequestException:
            print("⚠️ Endpoint de métricas da aplicação não está disponível")
            print("   Certifique-se de que a aplicação está rodando com métricas habilitadas")
        
        return False
    
    def show_access_info(self) -> None:
        """Mostra informações de acesso aos serviços."""
        print("\n" + "="*60)
        print("🎉 CONFIGURAÇÃO CONCLUÍDA!")
        print("="*60)
        print("\n📋 Informações de Acesso:")
        print(f"\n🔍 Prometheus: {self.services['prometheus']}")
        print("   - Métricas e consultas")
        print("   - Status dos targets")
        
        print(f"\n📊 Grafana: {self.services['grafana']}")
        print("   - Usuário: admin")
        print("   - Senha: admin123")
        print("   - Dashboards e visualizações")
        
        print(f"\n🚨 Alertmanager: {self.services['alertmanager']}")
        print("   - Gerenciamento de alertas")
        print("   - Status dos alertas")
        
        print(f"\n📤 Push Gateway: {self.services['pushgateway']}")
        print("   - Métricas batch")
        
        print("\n🔧 Comandos Úteis:")
        print(f"   Parar serviços: docker compose -f {self.docker_compose_file.name} down")
        print(f"   Ver logs: docker compose -f {self.docker_compose_file.name} logs -f")
        print(f"   Reiniciar: docker compose -f {self.docker_compose_file.name} restart")
        
        print("\n⚠️ Próximos Passos:")
        print("   1. Configure as credenciais de email no alertmanager.yml")
        print("   2. Configure o webhook do Slack (se necessário)")
        print("   3. Inicie a aplicação Nação Trader com métricas habilitadas")
        print("   4. Verifique se os targets estão UP no Prometheus")
    
    def run(self) -> None:
        """Executa a configuração completa."""
        print("🚀 Iniciando configuração do ambiente de monitoramento...\n")
        
        if not self.check_prerequisites():
            print("\n❌ Pré-requisitos não atendidos. Corrija os problemas e tente novamente.")
            sys.exit(1)
        
        self.create_directories()
        
        if not self.start_services():
            print("\n❌ Falha ao iniciar serviços.")
            sys.exit(1)
        
        self.wait_for_services()
        self.configure_grafana()
        self.test_metrics_endpoint()
        self.show_access_info()


def main():
    """Função principal."""
    setup = MonitoringSetup()
    setup.run()


if __name__ == "__main__":
    main()