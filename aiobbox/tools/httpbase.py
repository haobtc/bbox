import os, sys
import argparse
import logging
import uuid
import json
import asyncio
import aiobbox.server as bbox_server
from aiobbox.cluster import get_box, get_cluster
from aiobbox.cluster import get_ticket
from aiobbox.utils import import_module, get_ssl_context
from aiobbox.handler import BaseHandler

logger = logging.getLogger('bbox')

class Handler(BaseHandler):
    help = 'start bbox python httpd'
    run_forever = True
    mod_handle = None
    def add_arguments(self, parser):
        parser.add_argument(
            '--bind',
            type=str,
            default='127.0.0.1:28080',
            help='the box server bind')

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

    async def run(self, args):
        # start cluster client and box
        if not args.boxid:
            args.boxid = uuid.uuid4().hex

        ssl_context = get_ssl_context(args.ssl)
        await get_cluster().start()

        http_app = await self.get_app(args)
        _, handler = await bbox_server.start_server(args)

        http_handler = http_app.make_handler()

        host, port = args.bind.split(':')
        logger.warn('httpd starts at %s', args.bind)
        loop = asyncio.get_event_loop()
        await loop.create_server(http_handler,
                                 host, port,
                                 ssl=ssl_context)
        await self.start(args)
        self.handler = handler
        self.http_handler = http_handler

    async def get_app(self, args):
        raise NotImplemented

    def shutdown(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(get_box().deregister())
