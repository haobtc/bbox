from aiohaorpc.server import Service

srv = Service('calc')

@srv.method('add2num')
async def add2num(request, a, b):
    return a + b
