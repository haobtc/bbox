import os, sys
import logging
import uuid
import json
import asyncio
import argparse
from aiobbox.log import config_log
import aiobbox.server as bbox_server
from aiobbox.cluster import get_box, get_cluster
from aiobbox.cluster import get_ticket
from aiobbox.utils import import_module, get_ssl_context
from aiobbox.handler import BaseHandler

config_log()

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
    help='ssl prefix, the files certs/$prefix/$prefix.crt and certs/$prefix/$prefix.key must exist if specified')

parser.add_argument(
    '--boxid',
    type=str,
    default='',
    help='box id')

async def main():
    # start cluster client and box
    args, _ = parser.parse_known_args()
    httpd_mod = import_module(args.module)
    if hasattr(httpd_mod, 'Handler'):
        assert issubclass(httpd_mod.Handler, BaseHandler)
        mod_handler = httpd_mod.Handler()
    else:
        mod_handler = BaseHandler()
    mod_handler.add_arguments(parser)

    args = parser.parse_args()
    if not args.boxid:
        args.boxid = uuid.uuid4().hex

    ssl_context = get_ssl_context(args.ssl)
    await get_cluster().start()

    http_app = await mod_handler.get_app(args)
    _, handler = await bbox_server.start_server(args)

    http_handler = http_app.make_handler()

    host, port = args.bind.split(':')
    logging.warn('httpd starts at %s', args.bind)
    loop = asyncio.get_event_loop()
    await loop.create_server(http_handler,
                             host, port,
                             ssl=ssl_context)
    await mod_handler.start(args)
    return handler, mod_handler, http_handler

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    handler, mod_handler, http_handler = loop.run_until_complete(main())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        mod_handler.shutdown()
        loop.run_until_complete(
            get_box().deregister())
        loop.run_until_complete(
            handler.finish_connections())
        loop.run_until_complete(
            http_handler.finish_connections())
