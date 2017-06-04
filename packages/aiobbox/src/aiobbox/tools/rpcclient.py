import os, sys
import re
import json
import asyncio
import argparse
import aiobbox.client as bbox_client
import aiobbox.config as bbox_config
import aiobbox.discovery as bbox_dsc
from aiobbox.utils import guess_json, json_pp

parser = argparse.ArgumentParser(
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
    bbox_config.parse_local()
    args = parser.parse_args()

    srv, method = args.srv_method.split('::')

    ps = [guess_json(p) for p in args.param]

    if args.dispatch_policy == 'random':
        bbox_client.engine.policy = bbox_client.engine.RANDOM

    try:
        await bbox_dsc.client_connect(**bbox_config.local)
        for i in range(args.ntimes):
            r = await bbox_client.engine.request(
                srv,
                method,
                *ps,
                retry=args.retry)
            print(json_pp(r))
            if i >= args.ntimes - 1:
                break
            await asyncio.sleep(args.interval)
    finally:
        if bbox_dsc.client_agent:
            bbox_dsc.client_agent.close()


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
