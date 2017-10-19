#!/usr/bin/env python3
import argparse
import asyncio
from aiobbox.handler import BaseHandler
from aiobbox.utils import import_module

sub_modules = [
    ('init', 'aiobbox.tools.initprj'),
    ('start', 'aiobbox.tools.startbox'),
    ('httpd', 'aiobbox.tools.starthttpd'),
    ('run', 'aiobbox.tools.runtask'),
    ('rpc', 'aiobbox.tools.rpcclient'),
    ('config', 'aiobbox.tools.clusterconfig'),
    ('cluster', 'aiobbox.tools.clusterop'),
    ('lock', 'aiobbox.tools.watchlock'),
    ('printticket', 'aiobbox.tools.printticket'),
    ('doc', 'aiobbox.tools.printdoc')
    ]

def main():
    top_parser = argparse.ArgumentParser(
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

    args = top_parser.parse_args()
    loop = asyncio.get_event_loop()
    handler = getattr(args, 'handler', None)
    if handler is None:
        top_parser.print_help()
    else:
        loop.run_until_complete(handler.run(args))
        if getattr(handler, 'run_forever', False):
            try:
                loop.run_forever()
            except KeyboardInterrupt:
                handler.shutdown()
        else:
            handler.shutdown()

if __name__ == '__main__':
    main()
