import os, sys
import uuid
import json
import asyncio
import argparse
import aiobbox.server as bbox_server
from aiobbox.cluster import get_box, get_cluster
from aiobbox.cluster import get_ticket
from aiobbox.utils import import_module
from aiobbox.handler import BaseHandler

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

parser.add_argument(
    '--ssl',
    type=str,
    default='',
    help='ssl prefix, the files certs/$prefix/$prefix.crt and certs/$prefix/$prefix.key must exist if specified')

async def main():
    cfg = get_ticket()
    if cfg.language != 'python3':
        print('language must be python3', file=sys.stderr)
        sys.exit(1)
    args, _ = parser.parse_known_args()
    if not args.boxid:
        args.boxid = uuid.uuid4().hex

    mod_handlers = []
    for modspec in args.module:
        mod = import_module(modspec)

        if hasattr(mod, 'Handler'):
            mod_handlers.append(mod.Handler())
        else:
            mod_handlers.append(BaseHandler())

    # start cluster client
    await get_cluster().start()
    src, handler = await bbox_server.start_server(args)

    for h in mod_handlers:
        await h.start(args)
    return handler, mod_handlers

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    handler, mod_handlers = loop.run_until_complete(main())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        for h in mod_handlers:
            h.shutdown()
        loop.run_until_complete(get_box().deregister())
        loop.run_until_complete(handler.finish_connections())
