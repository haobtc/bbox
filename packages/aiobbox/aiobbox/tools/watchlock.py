import os, sys
import re
import shlex
import json
import asyncio
import argparse
import aiobbox.client as bbox_client
from aiobbox.cluster import get_cluster, get_sharedconfig, SimpleLock
from aiobbox.exceptions import ETCDError
from aiobbox.utils import guess_json, json_pp

parser = argparse.ArgumentParser(
    prog='bbox lock',
    description='acquire a lock and execute')

parser.add_argument(
    'entry',
    type=str,
    help='lock entry')

async def main():
    args, rest_args = parser.parse_known_args()
    try:
        await get_cluster().start()
    except ETCDError:
        return
    
    c = get_cluster()
    try:
        async with c.acquire_lock(args.entry) as lock:
            if lock.is_acquired and rest_args:
                proc = await asyncio.create_subprocess_shell(
                    ' '.join(shlex.quote(a)
                             for a in rest_args))
                await proc.communicate()
            else:
                await asyncio.sleep(0.1)
    finally:
        pass
    return True

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    normal = True    
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        normal = False
    #if not normal:
    if True:
        c = get_cluster()
        loop.run_until_complete(SimpleLock.close_all_keys(c))
        c.cont = False
        c.close()
