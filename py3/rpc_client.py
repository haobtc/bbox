from aiotup.client import Client, WebSocketClient
import asyncio

async def main():
    client = Client()
    r = await client.request('calc', 'add2num', 5, 69)
    print(r)

    client = WebSocketClient()
    await client.connect()
    r = await asyncio.gather(
        client.request('calc', 'add2sleep', 5, 68, 13.5),
        client.request('calc', 'add2sleep', 6, 11, 1.5))
    print(r)

loop = asyncio.get_event_loop()
loop.run_until_complete(main())
