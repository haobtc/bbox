import os, sys
import shlex
import signal
import logging
import json
import asyncio
import argparse
from aiobbox.utils import wakeup_sleep_tasks
from aiobbox.exceptions import Stop
import aiobbox.server as bbox_server
from aiobbox.cluster import get_box, get_cluster, get_ticket
from aiobbox.utils import import_module, wakeup_sleep_tasks
from aiobbox.handler import BaseHandler

logger = logging.getLogger('bbox')

class Handler(BaseHandler):
    help = 'run multiple bbox tasks'
    def add_arguments(self, parser):
        parser.add_argument(
            'taskspec',
            type=str,
            nargs='+',
            help='the task specs to load')

    async def run(self, args):
        cfg = get_ticket()
        if cfg.language != 'python3':
            print('language must be python3', file=sys.stderr)
            sys.exit(1)

        cors = []
        handlers = []
        for spec in args.taskspec:
            args = shlex.split(spec)
            module, task_params = args[0], args[1:]
            mod = import_module(module)
            if hasattr(mod, 'Handler'):
                handler = mod.Handler()
            else:
                handler = BaseHandler()

            parser = argparse.ArgumentParser(prog='bbox.py mrun {}'.format(module))
            handler.add_arguments(parser)
            sub_args = parser.parse_args(task_params)
            handlers.append(handler)
            cors.append(self.run_handler(handler, sub_args))

        loop = asyncio.get_event_loop()

        loop.add_signal_handler(
            signal.SIGINT,
            self.handle_stop_sig,
            handlers)

        try:
            await get_cluster().start()
            await asyncio.gather(*cors)
        finally:
            handler.shutdown()
            c = get_cluster()
            c.cont = False
            await asyncio.sleep(0.1)
            c.close()

    async def run_handler(self, handler, args):
        try:
            return await handler.run(args)
        finally:
            handler.shutdown()

    def handle_stop_sig(self, handlers):
        print('handle stop sig')
        try:
            logger.debug('sigint met, handlers %s should stop lately', handlers)
            for handler in handlers:
                handler.cont = False

            wakeup_sleep_tasks()
            loop = asyncio.get_event_loop()
            loop.remove_signal_handler(signal.SIGINT)
            loop.call_later(15, sys.exit, 0)  # force exit 15 seconds later
        except:
            logger.error('error on handle sigint', exc_info=True)
            raise
