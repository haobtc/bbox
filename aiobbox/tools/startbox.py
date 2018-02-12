import os, sys
import logging
import uuid
import json
import asyncio
import argparse
import aiobbox.server as bbox_server
from aiobbox.cluster import get_box, get_cluster
from aiobbox.cluster import get_ticket
from aiobbox.utils import import_module
from aiobbox.handler import BaseHandler

class Handler(BaseHandler):
    help = 'start bbox python project'
    run_forever = True

    def add_arguments(self, parser):
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

        parser.add_argument(
            '--ttl',
            type=float,
            default=3600 * 24,  # one day
            help='time to live')

    async def run(self, args):
        cfg = get_ticket()
        if cfg.language != 'python3':
            print('language must be python3', file=sys.stderr)
            sys.exit(1)

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
        self.handler = handler
        self.mod_handlers = mod_handlers

        asyncio.ensure_future(self.wait_ttl(args.ttl))

    async def wait_ttl(self, ttl):
        await asyncio.sleep(ttl)
        logging.warn('box ttl expired, stop')
        sys.exit(0)

    def shutdown(self):
        loop = asyncio.get_event_loop()
        for h in self.mod_handlers:
            h.shutdown()
        loop.run_until_complete(get_box().deregister())
        #loop.run_until_complete(
        #    self.handler.finish_connections())
