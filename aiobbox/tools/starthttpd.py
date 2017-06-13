import os, sys
import ssl
import logging
import uuid
import json
import asyncio
import argparse
import aiobbox.server as bbox_server
from aiobbox.cluster import get_box, get_cluster
from aiobbox.cluster import get_ticket
from aiobbox.utils import import_module, abs_path

parser = argparse.ArgumentParser(
    prog='bbox httpd',
    description='start bbox python project')

parser.add_argument(
    'module',
    type=str,
    help='python module to custom apps')

parser.add_argument(
    '--bind',
    type=str,
    default='127.0.0.1:28080',
    help='the box service module to load')

parser.add_argument(
    '--ssl',
    type=str,
    default='',
    help='ssl prefix, the files certs/$prefix.crt and certs/$prefix.key must exist if specified')

parser.add_argument(
    '--boxid',
    type=str,
    default='',
    help='box id')

httpd_mod = None
async def main():
    global httpd_mod

    args, _ = parser.parse_known_args()
    if not args.boxid:
        args.boxid = uuid.uuid4().hex

    ssl_context = None
    if args.ssl:
        ssl_cert = abs_path(
            'certs/{}.crt'.format(args.ssl))
        ssl_key = abs_path(
            'certs/{}.key'.format(args.ssl))
        ssl_context = ssl.create_default_context(
            ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(
            ssl_cert, ssl_key)

    # start cluster client and box
    await get_cluster().start()

    httpd_mod = import_module(args.module)
    http_app = await httpd_mod.get_app(bind=args.bind)

    _, handler = await bbox_server.http_server(args.boxid)

    http_handler = http_app.make_handler()

    host, port = args.bind.split(':')
    logging.warn('httpd starts at %s', args.bind)
    loop = asyncio.get_event_loop()


    await loop.create_server(http_handler,
                             host, port,
                             ssl=ssl_context)

    if hasattr(httpd_mod, 'start'):
        await httpd_mod.start()

    return handler, httpd_mod, http_handler

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    handler, httpd_mod, http_handler = loop.run_until_complete(main())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        if hasattr(httpd_mod, 'shutdown'):
            loop.run_until_complete(httpd_mod.shutdown())
        loop.run_until_complete(get_box().deregister())
        loop.run_until_complete(handler.finish_connections())
        loop.run_until_complete(http_handler.finish_connections())
