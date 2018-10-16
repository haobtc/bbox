import os, sys
import logging
import uuid
import json
import asyncio

from aiobbox.cluster import get_cluster
from aiobbox.handler import BaseHandler

from .tunnel import RedisTunnel

class Handler(BaseHandler):
    help = 'start bbox tunnel backend'
    run_forever = True

    def add_arguments(self, parser):
        parser.add_argument(
            'url',
            type=str,
            help='tunnel url in the form of redis://xxx.com/req?ssl=fff')

        parser.add_argument(
            '--ttl',
            type=float,
            default=3600 * 24,  # one day
            help='time to live')

    async def run(self, args):
        # start cluster client
        await get_cluster().start()

        tunnel = RedisTunnel(args.url)
        asyncio.ensure_future(self.wait_ttl(args.ttl))

        await tunnel.take_jobs()

    async def wait_ttl(self, ttl):
        await asyncio.sleep(ttl)
        sys.exit(0)
