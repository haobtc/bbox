import os, sys
import json
from aiobbox.log import config_log
import asyncio
import argparse
import aiobbox.client as bbox_client
from aiobbox.utils import guess_json, json_pp
from aiobbox.cluster import get_cluster, get_ticket

config_log()

parser = argparse.ArgumentParser(
    prog='bbox cluster')

async def cluster_info(args):
    cfg = get_ticket()
    info = {
        'etcd': cfg.etcd,
        'prefix': cfg.prefix,
        'boxes': get_cluster().boxes
        }
    print(json_pp(info))

subp = parser.add_subparsers()
p = subp.add_parser('info')
p.add_argument('--tic', type=str)
p.set_defaults(func=cluster_info)

async def main():
    args = parser.parse_args()
    await get_cluster().start()
    try:
        await args.func(args)
    finally:
        c = get_cluster()
        c.cont = False
        await asyncio.sleep(0.1)
        c.close()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

