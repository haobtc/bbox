import asyncio
from aiobbox.cluster import get_cluster
from aiobbox.client import pool as srv_pool
from aiobbox.handler import BaseHandler

class Handler(BaseHandler):
    def add_arguments(self, parser):
        parser.add_argument('--a',
                           type=float)

        parser.add_argument('--b',
                           type=float)

    async def run(self, args):
        #for _ in range(2):
            #r = await pool.calc.echostr('888', retry=100)
         #   print(r)
         #   await asyncio.sleep(3)
        r = await srv_pool.calc.add2num(args.a, args.b)
        print(r)

