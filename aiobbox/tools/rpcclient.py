import os, sys
import re
import json
import asyncio
import argparse
from aiobbox.log import config_log
import aiobbox.client as bbox_client
from aiobbox.cluster import get_cluster
from aiobbox.utils import guess_json, json_pp, json_to_str

config_log()
parser = argparse.ArgumentParser(
    prog='bbox rpc',
    description='test an rpc interface')

parser.add_argument(
    'srv_method',
    type=str,
    help='service::method')

parser.add_argument(
    'param',
    type=str,
    nargs='*',
    help='params')

parser.add_argument(
    '--retry',
    type=int,
    default=0,
    help='retry times on connection')

parser.add_argument(
    '--ntimes',
    type=int,
    default=1,
    help='iterate x times')

parser.add_argument(
    '--interval',
    type=float,
    default=1.0,
    help='time interval between times')

parser.add_argument(
    '--dispatch_policy',
    type=str,
    default='first',
    help='dispatch request to clients')

async def main():
    args = parser.parse_args()

    srv, method = args.srv_method.split('::')

    ps = [guess_json(p) for p in args.param]

    if args.dispatch_policy == 'random':
        bbox_client.pool.policy = bbox_client.pool.RANDOM

    try:
        await get_cluster().start()

        for i in range(args.ntimes):
            r = await bbox_client.pool.request(
                srv,
                method,
                *ps,
                retry=args.retry)
            print(json_to_str(r))
            if i >= args.ntimes - 1:
                break
            await asyncio.sleep(args.interval)
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
