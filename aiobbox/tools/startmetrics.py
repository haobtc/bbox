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

parser = argparse.ArgumentParser(
    prog='bbox metrics',
    description='start bbox python project')

parser.add_argument(
    '--bind',
    type=str,
    default='127.0.0.1:28081',
    help='the box service module to load')

parser.add_argument(
    '--ssl',
    type=str,
    default='',
    help='ssl prefix, the files certs/$prefix.crt and certs/$prefix.key must exist if specified')

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

async def http_server(bind='127.0.0.1:28081', ssl=None):
    app = web.Application()
    app.router.add_get('/metrics', handle_metrics)
    app.router.add_get('/', handle_metrics)

    handler = app.make_handler()
    host, port = bind.split(':')
    logging.warn('metrics starts at %s', bind)
    loop = asyncio.get_event_loop()
    srv = await loop.create_server(handler,
                                   host,
                                   port, ssl=ssl)
    return handler

httpd_mod = None
async def main():
    args = parser.parse_args()
    ssl_context = None
    if args.ssl:
        ssl_cert = abs_path(
            'certs/{}.crt'.format(args.ssl))
        ssl_key = abs_path(
            'certs/{}.key'.format(args.ssl))
        ssl_context = ssl.create_default_context(
            ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(
            ssl_cert, ssl_key)

    # start cluster client
    await get_cluster().start()

    handler = await http_server(bind=args.bind,
                                ssl=ssl_context)
    return handler

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    handler = loop.run_until_complete(main())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        loop.run_until_complete(handler.finish_connections())
