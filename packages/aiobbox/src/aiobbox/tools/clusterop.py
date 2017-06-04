import os, sys
import json
import asyncio
import argparse
import aiobbox.client as bbox_client
from aiobbox.utils import guess_json, json_pp
from aiobbox.cluster import get_cluster, get_localconfig

parser = argparse.ArgumentParser(
    description='cluster op and info')

parser.add_argument(
    'op',
    type=str,
    help='cluster op')

parser.add_argument(
    'param',
    type=str,
    nargs='*',
    help='params')

async def cluster_info():
    cfg = get_localconfig()
    info = {
        'etcd': cfg.etcd,
        'prefix': cfg.prefix,
        'boxes': get_cluster().boxes
        }
    print(json_pp(info))
    
async def main():
    args = parser.parse_args()
    await get_cluster().start()
    try:
        if args.op == 'info':
            await cluster_info(*args.param)
        else:
            print('unknown command {}'.format(args.op), file=sys.stderr)
            sys.exit(1)
    finally:
        c = get_cluster()
        c.cont = False
        await asyncio.sleep(0.1)
        c.close()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
            
