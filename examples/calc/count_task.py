import asyncio
from aiobbox.handler import BaseHandler

class Handler(BaseHandler):
    async def run(self, args):
        while self.cont:
            print('step 1')
            await self.sleep(3)

        # will continue executing about 15 steps when pressing ctrl-c
        for _ in range(100):
            #await asyncio.sleep(1)
            await self.sleep(1)
            print('step 2')
        print('end')

    def shutdown(self):
        print("shutdown")
