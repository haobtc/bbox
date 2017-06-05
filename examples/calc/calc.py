import sys
import asyncio
from aiobbox.server import Service
from aiobbox.cluster import get_box

srv = Service()

@srv.method('add2num')
async def add2num(request, a, b):
    return a + b

@srv.method('add2sleep')
async def add2sleep(request, a, b, sec):
    await asyncio.sleep(sec)
    return a + b

@srv.method('echostr')
async def echostr(request, msg):
    curr_box = get_box()
    return 'echo {} from {} {}'.format(
        msg,
        curr_box.bind,
        curr_box.boxid
    )

srv.register('calc')

async def shutdown():
    print('calc shutdown')
