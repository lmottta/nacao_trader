import asyncio
from src.main_integrated import IntegratedSystem

async def test():
    system = IntegratedSystem()
    await system.initialize()
    fallback_status = await system.fallback_system.get_fallback_status()
    print('Fallback status keys:', list(fallback_status.keys()))
    print('Full fallback status:', fallback_status)
    await system.close()

if __name__ == "__main__":
    asyncio.run(test())