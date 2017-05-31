import os, sys
import json
import argparse
import aiotup.server as tup_server
from aiotup.config import Config

parser = argparse.ArgumentParser(
    description='start tup python project')

parser.add_argument(
    'module',
    type=str,
    nargs='+',
    help='the tup sevice module to load')

parser.add_argument(
    '--bind',
    type=str,
    default='localhost:8080',
    help='server host')

def main():
    config = Config.parse()
    if config['language'] != 'python3':
        print('language must be python3', file=sys.stderr)
        sys.exit(1)
    args = parser.parse_args()
    for mod in args.module:
        __import__(mod)

    host, port = args.bind.split(':')
    tup_server.http_server(host=host, port=int(port))

if __name__ == '__main__':
    main()
