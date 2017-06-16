import asyncio
from aiobbox.cluster import get_cluster
from aiobbox.client import pool
from aiobbox.handler import BaseHandler

class Handler(BaseHandler):
    async def run(self, args):
        for _ in range(2):
            r = await pool.calc.echostr('888', retry=100)
            print(r)
            await asyncio.sleep(3)
