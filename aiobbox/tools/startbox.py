from typing import Dict, Any, List, Union, Iterable, Set
import os, sys
import logging
import uuid
import json
import asyncio
from argparse import Namespace, ArgumentParser
import aiobbox.server as bbox_server
from aiobbox.cluster import get_box, get_cluster
from aiobbox.cluster import get_ticket
from aiobbox.utils import import_module
from aiobbox.handler import BaseHandler

class Handler(BaseHandler):
    help = 'start bbox python project'
    run_forever:bool = True

    def add_arguments(self, parser: ArgumentParser) -> None:
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
            '--port',
            type=str,
            default='',
            help='custom port instead of using ticket')

        parser.add_argument(
            '--bind_ip',
            type=str,
            default='',
            help='custom bind_ip instead of using ticket')

        parser.add_argument(
            '--extbind',
            type=str,
            default='',
            help='external visible bind instead of using ticket')

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

    async def run(self, args: Namespace) -> None:
        if get_ticket().language != 'python3':
            print('language must be python3', file=sys.stderr)
            sys.exit(1)

        if not args.boxid:
            args.boxid = uuid.uuid4().hex

        loop = asyncio.get_event_loop()
        loop.set_exception_handler(coroutine_exc_handler)

        mod_handlers = []
        for modspec in args.module:
            mod = import_module(modspec)

            if hasattr(mod, 'Handler'):
                mod_handlers.append(mod.Handler())
            else:
                mod_handlers.append(BaseHandler())

        # start cluster client
        await get_cluster().start()
        src, handler = await bbox_server.start_server(
            args, port=args.port,
            bind_ip=args.bind_ip,
            extbind=args.extbind)
        self.mod_handlers = mod_handlers
        for h in mod_handlers:
            await h.start(args)
        self.handler = handler


        asyncio.ensure_future(self.wait_ttl(args.ttl))

    async def wait_ttl(self, ttl:float) -> None:
        await asyncio.sleep(ttl)
        logging.info('box ttl expired, stoping')
        await get_box().deregister()
        logging.info('box ttl expired, stoped')
        sys.exit(0)

    def shutdown(self) -> None:
        loop = asyncio.get_event_loop()
        for h in self.mod_handlers:
            h.shutdown()
        loop.run_until_complete(get_box().deregister())

def coroutine_exc_handler(loop, context):
    loop.default_exception_handler(context)
    exc = context.get('exception')
    logging.error('coroutine exception %s context %s', exc, context)
    if exc and os.getenv('BBOX_COR_EXIT', '').lower() in ('1', 'yes', 'ok', 'true'):
        loop.stop()
