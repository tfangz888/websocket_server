#!/usr/bin/env python3

import sys
import asyncio
import signal
import websockets

import logging
import json

logging.basicConfig(
    format="%(asctime)s %(message)s",
    level=logging.DEBUG,
)

me = sys.argv[1]  # 'client3'

# msg = {
#     "to": "client2, client3", # "all"
#     "from": "client1"
#     "type": "broadcast", "event", "request", "reply"
#     "verb": "register", "bye", "broadcast", "event", "request"， "reply"
#     "value": 5,
#     "msg": "message"
# }


def parseJson(jsonMsg):
    try:
        dict = json.loads(jsonMsg)
        return dict
    except json.JSONDecodeError:
        return None


def consumer(message):
    msg = parseJson(message)
    if not msg:
        logging.error("parse error: %s", message)
        return
    if "verb" not in msg or "from" not in msg:
        logging.error("format error: %s", message)
        return
    src = msg["from"]
    if src == me:
        return
    verb = msg["verb"]
    print("consumer received msg from: " + src)


async def producer():
    test = {}
    test["to"] = "client1"
    test["from"] = me
    test["verb"] = "request"
    test["msg"] = "msg from: " + me
    return json.dumps(test)


async def consumer_handler(websocket):
    try:
        async for message in websocket:
            consumer(message)
    except websockets.ConnectionClosed:
        logging.error("ConnectionClosed in consumer_handler")
        pass


async def producer_handler(websocket):
    while True:
        await asyncio.sleep(2.5)
        message = await producer()
        try:
            await websocket.send(message)
        except websockets.ConnectionClosed:
            logging.error("ConnectionClosed in producer_handler")
            continue


async def handler(websocket):
    consumer_task = asyncio.create_task(consumer_handler(websocket))
    producer_task = asyncio.create_task(producer_handler(websocket))
    done, pending = await asyncio.wait(
        [consumer_task, producer_task],
        return_when=asyncio.FIRST_COMPLETED,
    )
    for task in pending:
        task.cancel()


async def client():
    uri = "ws://localhost:8765/" + me
    async for websocket in websockets.connect(uri):
        # close the connection when receiving SIGTERM.
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGTERM, loop.create_task, websocket.close())

        await handler(websocket)


if __name__ == "__main__":
    asyncio.run(client())
