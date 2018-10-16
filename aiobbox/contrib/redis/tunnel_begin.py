import os, sys
import logging
import uuid
import json
import asyncio

from aiobbox.cluster import get_box, get_cluster
from aiobbox.handler import BaseHandler

from .tunnel import RedisTunnel

class Handler(BaseHandler):
    help = 'start bbox tunnel proxy'
    run_forever = True

    def add_arguments(self, parser):
        parser.add_argument(
            'url',
            type=str,
            help='tunnel url in the form of redis://xxx.com/req?ssl=fff')

        parser.add_argument(
            'srv_name',
            type=str,
            nargs='+',
            help='proxied services')

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
        if not args.boxid:
            args.boxid = uuid.uuid4().hex

        # start cluster client
        await get_cluster().start()

        tunnel = RedisTunnel(args.url)
        await tunnel.start_proxy_server(args)
        asyncio.ensure_future(self.wait_ttl(args.ttl))

    async def wait_ttl(self, ttl):
        await asyncio.sleep(ttl)
        logging.info('box ttl expired, stoping')
        await get_box().deregister()
        logging.info('box ttl expired, stoped')
        sys.exit(0)

    def shutdown(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(get_box().deregister())
