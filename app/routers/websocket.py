from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Dict, Optional
import json
import uuid
import asyncio
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# {room_code: {user_id: websocket}}
active_connections: Dict[str, Dict[str, WebSocket]] = {}


@router.websocket("/ws/room/{room_code}")
async def room_websocket(
    websocket: WebSocket, 
    room_code: str,
    token: Optional[str] = Query(None),
):
    await websocket.accept()

    user_id = str(uuid.uuid4())
    
    logger.info(f"[WS] 🔌 Новое подключение: {user_id} → {room_code}")
    
    # Добавляем в активные соединения
    if room_code not in active_connections:
        active_connections[room_code] = {}
    active_connections[room_code][user_id] = websocket
    
    try:
        # 1. Отправляем список активных участников
        active_users = [uid for uid in active_connections[room_code].keys() 
                        if uid != user_id]
        logger.info(f"[WS] Отправляю active_peers к {user_id}: {len(active_users)} участников")
        await websocket.send_json({
            "type": "active_peers",
            "peers": active_users
        })
        await asyncio.sleep(0.2)
        
        # 3. Уведомляем других о новом участнике
        logger.info(f"[WS] Уведомляю остальных о {user_id}")
        await broadcast(room_code, {
            "type": "peer_joined",
            "peer_token": user_id
        }, exclude=user_id)
        
        logger.info(f"[WS] ✅ Инициализация завершена для {user_id}")
        logger.info(f"[WS] Всего в комнате '{room_code}': {len(active_connections[room_code])}")
        
        # Основной цикл обработки сообщений
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            msg_type = message.get("type")
            logger.debug(f"[WS] 📨 {user_id} → {msg_type}")
            
            # WebRTC signaling
            if msg_type in ["offer", "answer", "ice_candidate"]:
                target_id = message.get("target")
                if target_id and target_id in active_connections.get(room_code, {}):
                    target_ws = active_connections[room_code][target_id]
                    message["from"] = user_id
                    await target_ws.send_json(message)
                    logger.debug(f"[WS] ✅ Переслано {msg_type}: {user_id} → {target_id}")
                else:
                    logger.warning(f"[WS] ⚠️ Target {target_id} не найден")
            
            # ✅ НОВОЕ: Трансляция статуса медиа (mic/camera)
            elif msg_type == "media_status":
                status = message.get("status", {})
                audio_on = status.get("audioOn", True)
                video_on = status.get("videoOn", True)
                
                logger.info(f"[WS] 🎬 Статус медиа от {user_id}: audio={audio_on}, video={video_on}")
                
                # Отправляем всем остальным участникам
                await broadcast(room_code, {
                    "type": "media_status",
                    "from": user_id,
                    "status": {
                        "audioOn": audio_on,
                        "videoOn": video_on
                    }
                }, exclude=user_id)
            
            else:
                logger.warning(f"[WS] ⚠️ Неизвестный тип сообщения: {msg_type}")
    
    except WebSocketDisconnect:
        logger.info(f"[WS] 🔴 Отключился: {user_id}")
    except Exception as e:
        logger.error(f"[WS] ❌ Ошибка для {user_id}: {e}")
    finally:
        # Удаляем соединение
        if room_code in active_connections and user_id in active_connections[room_code]:
            del active_connections[room_code][user_id]
            logger.info(f"[WS] Удален из комнаты: {user_id}")
        
        # Уведомляем остальных
        await broadcast(room_code, {
            "type": "peer_left",
            "peer_token": user_id
        })
        
        # Очищаем пустые комнаты
        if room_code in active_connections and len(active_connections[room_code]) == 0:
            del active_connections[room_code]
            logger.info(f"[WS] Комната '{room_code}' пуста, удалена")


async def broadcast(room_code: str, message: dict, exclude: str = None):
    """
    Отправить сообщение всем участникам комнаты (кроме exclude)
    
    Args:
        room_code: Код комнаты
        message: Сообщение для отправки
        exclude: User ID которого исключить из рассылки
    """
    if room_code not in active_connections:
        return
    
    disconnected = []
    
    for user_id, ws in active_connections[room_code].items():
        if user_id == exclude:
            continue
        
        try:
            await ws.send_json(message)
            logger.debug(f"[BROADCAST] ✅ Отправлено {user_id}")
        except Exception as e:
            logger.error(f"[BROADCAST] ❌ Ошибка отправки {user_id}: {e}")
            disconnected.append(user_id)
    
    # Удаляем отключенные соединения
    for user_id in disconnected:
        if user_id in active_connections[room_code]:
            del active_connections[room_code][user_id]
            logger.info(f"[BROADCAST] Удален отключенный: {user_id}")
