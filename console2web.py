#!/usr/bin/env python3

from aiohttp import web, WSMsgType
import asyncio
import weakref
import sys


HOST = '127.0.0.1'
PORT = 8080

async def websocket_handler(request):
    print('Websocket connection starting', flush=True)
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    print('Websocket connection ready', flush=True)
    request.app['websockets'].add(ws)

    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                if msg.data == 'close':
                    await ws.close()
                else:
                    if app['mutable_state']['process'] != None:
                        app['mutable_state']['process'].stdin.write((msg.data + '\n').encode('utf-8'))
                    else:
                        print("Process was None")
    finally:
        request.app['websockets'].discard(ws)

    print('Websocket connection closed', flush=True)
    return ws

async def listen_to_redis(app):
    await asyncio.sleep(10)

async def system_process(app):
    process = await asyncio.create_subprocess_exec(
        app['command'],
        *app['args'],
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE)
    app['mutable_state']['process'] = process
    while True:
        data = await process.stdout.readline()
        line = data.decode('ascii').rstrip()
        print(line, flush=True)
        for ws in set(app['websockets']):
            await ws.send_str(line)

        # await asyncio.sleep(0.03)

async def start_background_tasks(app):
    app['system_process'] = asyncio.create_task(system_process(app))

async def cleanup_background_tasks(app):
    print('cleaning up', flush=True)
    app['system_process'].cancel()
    # await app['system_process']

async def cancel_background_tasks(app):
    app['system_process'].cancel()
    print("cancel_background_tasks")

if __name__ == "__main__":
    if len(sys.argv) <= 1:
        print("Usage: " + sys.argv[0] + " [-p PORT] COMMAND")
        sys.exit(1)

    args = sys.argv[1:]
    print(args)
    if args[0][0:2] == '-p':
        if len(args[0]) == 2:
            PORT = int(args[1])
            args = args[2:]
        else:
            PORT = int(args[0][2:])
            args = args[1:]
    if len(args) == 0:
        print("Usage: " + sys.argv[0] + " [-p PORT] COMMAND")
    command = args[0]
    args = args[1:]

    app = web.Application()
    app['command'] = command
    app['args'] = args
    app['websockets'] = weakref.WeakSet()
    app['mutable_state'] = {"process": None}
    app.on_startup.append(start_background_tasks)
    app.on_cleanup.append(cleanup_background_tasks)
    app.on_shutdown.append(cancel_background_tasks)
    app.add_routes([
        web.get('/', websocket_handler)
    ])
    web.run_app(app, host=HOST, port=PORT)
