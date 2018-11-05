import os, sys
import re
import json
import asyncio
import argparse
import aiobbox.client as bbox_client
from aiobbox.cluster import get_cluster
from aiobbox.utils import guess_json, json_pp, json_to_str, semanticbool
from aiobbox.handler import BaseHandler


def handle_text(text, indent=0, prompt=''):
    text = text or ''
    pad = ' ' * indent + prompt
    lines = text.split('\n')
    lines = [re.sub(r'^\s*', '', line)
             for line in lines]

    text = '\n'.join(lines)
    text = re.sub(r'^ *\n', '', text)
    text = re.sub(r'\s+$', '', text)
    if not text:
        return ''

    text = '\n'.join((pad + line) for line in text.split('\n'))
    return text

def print_text(r):
    print('{}:'.format(r['name']))
    print(handle_text(r['doc'], indent=2, prompt='* '))
    print('methods:')
    for method in r['methods']:
        print('  {}:'.format(method['name']))
        doc = handle_text(method['doc'], indent=4, prompt='* ')
        if doc:
            print(doc)
        else:
            print()

def print_markdown(r):
    print('= {}'.format(r['name']))
    print(handle_text(r['doc']))
    print()
    print('= methods:')
    for method in r['methods']:
        print('== {}'.format(method['name']))
        doc = handle_text(method['doc'])
        if doc:
            print(doc)
        print()

class Handler(BaseHandler):
    help = 'print human readable documents'
    def add_arguments(self, parser):
        parser.add_argument(
            'srv_name',
            type=str,
            help='service name')

        parser.add_argument(
            '--format',
            type=str,
            default='markdown',
            help='output format')

        parser.add_argument(
            '--nameonly',
            type=semanticbool,
            default=False,
            help='only show methods names')

    async def run(self, args):
        try:
            await get_cluster().start()

            resp = await bbox_client.pool.request(
                args.srv_name,
                '__doc__')
            if not resp.get('result'):
                return
            r = resp['result']
            if args.nameonly:
                print(r['name'])
                print('methods:')
                for method in r['methods']:
                    print('  {}'.format(method['name']))
            elif args.format in ('markdown', 'md'):
                print_markdown(r)
            else:
                print_text(r)
        finally:
            c = get_cluster()
            c.cont = False
            await asyncio.sleep(0.1)
            c.close()
