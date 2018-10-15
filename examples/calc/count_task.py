import asyncio
from aiobbox.handler import BaseHandler
from aiobbox.utils import sleep
from aiobbox.cluster import get_cluster

"""
run multiple tasks
bbox.py mrun 'count_task haha'  'count_task haha2'
"""

class Handler(BaseHandler):
    def add_arguments(self, parser):
        parser.add_argument(
            'seq', type=str,
            help='sequence to differenciate tasks')

    async def run(self, args):
        self.seq = args.seq
        while get_cluster().is_running():
            print(self.seq, 'step 1')
            await sleep(3)

        # will continue executing about 15 steps when pressing ctrl-c
        for _ in range(100):
            print('stopping', get_cluster().is_stopping())
            print(self.seq, 'step 2')
            await sleep(1)
        print(self.seq, 'end')

    def shutdown(self):
        print(self.seq, 'shutdown')
