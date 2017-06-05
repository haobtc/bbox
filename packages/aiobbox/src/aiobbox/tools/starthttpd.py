import os, sys
import uuid
import json
import asyncio
import argparse
import aiobbox.server as bbox_server
from aiobbox.cluster import get_box, get_cluster
from aiobbox.cluster import get_ticket
from aiobbox.utils import import_module

parser = argparse.ArgumentParser(
    prog='bbox httpd',
    description='start bbox python project')

parser.add_argument(
    'handler',
    type=str,
    help='service::method to handle http request')

parser.add_argument(
    '--bind',
    type=str,
    default='127.0.0.1:28080',
    help='the box service module to load')

parser.add_argument(
    '--boxid',
    type=str,
    default='',
    help='box id')


httpd_mod = None
async def main():
    global httpd_mod

    args = parser.parse_args()
    if not args.boxid:
        args.boxid = uuid.uuid4().hex

    # start cluster client
    await get_cluster().start()
    src, handler = await bbox_server.http_server(args.boxid)
    
    httpd_mod = import_module('aiobbox.services.httpd')
    await httpd_mod.start(handler=args.handler,
                          bind=args.bind)
    return handler

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    handler = loop.run_until_complete(main())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        if httpd_mod:
            httpd_mod.shutdown()
        loop.run_until_complete(get_box().deregister())
        loop.run_until_complete(handler.finish_connections())
