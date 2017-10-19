import os, sys
import json
import asyncio
import argparse
import aiobbox.client as bbox_client
from aiobbox.utils import guess_json, json_pp
from aiobbox.cluster import get_cluster, get_ticket
from aiobbox.handler import BaseHandler

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

class Handler(BaseHandler):
    help = 'bbox cluster'
    def add_arguments(self, parser):
        subp = parser.add_subparsers()
        p = subp.add_parser('info')
        p.add_argument('--tic', type=str)
        p.set_defaults(func=cluster_info)

    async def run(self, args):
        await get_cluster().start()
        func = getattr(args, 'func', None)
        if func is None:
            print('bbox.py cluster -h')
        else:
            try:
                await args.func(args)
            finally:
                c = get_cluster()
                c.cont = False
                await asyncio.sleep(0.1)
                c.close()
