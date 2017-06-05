import os, sys
import uuid
import json
import asyncio
import argparse
import aiobbox.server as bbox_server
from aiobbox.cluster import get_box, get_cluster
from aiobbox.cluster import get_localconfig
from aiobbox.utils import import_module

parser = argparse.ArgumentParser(
    prog='bbox start',
    description='start bbox python project')

parser.add_argument(
    'module',
    type=str,
    nargs='+',
    help='the box service module to load')

parser.add_argument(
    '--boxid',
    type=str,
    default='',
    help='box id')

async def main():
    cfg = get_localconfig()
    if cfg.language != 'python3':
        print('language must be python3', file=sys.stderr)
        sys.exit(1)
    args = parser.parse_args()
    if not args.boxid:
        args.boxid = uuid.uuid4().hex

    # start cluster client
    await get_cluster().start()

    shutdown_handlers = []
    for modspec in args.module:
        mod = import_module(modspec)
        shutdown = getattr(mod, 'shutdown', None)
        if shutdown:
            shutdown_handlers.append(shutdown)

    src, handler = await bbox_server.http_server(args.boxid)
    return handler, shutdown_handlers

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    handler, shutdown_handlers = loop.run_until_complete(main())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        if shutdown_handlers:
            for shutdown in shutdown_handlers:
                loop.run_until_complete(
                    asyncio.wait_for(
                        shutdown(),
                        timeout=2))
        loop.run_until_complete(get_box().deregister())
        loop.run_until_complete(handler.finish_connections())
