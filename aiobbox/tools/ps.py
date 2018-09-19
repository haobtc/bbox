import os, sys
import logging
import json
import asyncio
import argparse
from datetime import datetime
from aiobbox.exceptions import Stop
import aiobbox.server as bbox_server
from aiobbox.cluster import get_box, get_cluster, get_ticket
from aiobbox.utils import import_module
from aiobbox.handler import BaseHandler

logger = logging.getLogger('bbox')

class Handler(BaseHandler):
    help = 'process status'
    def add_arguments(self, parser):
        parser.add_argument('--skipheaders', '-s',
                            default='no',
                            help="don't print headers")

    async def run(self, args):
        cluster = get_cluster()
        await cluster.start()
        if args.skipheaders.lower() not in ('yes', 'true', '1'):
            headers = ['srv', 'bind', 'boxid', 'start', 'ssl_prefix']
            print('\t'.join(headers))
            print('\t'.join(['-' * len(h) for h in headers]))
        now = datetime.utcnow()
        for srv, boxes in cluster.route.items():
            for bind in boxes:
                row = [srv, bind]
                box = cluster.boxes.get(bind, {})
                row.append(box.get('boxid', '-'))
                start_time = box.get('start_time')
                row.append(start_time or '-')
                row.append(box.get('ssl') or '-')
                print('\t'.join(row))

