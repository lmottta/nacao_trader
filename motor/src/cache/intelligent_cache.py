"""Sistema de Cache Inteligente Hierárquico para o Nação Trader.

Implementa um sistema de cache em múltiplas camadas:
- Memória (L1): Cache mais rápido para dados frequentemente acessados
- Redis (L2): Cache distribuído para dados compartilhados
- Disco (L3): Cache persistente para dados históricos
- Database (L4): Fonte de dados principal
"""

import asyncio
import json
import pickle
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import logging

import redis.asyncio as redis
from redis.exceptions import ConnectionError as RedisConnectionError

from ..utils.config import settings


class CacheLevel(Enum):
    """Níveis de cache disponíveis."""
    MEMORY = "memory"
    REDIS = "redis"
    DISK = "disk"
    DATABASE = "database"


@dataclass
class CacheEntry:
    """Entrada do cache com metadados."""
    key: str
    value: Any
    timestamp: float
    ttl: int  # Time to live em segundos
    access_count: int = 0
    last_access: float = 0
    size_bytes: int = 0
    level: CacheLevel = CacheLevel.MEMORY
    
    def is_expired(self) -> bool:
        """Verifica se a entrada expirou."""
        return time.time() - self.timestamp > self.ttl
    
    def update_access(self):
        """Atualiza estatísticas de acesso."""
        self.access_count += 1
        self.last_access = time.time()


class IntelligentCache:
    """Sistema de Cache Inteligente com múltiplas camadas."""
    
    def __init__(self, 
                 max_memory_size: int = 100 * 1024 * 1024,  # 100MB
                 max_disk_size: int = 1024 * 1024 * 1024,   # 1GB
                 redis_url: Optional[str] = None,
                 disk_cache_dir: Optional[str] = None):
        
        self.max_memory_size = max_memory_size
        self.max_disk_size = max_disk_size
        self.redis_url = redis_url or settings.REDIS_URL
        
        # Cache em memória
        self._memory_cache: Dict[str, CacheEntry] = {}
        self._memory_size = 0
        
        # Cliente Redis
        self._redis_client: Optional[redis.Redis] = None
        self._redis_available = False
        
        # Cache em disco
        self.disk_cache_dir = Path(disk_cache_dir or settings.DATA_DIR) / "cache"
        self.disk_cache_dir.mkdir(parents=True, exist_ok=True)
        self._disk_size = 0
        
        # Estatísticas
        self.stats = {
            "hits": {level.value: 0 for level in CacheLevel},
            "misses": {level.value: 0 for level in CacheLevel},
            "evictions": {level.value: 0 for level in CacheLevel},
            "total_requests": 0
        }
        
        # Logger
        self.logger = logging.getLogger(__name__)
        
    async def initialize(self):
        """Inicializa o sistema de cache."""
        await self._init_redis()
        self._calculate_disk_size()
        self.logger.info("Sistema de Cache Inteligente inicializado")
    
    async def _init_redis(self):
        """Inicializa conexão com Redis."""
        if not self.redis_url:
            self.logger.warning("Redis URL não configurada, cache Redis desabilitado")
            return
            
        try:
            self._redis_client = redis.from_url(self.redis_url)
            await self._redis_client.ping()
            self._redis_available = True
            self.logger.info("Conexão com Redis estabelecida")
        except Exception as e:
            self.logger.warning(f"Falha ao conectar com Redis: {e}")
            self._redis_available = False
    
    def _calculate_disk_size(self):
        """Calcula o tamanho atual do cache em disco."""
        self._disk_size = sum(
            f.stat().st_size for f in self.disk_cache_dir.rglob("*") if f.is_file()
        )
    
    def _generate_cache_key(self, key: str, namespace: str = "default") -> str:
        """Gera chave de cache com namespace."""
        return f"{namespace}:{hashlib.md5(key.encode()).hexdigest()}"
    
    async def get(self, key: str, namespace: str = "default") -> Optional[Any]:
        """Busca valor no cache hierárquico."""
        cache_key = self._generate_cache_key(key, namespace)
        self.stats["total_requests"] += 1
        
        # L1: Memória
        if cache_key in self._memory_cache:
            entry = self._memory_cache[cache_key]
            if not entry.is_expired():
                entry.update_access()
                self.stats["hits"][CacheLevel.MEMORY.value] += 1
                self.logger.debug(f"Cache hit (memória): {key}")
                return entry.value
            else:
                # Remove entrada expirada
                await self._evict_from_memory(cache_key)
        
        # L2: Redis
        if self._redis_available:
            try:
                redis_value = await self._redis_client.get(cache_key)
                if redis_value:
                    entry_data = json.loads(redis_value)
                    entry = CacheEntry(**entry_data)
                    
                    if not entry.is_expired():
                        # Promove para memória se houver espaço
                        await self._promote_to_memory(cache_key, entry)
                        self.stats["hits"][CacheLevel.REDIS.value] += 1
                        self.logger.debug(f"Cache hit (Redis): {key}")
                        return entry.value
                    else:
                        # Remove entrada expirada
                        await self._redis_client.delete(cache_key)
            except Exception as e:
                self.logger.warning(f"Erro ao acessar Redis: {e}")
        
        # L3: Disco
        disk_path = self.disk_cache_dir / f"{cache_key}.cache"
        if disk_path.exists():
            try:
                with open(disk_path, 'rb') as f:
                    entry = pickle.load(f)
                
                if not entry.is_expired():
                    # Promove para níveis superiores
                    await self._promote_to_redis(cache_key, entry)
                    await self._promote_to_memory(cache_key, entry)
                    self.stats["hits"][CacheLevel.DISK.value] += 1
                    self.logger.debug(f"Cache hit (disco): {key}")
                    return entry.value
                else:
                    # Remove arquivo expirado
                    disk_path.unlink()
            except Exception as e:
                self.logger.warning(f"Erro ao ler cache do disco: {e}")
        
        # Cache miss em todos os níveis
        self.stats["misses"][CacheLevel.DATABASE.value] += 1
        self.logger.debug(f"Cache miss: {key}")
        return None
    
    async def set(self, key: str, value: Any, ttl: int = 3600, namespace: str = "default"):
        """Armazena valor no cache hierárquico."""
        cache_key = self._generate_cache_key(key, namespace)
        
        # Calcula tamanho do valor
        try:
            value_size = len(pickle.dumps(value))
        except Exception:
            value_size = len(str(value).encode())
        
        entry = CacheEntry(
            key=cache_key,
            value=value,
            timestamp=time.time(),
            ttl=ttl,
            size_bytes=value_size,
            level=CacheLevel.MEMORY
        )
        
        # Armazena em todos os níveis disponíveis
        await self._store_in_memory(cache_key, entry)
        await self._store_in_redis(cache_key, entry)
        await self._store_in_disk(cache_key, entry)
        
        self.logger.debug(f"Valor armazenado no cache: {key}")
    
    async def _store_in_memory(self, cache_key: str, entry: CacheEntry):
        """Armazena entrada na memória."""
        # Verifica se há espaço suficiente
        while (self._memory_size + entry.size_bytes > self.max_memory_size and 
               self._memory_cache):
            await self._evict_lru_from_memory()
        
        self._memory_cache[cache_key] = entry
        self._memory_size += entry.size_bytes
    
    async def _store_in_redis(self, cache_key: str, entry: CacheEntry):
        """Armazena entrada no Redis."""
        if not self._redis_available:
            return
        
        try:
            # Serializa entrada (sem o valor para economizar espaço)
            entry_data = asdict(entry)
            entry_json = json.dumps(entry_data, default=str)
            
            await self._redis_client.setex(
                cache_key, 
                entry.ttl, 
                entry_json
            )
        except Exception as e:
            self.logger.warning(f"Erro ao armazenar no Redis: {e}")
    
    async def _store_in_disk(self, cache_key: str, entry: CacheEntry):
        """Armazena entrada no disco."""
        # Verifica se há espaço suficiente
        while (self._disk_size + entry.size_bytes > self.max_disk_size):
            await self._evict_lru_from_disk()
        
        try:
            disk_path = self.disk_cache_dir / f"{cache_key}.cache"
            with open(disk_path, 'wb') as f:
                pickle.dump(entry, f)
            
            self._disk_size += entry.size_bytes
        except Exception as e:
            self.logger.warning(f"Erro ao armazenar no disco: {e}")
    
    async def _promote_to_memory(self, cache_key: str, entry: CacheEntry):
        """Promove entrada para cache de memória."""
        if cache_key not in self._memory_cache:
            await self._store_in_memory(cache_key, entry)
    
    async def _promote_to_redis(self, cache_key: str, entry: CacheEntry):
        """Promove entrada para cache Redis."""
        if self._redis_available:
            await self._store_in_redis(cache_key, entry)
    
    async def _evict_from_memory(self, cache_key: str):
        """Remove entrada específica da memória."""
        if cache_key in self._memory_cache:
            entry = self._memory_cache.pop(cache_key)
            self._memory_size -= entry.size_bytes
            self.stats["evictions"][CacheLevel.MEMORY.value] += 1
    
    async def _evict_lru_from_memory(self):
        """Remove entrada menos recentemente usada da memória."""
        if not self._memory_cache:
            return
        
        # Encontra entrada com menor last_access
        lru_key = min(
            self._memory_cache.keys(),
            key=lambda k: self._memory_cache[k].last_access
        )
        
        await self._evict_from_memory(lru_key)
    
    async def _evict_lru_from_disk(self):
        """Remove entrada menos recentemente usada do disco."""
        cache_files = list(self.disk_cache_dir.glob("*.cache"))
        if not cache_files:
            return
        
        # Encontra arquivo mais antigo
        oldest_file = min(cache_files, key=lambda f: f.stat().st_mtime)
        file_size = oldest_file.stat().st_size
        
        oldest_file.unlink()
        self._disk_size -= file_size
        self.stats["evictions"][CacheLevel.DISK.value] += 1
    
    async def invalidate(self, key: str, namespace: str = "default"):
        """Invalida entrada em todos os níveis de cache."""
        cache_key = self._generate_cache_key(key, namespace)
        
        # Remove da memória
        if cache_key in self._memory_cache:
            await self._evict_from_memory(cache_key)
        
        # Remove do Redis
        if self._redis_available:
            try:
                await self._redis_client.delete(cache_key)
            except Exception as e:
                self.logger.warning(f"Erro ao invalidar no Redis: {e}")
        
        # Remove do disco
        disk_path = self.disk_cache_dir / f"{cache_key}.cache"
        if disk_path.exists():
            file_size = disk_path.stat().st_size
            disk_path.unlink()
            self._disk_size -= file_size
        
        self.logger.debug(f"Cache invalidado: {key}")
    
    async def clear_expired(self):
        """Remove todas as entradas expiradas."""
        current_time = time.time()
        
        # Limpa memória
        expired_keys = [
            key for key, entry in self._memory_cache.items()
            if entry.is_expired()
        ]
        for key in expired_keys:
            await self._evict_from_memory(key)
        
        # Limpa disco
        for cache_file in self.disk_cache_dir.glob("*.cache"):
            try:
                with open(cache_file, 'rb') as f:
                    entry = pickle.load(f)
                if entry.is_expired():
                    file_size = cache_file.stat().st_size
                    cache_file.unlink()
                    self._disk_size -= file_size
            except Exception:
                # Remove arquivos corrompidos
                cache_file.unlink()
        
        self.logger.info("Limpeza de cache expirado concluída")
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do cache."""
        total_hits = sum(self.stats["hits"].values())
        total_misses = sum(self.stats["misses"].values())
        hit_rate = total_hits / (total_hits + total_misses) if (total_hits + total_misses) > 0 else 0
        
        return {
            **self.stats,
            "hit_rate": hit_rate,
            "memory_usage": {
                "current_size": self._memory_size,
                "max_size": self.max_memory_size,
                "usage_percent": (self._memory_size / self.max_memory_size) * 100
            },
            "disk_usage": {
                "current_size": self._disk_size,
                "max_size": self.max_disk_size,
                "usage_percent": (self._disk_size / self.max_disk_size) * 100
            },
            "redis_available": self._redis_available,
            "entries_count": {
                "memory": len(self._memory_cache),
                "disk": len(list(self.disk_cache_dir.glob("*.cache")))
            }
        }
    
    async def close(self):
        """Fecha conexões e limpa recursos."""
        if self._redis_client:
            await self._redis_client.close()
        
        self.logger.info("Sistema de Cache Inteligente finalizado")


# Instância global do cache
_cache_instance: Optional[IntelligentCache] = None


async def get_cache() -> IntelligentCache:
    """Retorna instância global do cache."""
    global _cache_instance
    
    if _cache_instance is None:
        _cache_instance = IntelligentCache()
        await _cache_instance.initialize()
    
    return _cache_instance


async def close_cache():
    """Fecha instância global do cache."""
    global _cache_instance
    
    if _cache_instance:
        await _cache_instance.close()
        _cache_instance = None