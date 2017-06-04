import os, sys
import json
import asyncio
import argparse
import aiobbox.client as bbox_client
import aiobbox.config as bbox_config
from aiobbox.utils import guess_json, json_pp
from aiobbox.cluster import ClientAgent

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
        'boxes': ClientAgent.agent.boxes
        }
    print(json_pp(info))
    
async def main():
    bbox_config.parse_local()
    args = parser.parse_args()
    await ClientAgent.connect_cluster(**bbox_config.local)
    try:
        if args.op == 'info':
            await cluster_info(*args.param)
        else:
            print('unknown command {}'.format(args.op), file=sys.stderr)
            sys.exit(1)
    finally:
        if ClientAgent.agent:
            ClientAgent.agent.cont = False
            await asyncio.sleep(0.1)
            ClientAgent.agent.close()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
            
