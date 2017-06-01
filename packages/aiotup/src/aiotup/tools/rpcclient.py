import os, sys
import re
import json
import asyncio
import argparse
import aiotup.client as tup_client
import aiotup.config as tup_config

parser = argparse.ArgumentParser(
    description='test an rpc interface')

parser.add_argument(
    'srv_method',
    type=str,
    help='service')

parser.add_argument(
    'param',
    type=str,
    nargs='+',
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

async def main():
    tup_config.parse_local()
    args = parser.parse_args()

    srv, method = args.srv_method.split('::')
    ps = []
    for p in args.param:
        if p == 'null':
            p = None
        elif p.isdigit():
            p = int(p)
        elif p.startswith('{') or p.startswith('['):
            p = json.loads(p)
        elif re.match(r'-?\d*(\.\d+)?$', p):
            p = float(p)

        ps.append(p)

    try:
        await tup_client.engine.connect()
        for i in range(args.ntimes):
            r = await tup_client.engine.request(
                srv,
                method,
                *ps,
                conn_retry=args.retry,
                retry=args.retry)
            print(r)
            if i >= args.ntimes - 1:
                break
            await asyncio.sleep(args.interval)
    finally:
        if tup_client.engine:
            tup_client.engine.close()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
