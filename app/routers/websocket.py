from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Cookie
from typing import Dict, Optional
import json

router = APIRouter()

# {room_code: {token: websocket}}
active_connections: Dict[str, Dict[str, WebSocket]] = {}

@router.websocket("/ws/room/{room_code}")
async def room_websocket(
    websocket: WebSocket, 
    room_code: str,
    token_room: Optional[str] = Cookie(None)
):
    await websocket.accept()
    await websocket.send_text("Успешно")
    
    if not token_room:
        await websocket.close(code=1008, reason="No token")
        return
    
    # Добавиляем в список подключений
    if room_code not in active_connections:
        active_connections[room_code] = {}
    active_connections[room_code][token_room] = websocket
    
    try:
        active_tokens = [t for t in active_connections[room_code].keys() if t != token_room]
        await websocket.send_json({
            "type": "active_peers",
            "peers": active_tokens 
        })
        
        # Уведомить всех о новом peer
        await broadcast(room_code, {
            "type": "user_joined",
            "user_token": token_room
        }, exclude=token_room)
        
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # WebRTC signaling
            if message.get("type") in ["offer", "answer", "ice_candidate"]:
                target_token = message.get("target")
                if target_token and target_token in active_connections.get(room_code, {}):
                    target_ws = active_connections[room_code][target_token]
                    message["from"] = token_room
                    await target_ws.send_json(message)
                    
    except WebSocketDisconnect:
        # Удалить соединение
        if room_code in active_connections and token_room in active_connections[room_code]:
            del active_connections[room_code][token_room]
            
        # Уведомить всех
        await broadcast(room_code, {
            "type": "user_left",
            "user_token": token_room
        })
        
        if room_code in active_connections and len(active_connections[room_code]) == 0:
            del active_connections[room_code]

async def broadcast(room_code: str, message: dict, exclude: str = None):
    if room_code not in active_connections:
        return
    
    disconnected = []
    for token, ws in active_connections[room_code].items():
        if token == exclude:
            continue   
        try:
            await ws.send_json(message)
        except:
            disconnected.append(token)
    
    for token in disconnected:
        if token in active_connections[room_code]:
            del active_connections[room_code][token]
