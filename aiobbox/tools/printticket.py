import os, sys
import json
import argparse
from aiobbox.cluster import get_ticket
from aiobbox.log import config_log
from aiobbox.handler import BaseHandler

config_log(mute_console=True)

class Handler(BaseHandler):
    help = 'print ticket info'
    def add_arguments(self, parser):
        parser.add_argument(
            'key',
            type=str,
            help='print key')

    async def run(self, args):
        print(get_ticket()[args.key])
