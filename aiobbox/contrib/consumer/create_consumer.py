import sys
import ssl
import re
import os
import uuid
from aiobbox.handler import BaseHandler
from aiobbox.utils import guess_json, json_pp
from aiobbox.cluster import get_sharedconfig, get_cluster

class Handler(BaseHandler):
    def add_arguments(self, parser):
        parser.add_argument(
            'consumer',
            type=str,
            help='consumer name')

    async def run(self, args):
        consumer = args.consumer
        if not consumer:
            raise Exception('void consumer')

        if not re.match(r'\w+$', consumer):
            raise Exception('invalid consumer')

        cfg = get_sharedconfig()
        coptions = cfg.get('consumers', consumer)
        if coptions:
            print(
                'consumer {} already exist, secret is {}'.format(
                consumer, coptions['secret']))
            return


        coptions = {}
        coptions['secret'] = uuid.uuid4().hex
        coptions['seed'] = ssl.RAND_bytes(256).hex()

        c = get_cluster()
        if c.use_local_configs():
            print(json_pp({
                'consumer': {
                    consumer: coptions
                }
            }))
        else:
            await c.set_config('consumers', consumer, coptions)

        # TODO: limit the consumer size

        print('secret for', consumer, coptions['secret'])
