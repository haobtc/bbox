import asyncio
from aiotup.server import Service

srv = Service('calc')

@srv.method('add2num')
async def add2num(request, a, b):
    return a + b

@srv.method('add2sleep')
async def add2sleep(request, a, b, sec):
    await asyncio.sleep(sec)
    return a + b
