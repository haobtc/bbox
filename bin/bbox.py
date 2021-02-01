#!/usr/bin/env python3
from typing import Optional, List
import sys
import os
import logging
import signal
import signal
from argparse import ArgumentParser, Namespace
import asyncio
from aiobbox.log import config_log
from aiobbox.handler import BaseHandler
from aiobbox.utils import import_module
import sentry_sdk
from sentry_sdk.integrations.aiohttp import AioHttpIntegration

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

    run(top_parser)

def run(top_parser:ArgumentParser, input_args:Optional[List[str]]=None) -> None:
    args = top_parser.parse_args(input_args)
    loop = asyncio.get_event_loop()

    sentry_url = os.environ.get('SENTRY_URL')
    if sentry_url:
        sentry_sdk.init(
              dsn=sentry_url,
              integrations=[AioHttpIntegration()]
        )

    handler = getattr(args, 'handler', None)
    if handler is None:
        top_parser.print_help()
    else:
        loop.add_signal_handler(
            signal.SIGTERM,
            on_term_sig)

        try:
            loop.run_until_complete(handler.run(args))
            if getattr(handler, 'run_forever', False):
                loop.run_forever()
        except KeyboardInterrupt:
            pass
        except RuntimeError as e:
            if 'Event loop stopped before Future completed' not in str(e):
                raise
        handler.shutdown()

def on_term_sig():
    raise KeyboardInterrupt()

if __name__ == '__main__':
    main()
