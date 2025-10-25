import asyncio
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from typing import Dict
import json
import uuid

router = APIRouter()

# {room_code: {user_id: websocket}}
active_connections: Dict[str, Dict[str, WebSocket]] = {}


@router.websocket("/ws/room/{room_code}")
async def room_websocket(websocket: WebSocket, room_code: str, token_room: str = Query(..., description="Токен подключения к комнате")):
    await websocket.accept()
    
    # Добавляем в список подключений
    if room_code not in active_connections:
        active_connections[room_code] = {}
    active_connections[room_code][token_room] = websocket
    
    try:
        # Отправить список активных пользователей
        active_users = [t for t in active_connections[room_code].keys() if t != token_room]
        await websocket.send_json({
            "type": "active_peers",
            "peers": active_users
        })
        
        # Уведомить всех о новом пользователе
        await broadcast(room_code, {
            "type": "peer_joined",
            "peer_token": token_room
        }, exclude=token_room)
        
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # WebRTC signaling
            if message.get("type") in ["offer", "answer", "ice_candidate"]:
                target_id = message.get("target")
                if target_id and target_id in active_connections.get(room_code, {}):
                    target_ws = active_connections[room_code][target_id]
                    message["from"] = token_room
                    await target_ws.send_json(message)
                    
    except WebSocketDisconnect:
        
        # Удалить соединение
        if room_code in active_connections and token_room in active_connections[room_code]:
            del active_connections[room_code][token_room]
            
        # Уведомить всех
        await broadcast(room_code, {
            "type": "peer_left",
            "peer_token": token_room
        })
        
        # Удалить комнату если пустая
        if room_code in active_connections and len(active_connections[room_code]) == 0:
            del active_connections[room_code]
            print(f"🗑️ Удалена пустая комната: {room_code}")


async def broadcast(room_code: str, message: dict, exclude: str = None):
    """Отправить сообщение всем в комнате"""
    if room_code not in active_connections:
        return
    
    disconnected = []
    for user_id, ws in active_connections[room_code].items():
        if user_id == exclude:
            continue
        try:
            await ws.send_json(message)
        except Exception as e:
            disconnected.append(user_id)
    
    # Удалить отключенных
    for user_id in disconnected:
        if user_id in active_connections[room_code]:
            del active_connections[room_code][user_id]
 