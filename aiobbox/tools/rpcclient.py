import os, sys
import re
import json
import asyncio
import argparse
import aiobbox.client as bbox_client
from aiobbox.cluster import get_cluster
from aiobbox.utils import guess_json, json_pp, json_to_str, semanticbool
from aiobbox.handler import BaseHandler

class Handler(BaseHandler):
    help = 'test an rpc interface'
    def add_arguments(self, parser):
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
            '--pp',
            type=semanticbool,
            default=True,
            help='pretty print')

        parser.add_argument(
            '--dispatch_policy',
            type=str,
            default='first',
            help='dispatch request to clients')
        parser.add_argument(
            '--timeout',
            type=float,
            default=bbox_client.DEFAULT_TIMEOUT_SECS,
        )

        parser.add_argument(
            '--stack',
            type=semanticbool,
            default=False,
            help='print error stack')

    async def run(self, args):
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
                    retry=args.retry,
                    timeout=args.timeout)
                if args.pp:
                    print(json_pp(r))
                else:
                    print(json_to_str(r))
                if (args.stack
                    and r.get('error')
                    and isinstance(r['error'], dict)
                    and r['error'].get('stack')):

                    print('\nerror stack:')
                    print(r['error']['stack'])

                if i >= args.ntimes - 1:
                    break
                await asyncio.sleep(args.interval)
        finally:
            c = get_cluster()
            c.cont = False
            await asyncio.sleep(0.1)
            c.close()
