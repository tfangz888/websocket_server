#!/usr/bin/evn python3

import asyncio
import signal
import websockets

import logging
import json

logging.basicConfig(
    format = "%(asctime)s %(message)s",
    level = logging.DEBUG,
)

# msg = {
#     "to": "client2, client3", # "all"
#     "from": "client1"
#     "type": "broadcast", "event", "request", "reply"
#     "verb": "register", "bye", "broadcast", "event", "request"， "reply"
#     "value": 5,
#     "msg": "message"
# }


CONNECTIONS = {}

def parseJson(jsonMsg):
    try:
        dict = json.loads(jsonMsg)
        return dict
    except json.JSONDecodeError:
        return None

async def send(websocket, message):
    try:
        await websocket.send(message)
    except websockets.ConnectionClosed:
        logging.error("error sending: %s", message)
        del_key = None
    for key in CONNECTIONS:
       if websocket == CONNECTIONS[key]:
          del_key = key
    if del_key:
        del CONNECTIONS[del_key]
    
def message_all(message):
    websocket.broadcast(set(CONNECTIONS.values()), message)
    
async def message_user(user_id, message):
    try:
        websocket = CONNECTIONS[user_id] # raise KeyError if user disconnected
    except KeyError:
        logging.error("KeyError message_user user_id: %s", user_id)
        if user_id in CONNECTIONS:
            del CONNECTIONS[user_id]
        return
    try:
        await websocket.send(message)  # may raise websockets. ConnectionClosed
    except websockets.ConnectionClosed:
        logging.error("ConnectionClosed message_user user_id: %s", user_id)
        if user_id in CONNECTIONS:
            del CONNECTIONS[user_id]
    
async def forward(message):
    msg = parseJson(message)
    if "to" in msg:
        destinations = msg["to"].split(",")
        for dest in destinations:
            await message_user(dest.strip(), message)
            
async def broadcast(message):
    for websocket in set(CONNECTIONS.values()):
        asyncio.create_task(send(websocket, message))
        
async def register(name, websocket):
    if name in CONNECTIONS:
        # close connection
        await CONNECTIONS[name].close()
        pass
    CONNECTIONS[name] = websocket
    logging.info("register from: %s", name)
    
async def bye(name, websocket):
    if name in CONNECTIONS:
        #close connection
        await websocket.close()
        del CONNECTIONS[name]
    logging.info("bye from: %s", name)
    
async def handler(websocket):
    print(websocket.path)
    print(websocket.remote_address[0])
    name = websocket.path
    if len(name) < 2:
        logging.error("error register name: %s", name)
        return
    name = name[1:]
    await register(name, websocket) # 注册 
    
    async for message in websocket:
        try:
            msg = parseJson(message)
            if not msg:
                logging.error("parse error: %s", message)
                continue
            if "verb" not in msg or "from" not in msg:
                logging.error("format error: %s", message)
                continue
            verb = msg["verb"]
            if verb == 'bye': # 再见
                await bye(name, websocket)
            elif verb == 'broadcast':
                await broadcast(message) # 广播
            else:
                await forward(message)
        except websockets.ConnectionClosedError:
            logging.error("peer connection closed")
            websocket.close()
            
async def server():
    # Set the stop condition when receiving SIGTERM
    loop = asyncio.get_running_loop()
    stop = loop.create_future()
    loop.add_signal_handler(signal.SIGTERM, stop.set_result, None)
    
    async with websockets.serve(handler, "", 8765):
        await stop

if __name__ == "__main__":
    asyncio.run(server())
	
	
