import os, sys
import logging
import uuid
import json
import asyncio
import argparse
import aiobbox.server as bbox_server
from aiobbox.cluster import get_box, get_cluster, get_localconfig
from aiobbox.utils import import_module

parser = argparse.ArgumentParser(
    description='run bbox tasks')

parser.add_argument(
    'module',
    type=str,
    nargs='+',
    help='the task module to load')

async def run_mod(mod):
    runfn = getattr(mod, 'run', None)
    if runfn is None:
        return
    return await runfn()
    
async def main():
    cfg = get_localconfig()
    if cfg.language != 'python3':
        print('language must be python3', file=sys.stderr)
        sys.exit(1)
    args = parser.parse_args()

    modules = []
    for mod in args.module:
        modules.append(import_module(mod))

    try:
        await get_cluster().start()
        coros = [run_mod(mod) for mod in modules]
        r = await asyncio.gather(*coros)
        logging.info('tasks return %s', r)
    finally:
        c = get_cluster()
        c.cont = False
        await asyncio.sleep(0.1)
        c.close()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
