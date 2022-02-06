#!/usr/bin/env python3

import asyncio
from aiohttp import web, WSMsgType
import weakref
import signal
import sys

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
                    if not app['process'].stdin.is_closing():
                        # print("Sending " + msg.data, flush=True)
                        app['process'].stdin.write((msg.data + '\n').encode('utf-8'))
                        await app['process'].stdin.drain()
                        # print("Done sending " + msg.data, flush=True)
    finally:
        request.app['websockets'].discard(ws)

    print('Websocket connection closed', flush=True)
    return ws

async def listen_to_process(proc):
    while not proc.stdout.at_eof():
        line = await proc.stdout.readline()
        line = line.decode('utf-8')
        # print(proc.stdout.at_eof(), flush=True)
        print(line, flush=True, end='')
        for ws in set(app['websockets']):
            # print("Sending to WebSocket", flush=True)
            await ws.send_str(line)
            # print("Done sending to WebSocket", flush=True)
    # print("Done listening", flush=True)

async def say_stuff(proc):
    await asyncio.sleep(2)
    proc.stdin.write(('msg.data' + '\n').encode('utf-8'))
    await proc.stdin.drain()
    await asyncio.sleep(2)
    proc.stdin.write(('salad' + '\n').encode('utf-8'))
    await proc.stdin.drain()
    print("Done saying stuff", flush=True)

async def wait_for_process(proc):
    await proc.wait()
    # print("Process exited", flush=True)
    # It seems the only way to shut down the web server is to send a SIGINT?
    signal.raise_signal(signal.SIGINT)

async def start_process(app):
    global proc
    proc = await asyncio.create_subprocess_exec(
        options["command"][0],
        *options["command"][1:],
        stdin = asyncio.subprocess.PIPE,
        stdout = asyncio.subprocess.PIPE,
        stderr = asyncio.subprocess.STDOUT,
    )

    app['process'] = proc
    app['listen_process'] = asyncio.create_task(listen_to_process(proc))
    # app['say_process'] = asyncio.create_task(say_stuff(proc))
    app['wait_process'] = asyncio.create_task(wait_for_process(proc))

async def end_process(app):
    # print("ending_process", flush=True)
    if not app['process'].stdin.is_closing():
        if app['options']['exit_statement'] == "":
            app['process'].stdin.write_eof()
        else:
            app['process'].stdin.write((app['options']['exit_statement'] + '\n').encode('utf-8'))
        await app['process'].stdin.drain()
    # print("end_process", flush=True)

def print_usage():
    progname = sys.argv[0].split('/')[-1]
    print(f"Usage: {progname} [-h HOST] [-p PORT] [-e EXIT_STATEMENT] COMMAND")

def parse_arguments():
    if len(sys.argv) <= 1:
        print_usage()
        sys.exit(1)

    options = {
        "port": 8080,
        "host": "localhost",
        "exit_statement": "",
        "command": ""
    }

    args = sys.argv[1:]
    while len(args) > 0:
        if args[0] == '-h' and len(args) > 1:
            options["host"] = args[1]
            args = args[2:]
        elif args[0][0:2] == '-h':
            options["host"] = args[0][2:]
            args = args[1:]
        elif args[0] == '-p' and len(args) > 1:
            options["port"] = int(args[1])
            args = args[2:]
        elif args[0][0:2] == '-p':
            options["port"] = int(args[0][2:])
            args = args[1:]
        elif args[0] == '-e' and len(args) > 1:
            options["exit_statement"] = args[1]
            args = args[2:]
        elif args[0][0:2] == '-e':
            options["exit_statement"] = args[0][2:]
            args = args[1:]
        else:
            break

    if len(args) == 0:
        print_usage()
        sys.exit(1)

    options["command"] = args
    return options

if __name__ == '__main__':
    options = parse_arguments()

    app = web.Application()
    app['options'] = options
    app['websockets'] = weakref.WeakSet()
    app.on_startup.append(start_process)
    app.on_shutdown.append(end_process)
    app.add_routes([web.get('/', websocket_handler)])
    web.run_app(app, host=options['host'], port=options['port'])
    # print("I am so done here")
    # print(app['process'].returncode)
