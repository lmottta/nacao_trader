#!/usr/bin/env python3
"""Script para iniciar o Dashboard de Monitoramento."""

import asyncio
import sys
import os

# Adicionar o diretório src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.dashboard.monitoring_dashboard import start_dashboard


async def main():
    """Função principal."""
    host = sys.argv[1] if len(sys.argv) > 1 else "localhost"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8080
    
    print(f"🚀 Iniciando Dashboard de Monitoramento do Nação Trader")
    print(f"📊 Acesse: http://{host}:{port}")
    print(f"🔄 WebSocket: ws://{host}:{port}/ws")
    print("\n" + "="*50)
    
    try:
        await start_dashboard(host, port)
    except KeyboardInterrupt:
        print("\n🛑 Dashboard interrompido pelo usuário")
    except Exception as e:
        print(f"❌ Erro ao iniciar dashboard: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())