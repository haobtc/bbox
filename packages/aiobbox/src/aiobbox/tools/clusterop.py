import os, sys
import json
import asyncio
import argparse
import aiobbox.client as bbox_client
import aiobbox.config as bbox_config
import aiobbox.discovery as bbox_dsc
from aiobbox.utils import guess_json, json_pp

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
    info = {
        'etcd': bbox_config.local['etcd'],
        'prefix': bbox_config.local['prefix'],
        'boxes': bbox_dsc.client_agent.boxes
        }
    print(json_pp(info))
    
async def main():
    bbox_config.parse_local()
    args = parser.parse_args()
    await bbox_dsc.client_connect(**bbox_config.local)
    try:
        if args.op == 'info':
            await cluster_info(*args.param)
        else:
            print('unknown command {}'.format(args.op), file=sys.stderr)
            sys.exit(1)
    finally:
        if bbox_dsc.client_agent:
            bbox_dsc.client_agent.cont = False
            await asyncio.sleep(0.1)
            bbox_dsc.client_agent.close()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
            
