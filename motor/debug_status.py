import asyncio
from src.main_integrated import IntegratedSystem

async def test():
    system = IntegratedSystem()
    await system.initialize()
    status = await system.collector_manager.get_orchestration_status()
    print('Status keys:', list(status.keys()))
    print('Full status:', status)
    await system.close()

if __name__ == "__main__":
    asyncio.run(test())