from typing import Dict
import aioredis

_pools: Dict[str, aioredis.Redis] = {}
async def get_pool(url, **kw):
    if url not in _pools:
        pool = await aioredis.create_redis_pool(
            url, **kw)
        _pools[url] = pool
    return _pools[url]
