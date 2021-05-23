from typing import Dict, Any, List, Union, Iterable, Callable, Optional
from argparse import Namespace, ArgumentParser
import os, sys
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
    help = 'run bbox tasks'
    def add_arguments(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            'module',
            type=str,
            help='the task module to load')

        parser.add_argument(
            'task_params',
            type=str,
            nargs='*',
            help='task arguments')

    async def run(self, args: Namespace) -> None:
        ticket = get_ticket()
        if ticket.language != 'python3':
            print('language must be python3', file=sys.stderr)
            sys.exit(1)

        mod = import_module(args.module)

        if hasattr(mod, 'Handler'):
            handler = mod.Handler()
        else:
            handler = BaseHandler()

        loop = asyncio.get_event_loop()

        loop.add_signal_handler(
            signal.SIGINT,
            self.handle_stop_sig,
            handler)

        loop.add_signal_handler(
            signal.SIGTERM,
            self.handle_stop_sig,
            handler)

        loop.set_exception_handler(coroutine_exc_handler)

        parser = argparse.ArgumentParser(prog='bbox.py run')
        handler.add_arguments(parser)
        sub_args = parser.parse_args(args.task_params)
        try:
            await get_cluster().start()
            logger.info('task %s starts', args.module)
            r = await handler.run(sub_args)
            if r is not None:
                logger.debug('task return %s', r)
        finally:
            logger.info('task %s stopping', args.module)
            handler.shutdown()
            c = get_cluster()
            c.cont = False
            await asyncio.sleep(0.1)
            c.close()

    def handle_stop_sig(self, handler: BaseHandler) -> None:
        try:
            logger.debug('sigint met, the handle %s should stop lately', handler)
            get_cluster().stop()
            handler.cont = False
            wakeup_sleep_tasks()
            loop = asyncio.get_event_loop()
            loop.remove_signal_handler(signal.SIGINT)
            loop.remove_signal_handler(signal.SIGTERM)
            exit_after = int(os.getenv('BBOX_TASK_EXIT_WAIT', 10))
            loop.call_later(exit_after, sys_exit)  # force exit10 or env defined seconds later
        except:
            logger.error('error on handle sigint', exc_info=True)
            raise

def sys_exit() -> None:
    sys.exit(0)

def coroutine_exc_handler(loop, context):
    loop.default_exception_handler(context)
    exc = context.get('exception')
    logger.error('coroutine exception %s context %s', exc, context)
    if exc and os.getenv('BBOX_COR_EXIT', '').lower() in ('1', 'yes', 'ok', 'true'):
        loop.stop()
