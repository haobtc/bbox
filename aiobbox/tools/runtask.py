import os, sys
import logging
import uuid
import json
import asyncio
import argparse

from aiobbox.exceptions import Stop
import aiobbox.server as bbox_server
from aiobbox.cluster import get_box, get_cluster, get_ticket
from aiobbox.utils import import_module
from aiobbox.handler import BaseHandler

logger = logging.getLogger('bbox')

class Handler(BaseHandler):
    help = 'run bbox tasks'
    def add_arguments(self, parser):
        parser.add_argument(
            'module',
            type=str,
            help='the task module to load')

        parser.add_argument(
            'task_params',
            type=str,
            nargs='*',
            help='task arguments')

    async def run(self, args):
        cfg = get_ticket()
        if cfg.language != 'python3':
            print('language must be python3', file=sys.stderr)
            sys.exit(1)

        mod = import_module(args.module)

        if hasattr(mod, 'Handler'):
            handler = mod.Handler()
        else:
            handler = BaseHandler()

        parser = argparse.ArgumentParser(prog='bbox.py run')
        handler.add_arguments(parser)
        sub_args = parser.parse_args(args.task_params)
        try:
            await get_cluster().start()
            r = await handler.run(sub_args)
            if r:
                logger.debug('task return %s', r)
        finally:
            c = get_cluster()
            c.cont = False
            await asyncio.sleep(0.1)
            c.close()

