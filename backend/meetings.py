from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict

router = APIRouter()

# rooms -> username -> websocket
ROOMS: Dict[str, Dict[str, WebSocket]] = {}

@router.websocket('/ws/meet/{room}')
async def meet_ws(websocket: WebSocket, room: str):
    await websocket.accept()
    try:
        # first message should be join with username
        data = await websocket.receive_json()
        if data.get('type') != 'join' or 'username' not in data:
            await websocket.close(code=1008)
            return
        username = data['username']
        if room not in ROOMS:
            ROOMS[room] = {}
        # inform existing peers about new user
        existing = list(ROOMS[room].keys())
        ROOMS[room][username] = websocket
        # send list of existing participants to new user
        await websocket.send_json({'type': 'participants', 'participants': existing})
        # notify others about join
        for u, ws in list(ROOMS[room].items()):
            if u != username:
                try:
                    await ws.send_json({'type': 'join', 'username': username})
                except Exception:
                    pass
        # main loop: forward signaling messages
        while True:
            msg = await websocket.receive_json()
            typ = msg.get('type')
            if typ in ('offer', 'answer', 'ice'):
                target = msg.get('to')
                if not target:
                    continue
                target_ws = ROOMS[room].get(target)
                if target_ws:
                    await target_ws.send_json({
                        'type': typ,
                        'from': username,
                        'data': msg.get('data')
                    })
            elif typ == 'leave':
                break
            else:
                # unknown message types can be ignored or logged
                pass
    except WebSocketDisconnect:
        pass
    finally:
        # cleanup
        if room in ROOMS and username in ROOMS[room]:
            del ROOMS[room][username]
            for u, ws in list(ROOMS[room].items()):
                try:
                    await ws.send_json({'type': 'leave', 'username': username})
                except Exception:
                    pass
            if not ROOMS[room]:
                del ROOMS[room]
