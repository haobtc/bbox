import os, sys
import uuid
import json
import asyncio
import argparse
import aiobbox.server as bbox_server
from aiobbox.cluster import get_box, get_cluster, get_localconfig

parser = argparse.ArgumentParser(
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

def main():
    cfg = get_localconfig()
    if cfg.language != 'python3':
        print('language must be python3', file=sys.stderr)
        sys.exit(1)
    args = parser.parse_args()
    if not args.boxid:
        args.boxid = uuid.uuid4().hex
    for mod in args.module:
        __import__(mod)

    loop = asyncio.get_event_loop()
    r = bbox_server.http_server(args.boxid, loop=loop)
    srv, handler = loop.run_until_complete(r)

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        loop.run_until_complete(get_box().deregister())
        loop.run_until_complete(handler.finish_connections())


if __name__ == '__main__':
    main()
