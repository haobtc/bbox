from typing import Dict, Any, List, Union, Iterable, Callable, Optional
from argparse import Namespace, ArgumentParser

import os, sys
import json
import asyncio
import aiobbox.client as bbox_client
from aiobbox.utils import guess_json, json_pp
from aiobbox.cluster import get_cluster, get_ticket
from aiobbox.handler import BaseHandler

async def cluster_info(args) -> None:
    ticket = get_ticket()
    info = {
        'etcd': ticket.etcd,
        'prefix': ticket.prefix,
        'boxes': get_cluster().boxes
        }
    print(json_pp(info))

class Handler(BaseHandler):
    help = 'bbox cluster'
    def add_arguments(self, parser: ArgumentParser) -> None:
        subp = parser.add_subparsers()
        p = subp.add_parser('info')
        p.add_argument('--tic', type=str)
        p.set_defaults(func=cluster_info)

    async def run(self, args: Namespace) -> None:
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
