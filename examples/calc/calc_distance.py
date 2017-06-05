import asyncio
from aiobbox.cluster import get_cluster
from aiobbox.client import pool

async def run():
    for _ in range(2):
        r = await pool.calc.echostr.options(retry=100)('888')
        print(r)
        await asyncio.sleep(3)
