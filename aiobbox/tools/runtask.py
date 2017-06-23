import os, sys
import logging
import uuid
import json
import asyncio
import argparse
from aiobbox.log import config_log
import aiobbox.server as bbox_server
from aiobbox.cluster import get_box, get_cluster, get_ticket
from aiobbox.utils import import_module
from aiobbox.handler import BaseHandler

config_log()

parser = argparse.ArgumentParser(
    prog='bbox run',
    description='run bbox tasks')

parser.add_argument(
    'module',
    type=str,
    help='the task module to load')

async def main():
    cfg = get_ticket()
    if cfg.language != 'python3':
        print('language must be python3', file=sys.stderr)
        sys.exit(1)
    args, _ = parser.parse_known_args()
    mod = import_module(args.module)

    if hasattr(mod, 'Handler'):
        handler = mod.Handler()
    else:
        handler = BaseHandler()
    handler.add_arguments(parser)
    args = parser.parse_args()    

    try:
        await get_cluster().start()
        r = await handler.run(args)
        logging.info('task return %s', r)
    finally:
        c = get_cluster()
        c.cont = False
        await asyncio.sleep(0.1)
        c.close()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass
        
