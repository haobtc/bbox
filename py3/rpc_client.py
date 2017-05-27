from aiohaorpc.client import Client, WebSocketClient
import asyncio

async def added(r):
    print('added', r)
    
async def main():
    #client = Client()
    #r = await client.request('calc', 'add2num', [5, 69])
    #print(r)

    client = WebSocketClient()
    await client.connect()
    asyncio.gather(
        client.request('calc', 'add2num', [5, 68], added),
        client.request('calc', 'add2num', [6, 11], added))
    await client.wait()

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
