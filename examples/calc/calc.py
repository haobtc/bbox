import sys
import asyncio
from aiotup.server import Service
import aiotup.discovery as discovery

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
    
    return 'echooo {} from {}'.format(
        msg,
        discovery.server_agent.bind)
