import os, sys
import ssl
import logging
import uuid
import json
import asyncio
from urllib.parse import urljoin
from aiohttp import web, ClientSession, ClientConnectionError
import argparse
import aiobbox.server as bbox_server
from aiobbox.cluster import get_box, get_cluster
from aiobbox.cluster import get_ticket
from aiobbox.utils import import_module, abs_path
from aiobbox.client import HttpClient
from aiobbox.metrics import collect_cluster_metrics, report_box_failure
from aiobbox.handler import BaseHandler

export_cluster = False
collect_localbox = False

_http_clients = {}

async def get_box_metrics(connect):
    if connect not in _http_clients:
        client = HttpClient(connect)
        _http_clients[connect] = client
    else:
        client = _http_clients[connect]
    try:
        url = urljoin(client.url_prefix, '/metrics.json')
        resp = await client.session.get(url)
    except ClientConnectionError:
        logging.error('client connection error to %s', bind)
        return report_box_failure(bind)
    return await resp.json()

async def handle_metrics(request):
    c = get_cluster()

    with ClientSession() as session:
        if collect_localbox:
            fns = [get_box_metrics(bind)
                   for bind in c.get_local_boxes()]
        else:
            fns = [get_box_metrics(bind)
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

class Handler(BaseHandler):
    def add_arguments(self, parser):
        parser.add_argument(
            '--export_cluster',
            type=bool,
            default=export_cluster,
            help='export the whole cluster info')
        parser.add_argument(
            '--collect_localbox',
            type=bool,
            default=collect_localbox,
            help='coll')

    async def get_app(self, args):
        app = web.Application()
        app.router.add_get('/metrics', handle_metrics)
        app.router.add_get('/', handle_metrics)
        return app

    async def start(self, args):
        global export_cluster, collect_localbox
        export_cluster = args.export_cluster
        collect_localbox = args.collect_localbox
