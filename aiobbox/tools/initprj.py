import os, sys
import uuid
import json
import argparse
from aiobbox.handler import BaseHandler

class Handler(BaseHandler):
    help = 'init a bbox project folder'

    def add_arguments(self, parser):
        parser.add_argument(
            '--language',
            type=str,
            help='the language, default is python3')

        parser.add_argument(
            '--home',
            type=bool,
            default=False,
            help='init to home dir or work dir')

        parser.add_argument(
            '--prefix',
            type=str,
            help='cluster prefix, a cluster of boxes share the prefix')

    async def run(self, args):
        if args.home:
            home_dir = os.getenv('HOME')
            bbox_dir = os.path.join(home_dir, '.bbox')
            config_file = os.path.join(bbox_dir, 'ticket.json')
            gitignore_file = ''
        else:
            bbox_dir = os.path.join(os.getcwd(), '.bbox')
            config_file = os.path.join(bbox_dir, 'ticket.json')
            gitignore_file = os.path.join(os.getcwd(),
                                          '.gitignore')

        if os.path.exists(config_file):
            print('project already initialized!',
                  file=sys.stderr)
            sys.exit(1)

        if not os.path.exists(bbox_dir):
            os.makedirs(bbox_dir)

        prjname = os.getenv('BBOX_PRJNAME')
        if not prjname:
            prjname = os.path.basename(os.getcwd())

        lang = args.language
        if not lang:
            lang = os.getenv('BBOX_LANGUAGE', 'python3')

        if lang not in ('python3', 'python'):
            print('language {} not supported'.format(lang),
                  file=sys.stderr)
            sys.exit(1)

        if lang == 'python':
            lang = 'python3'

        prefix = args.prefix
        if not prefix:
            prefix = os.getenv('BBOX_PREFIX')
        if not prefix:
            prefix = uuid.uuid4().hex

        etcd = os.getenv('BBOX_ETCD')
        if etcd:
            etcd = etcd.split(',')
        if not etcd:
            etcd = ['127.0.0.1:2379']

        port_range = os.getenv('BBOX_PORT_RANGE', '30000-31000')
        port_range = [int(p) for p in port_range.split('-', 1)]

        extbind = os.getenv('BBOX_EXTBIND', '')
        bind_ip = os.getenv('BBOX_BIND_IP', '127.0.0.1')

        config_json = {
            'name': prjname,
            'etcd': etcd,
            'prefix': prefix,
            'language': lang,
            'bind_ip': bind_ip,
            'extbind': extbind,
            'port_range': port_range
        }
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config_json, f, indent=2, sort_keys=True)

        if gitignore_file and not os.path.exists(gitignore_file):
            lines = [
                '*.pyc',
                'node_modules/',
                '.DS_Store',
                'certs/',
                'tmp/',
                'bbox.ticket.json'
            ]
            with open(gitignore_file, 'w',
                      encoding='utf-8') as f:
                f.write(''.join(line + '\n' for line in lines))
