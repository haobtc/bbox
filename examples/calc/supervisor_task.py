import asyncio
import random
from aiobbox.handler import BaseHandler
from aiobbox.utils import sleep, supervised_run
from aiobbox.cluster import get_cluster

"""
run task
bbox.py run supervisor_task
"""

class MyError(Exception):
    pass

class Handler(BaseHandler):
    async def mytask(self, i):
        print('begin task', i)
        await sleep(2 * random.random())
        print('end task', i)
        raise MyError('bad')

    async def run(self, args):
        for i in range(10, 20):
            supervised_run(self.mytask, args=(i,), exc=MyError)
        await sleep(20)


