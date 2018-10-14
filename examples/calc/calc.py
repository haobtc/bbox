import sys
import asyncio
import urllib.parse as urlparse
from aiobbox.server import Service, ServiceError, Request
from aiobbox.cluster import get_box
from aiobbox.utils import sleep

srv = Service()
def _add2num(a:int, b:int) -> int:
    return a + b

@srv.method('add2num')
async def add2num(request, a, b):
    return _add2num(a, b)

@srv.method('add2sleep')
async def add2sleep(request, a, b, sec):
    await sleep(sec)
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
    def getval(d, key):
        a = d.get(key)
        if a:
            return a[0]

    path = webreq['path']
    r = urlparse.parse_qs(webreq.get('qs', ''))
    a = getval(r, 'a')
    b = getval(r, 'b')
    if a and a.isdigit() and b and b.isdigit():
        res = int(a) + int(b)
    else:
        raise ServiceError('400', 'Bad argument')
    return {
        'headers': {'X-Move': 'dont move'},
        'body': {'path': path,
                 'qs': r,
                 'headers': webreq['headers'],
                 'res': res}}

srv.register('calc')

async def shutdown():
    print('calc shutdown')
