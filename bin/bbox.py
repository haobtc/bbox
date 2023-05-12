#!/usr/bin/env python3
from typing import Optional, List
import sys
import logging
import signal
import signal
from argparse import ArgumentParser, Namespace
import asyncio
from aiobbox.log import config_log
from aiobbox.sentry import setup_sentry
from aiobbox.handler import BaseHandler
from aiobbox.utils import import_module

sys.path.append('.')

config_log()

sub_modules = [
    ('init', 'aiobbox.tools.initprj'),
    ('start', 'aiobbox.tools.startbox'),
    ('httpd', 'aiobbox.tools.starthttpd'),
    ('run', 'aiobbox.tools.runtask'),
    ('mrun', 'aiobbox.tools.runmultitasks'),
    ('ps', 'aiobbox.tools.ps'),
    ('rpc', 'aiobbox.tools.rpcclient'),
    ('config', 'aiobbox.tools.clusterconfig'),
    ('cluster', 'aiobbox.tools.clusterop'),
    ('printticket', 'aiobbox.tools.printticket'),
    ('doc', 'aiobbox.tools.printdoc'),
    ('metrics', 'aiobbox.tools.metrics'),
    ('tunnel.begin', 'aiobbox.contrib.redis.tunnel_begin'),
    ('tunnel.end', 'aiobbox.contrib.redis.tunnel_end')
    ]

def main():
    setup_sentry()

    top_parser = ArgumentParser(
        prog='bbox.py',
        description="bixin's micro services toolkit")

    sub_parsers = top_parser.add_subparsers(
        help='sub-command help')

    for sub_cmd, mod_name in sub_modules:
        mod = import_module(mod_name)

        assert issubclass(mod.Handler, BaseHandler)

        handler = mod.Handler()
        help_msg = getattr(handler, 'help', '')
        parser = sub_parsers.add_parser(sub_cmd, help=help_msg)
        handler.add_arguments(parser)
        parser.set_defaults(handler=handler)

    asyncio.run(_run(top_parser))

async def _run(top_parser:ArgumentParser, input_args:Optional[List[str]]=None) -> None:
    args = top_parser.parse_args(input_args)
    #loop = asyncio.get_event_loop()
    #loop = asyncio.get_running_loop()

    handler = getattr(args, 'handler', None)
    if handler is None:
        top_parser.print_help()
    else:
        #loop.call_later(0, handler.run(args))
        # loop.ensure_future(handler.run(args))
        # asyncio.add_signal_handler(
        #         signal.SIGTERM,
        #         on_term_sig)
        # loop = asyncio.get_running_loop()
        # loop.add_signal_handler(
        #         signal.SIGTERM, on_term_sig)
        try:
            await handler.run(args)
            if getattr(handler, 'run_forever', False):
                while True:
                    await asyncio.sleep(0.1)
        except KeyboardInterrupt:
            logger.info('keyboard interrupt')
        except RuntimeError as e:
            if 'Event loop stopped before Future completed' not in str(e):
                raise
        finally:
            cor = handler.shutdown()
            if asyncio.iscoroutine(cor):
                await cor

def on_term_sig():
    raise KeyboardInterrupt()

if __name__ == '__main__':
    main()
