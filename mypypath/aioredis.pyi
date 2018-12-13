from typing import Any

class Redis:
    async def execute(self, *commands, **kw) -> Any: ...
    
async def create_redis_pool(url:str, **kw) -> Redis:
    ...

