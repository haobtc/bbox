import os, sys
import ssl
import logging
import uuid
import json
import asyncio
from aiohttp import web, ClientSession, ClientConnectionError
import argparse
import aiobbox.server as bbox_server
from aiobbox.cluster import get_box, get_cluster
from aiobbox.cluster import get_ticket
from aiobbox.utils import import_module, abs_path
from aiobbox.metrics import collect_cluster_metrics


export_cluster = False

parser = argparse.ArgumentParser(
    prog='bbox httpd',
    description='start bbox python project')
parser.add_argument(
    '--export_cluster',
    type=bool,
    default=export_cluster,
    help='export the whole cluster info')

async def get_box_metrics(bind, session):
    try:
        resp = await session.get('http://' + bind + '/metrics.json')
    except ClientConnectionError:
        logging.error('client connection error')
        return []
    return await resp.json()

async def handle_metrics(request):
    c = get_cluster()

    with ClientSession() as session:
        fns = [get_box_metrics(bind, session)
               for bind in c.boxes.keys()]
        if fns:
            res = await asyncio.gather(*fns)
        else:
            res = []
            
    if export_cluster:
        res.append(collect_cluster_metrics())

    meta = {}
    lines = []
    meta_lines = []
    for resp in res:
        meta.update(resp['meta'])
        
        for name, labels, v in resp['lines']:
            d = ', '.join('{}="{}"'.format(lname, lvalue)
                          for lname, lvalue in labels.items())
            d = '{' + d + '}'
            lines.append('{} {} {}'.format(name, d, v))

    for name, define in meta.items():
        meta_lines.append('# HELP {} {}'.format(
            name, define['help']))
        meta_lines.append('# TYPE {} {}'.format(
            name, define['type']))
    meta_lines.append('')

    headers = {'Content-Type': 'text/plain'}
    return web.Response(text='\n'.join(meta_lines + lines + ['']),
                        headers=headers)

async def get_app(**kw):
    app = web.Application()
    app.router.add_get('/metrics', handle_metrics)
    app.router.add_get('/', handle_metrics)
    return app

async def start():
    global export_cluster
    args, _ = parser.parse_known_args()
    export_cluster = args.export_cluster

