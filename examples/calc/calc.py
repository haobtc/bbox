import sys
import asyncio
from aiobbox.server import Service
from aiobbox.cluster import BoxAgent

srv = Service('calc')

@srv.method('add2num')
async def add2num(request, a, b):
    return a + b

@srv.method('add2sleep')
async def add2sleep(request, a, b, sec):
    await asyncio.sleep(sec)
    return a + b

@srv.method('echostr')
async def echostr(request, msg):
    return 'echo {} from {} {}'.format(
        msg,
        BoxAgent.agent.bind,
        BoxAgent.agent.boxid
    )
