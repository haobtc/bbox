import sys
import asyncio
import urllib.parse as urlparse
from aiobbox.server import Service, ServiceError
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
    if not isinstance(msg, str):
        raise ServiceError('invalid arg',
                           'msg is not str')
    return 'echo {} from {} {}'.format(
        msg,
        curr_box.bind,
        curr_box.boxid
    )

@srv.method('web')
async def web(request, webreq):
    #raise ServiceError('400', 'bad')
    path = webreq['path']
    r = urlparse.parse_qs(webreq.get('qs', ''))
    body = '{} {}'.format(path, r)
    return {
        'headers': {'X-Move': 'dont move'},
        'body': {'aa': 1}
        }

srv.register('calc')

async def shutdown():
    print('calc shutdown')
