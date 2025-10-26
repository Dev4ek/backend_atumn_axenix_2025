from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Dict, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
import json
import uuid
import asyncio
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@dataclass
class PeerConnection:
    """Состояние одного участника"""
    user_id: str
    websocket: WebSocket
    audio_on: bool = True
    video_on: bool = False
    screen_sharing: bool = False
    connected_at: datetime = field(default_factory=datetime.utcnow)
    last_ping: datetime = field(default_factory=datetime.utcnow)
    # Набор peer_id с которыми установлено WebRTC соединение
    active_rtc_connections: Set[str] = field(default_factory=set)


@dataclass
class Room:
    """Состояние комнаты"""
    code: str
    peers: Dict[str, PeerConnection] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


# {room_code: Room}
active_rooms: Dict[str, Room] = {}

# Лок для безопасного изменения состояния
rooms_lock = asyncio.Lock()


@router.websocket("/ws/room/{room_code}")
async def room_websocket(
    websocket: WebSocket, 
    room_code: str,
    token: Optional[str] = Query(None),
):
    """
    WebSocket endpoint для видеочата
    
    Обрабатывает:
    - WebRTC signaling (offer/answer/ice_candidate)
    - Медиа статусы (mic/camera/screen)
    - Heartbeat для определения живых соединений
    """
    await websocket.accept()
    user_id = str(uuid.uuid4())
    
    logger.info(f"[WS] 🔌 Подключение: {user_id} → комната '{room_code}'")
    
    peer: Optional[PeerConnection] = None
    room: Optional[Room] = None
    
    try:
        # === ИНИЦИАЛИЗАЦИЯ ===
        async with rooms_lock:
            # Создаем комнату если не существует
            if room_code not in active_rooms:
                active_rooms[room_code] = Room(code=room_code)
                logger.info(f"[WS] 🏠 Создана комната '{room_code}'")
            
            room = active_rooms[room_code]
            
            # Создаем peer
            peer = PeerConnection(
                user_id=user_id,
                websocket=websocket
            )
            room.peers[user_id] = peer
            
            logger.info(f"[WS] 👤 Добавлен peer {user_id}. Всего в комнате: {len(room.peers)}")
            
            # Получаем список других участников
            other_peers = [
                {
                    "id": p.user_id,
                    "audioOn": p.audio_on,
                    "videoOn": p.video_on,
                    "screenSharing": p.screen_sharing
                }
                for uid, p in room.peers.items() 
                if uid != user_id
            ]
        
        # Отправляем новому участнику список существующих
        await websocket.send_json({
            "type": "active_peers",
            "peers": other_peers,
            "your_id": user_id
        })
        logger.info(f"[WS] 📋 Отправлено {len(other_peers)} активных участников → {user_id}")
        
        # Даем время на обработку на фронте
        await asyncio.sleep(0.1)
        
        # Уведомляем остальных о новом участнике
        new_peer_info = {
            "type": "peer_joined",
            "peer": {
                "id": user_id,
                "audioOn": peer.audio_on,
                "videoOn": peer.video_on,
                "screenSharing": peer.screen_sharing
            }
        }
        
        logger.info(f"[WS] 📣 Уведомляем комнату о новом участнике: {user_id}")
        await broadcast_to_room(room_code, new_peer_info, exclude=user_id)
        
        logger.info(f"[WS] ✅ Инициализация завершена для {user_id}. Всего участников: {len(room.peers)}")
        
        # === ОСНОВНОЙ ЦИКЛ ===
        while True:
            try:
                # Таймаут для обнаружения зависших соединений
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                message = json.loads(data)
                
                msg_type = message.get("type")
                logger.debug(f"[WS] 📨 {user_id}: {msg_type}")
                
                # Обновляем timestamp последней активности
                async with rooms_lock:
                    if peer:
                        peer.last_ping = datetime.utcnow()
                
                # === WebRTC SIGNALING ===
                if msg_type in ["offer", "answer", "ice_candidate"]:
                    await handle_webrtc_signal(room_code, user_id, message)
                
                # === МЕДИА СТАТУСЫ ===
                elif msg_type == "media_status":
                    await handle_media_status(room_code, user_id, message)
                
                # === HEARTBEAT ===
                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong"})
                
                # === УПРАВЛЕНИЕ RTC СОЕДИНЕНИЯМИ ===
                elif msg_type == "rtc_connected":
                    # Фронтенд сообщает что установил соединение с peer
                    target_id = message.get("peer_id")
                    if target_id:
                        async with rooms_lock:
                            if peer:
                                peer.active_rtc_connections.add(target_id)
                        logger.info(f"[WS] 🔗 RTC установлено: {user_id} ↔ {target_id}")
                
                elif msg_type == "rtc_disconnected":
                    # Фронтенд сообщает что разорвал соединение с peer
                    target_id = message.get("peer_id")
                    if target_id:
                        async with rooms_lock:
                            if peer:
                                peer.active_rtc_connections.discard(target_id)
                        logger.info(f"[WS] 🔌 RTC разорвано: {user_id} ↔ {target_id}")
                
                else:
                    logger.warning(f"[WS] ⚠️ Неизвестный тип: {msg_type} от {user_id}")
            
            except asyncio.TimeoutError:
                # Проверяем живо ли соединение
                try:
                    await websocket.send_json({"type": "ping"})
                    logger.debug(f"[WS] 🏓 Ping отправлен → {user_id}")
                except Exception as e:
                    logger.warning(f"[WS] ⏱️ Timeout для {user_id}, соединение мертво: {e}")
                    break
    
    except WebSocketDisconnect:
        logger.info(f"[WS] 🔴 Отключился: {user_id}")
    
    except Exception as e:
        logger.error(f"[WS] ❌ Ошибка для {user_id}: {e}", exc_info=True)
    
    finally:
        # === CLEANUP ===
        logger.info(f"[WS] 🧹 Начинаем cleanup для {user_id}")
        await cleanup_peer(room_code, user_id)


async def handle_webrtc_signal(room_code: str, from_id: str, message: dict):
    """
    Обработка WebRTC signaling сообщений
    
    Args:
        room_code: Код комнаты
        from_id: ID отправителя
        message: Сообщение (offer/answer/ice_candidate)
    """
    msg_type = message.get("type")
    target_id = message.get("target")
    
    if not target_id:
        logger.warning(f"[WS] ⚠️ {msg_type} без target от {from_id}")
        return
    
    target_ws = None
    
    async with rooms_lock:
        room = active_rooms.get(room_code)
        if not room:
            logger.warning(f"[WS] ⚠️ Комната {room_code} не найдена")
            return
        
        target_peer = room.peers.get(target_id)
        if not target_peer:
            logger.warning(f"[WS] ⚠️ Target {target_id} не найден в комнате {room_code}")
            return
        
        target_ws = target_peer.websocket
    
    # Отправляем вне lock
    # Добавляем from в сообщение
    message["from"] = from_id
    
    try:
        await target_ws.send_json(message)
        logger.debug(f"[WS] ✅ {msg_type}: {from_id} → {target_id}")
    except Exception as e:
        logger.error(f"[WS] ❌ Ошибка отправки {msg_type} к {target_id}: {e}")
        # Помечаем соединение как мертвое
        await cleanup_peer(room_code, target_id)


async def handle_media_status(room_code: str, from_id: str, message: dict):
    """
    Обработка изменения медиа-статуса (mic/camera/screen)
    
    Args:
        room_code: Код комнаты
        from_id: ID отправителя
        message: Сообщение со статусом
    """
    status = message.get("status", {})
    audio_on = status.get("audioOn")
    video_on = status.get("videoOn")
    screen_sharing = status.get("screenSharing")
    
    logger.info(
        f"[WS] 🎬 Медиа статус от {from_id}: "
        f"audio={audio_on}, video={video_on}, screen={screen_sharing}"
    )
    
    # Обновляем состояние peer
    async with rooms_lock:
        room = active_rooms.get(room_code)
        if room and from_id in room.peers:
            peer = room.peers[from_id]
            if audio_on is not None:
                peer.audio_on = audio_on
            if video_on is not None:
                peer.video_on = video_on
            if screen_sharing is not None:
                peer.screen_sharing = screen_sharing
    
    # Транслируем всем остальным
    await broadcast_to_room(room_code, {
        "type": "media_status",
        "from": from_id,
        "status": {
            "audioOn": audio_on,
            "videoOn": video_on,
            "screenSharing": screen_sharing
        }
    }, exclude=from_id)


async def broadcast_to_room(
    room_code: str, 
    message: dict, 
    exclude: Optional[str] = None
):
    """
    Отправить сообщение всем участникам комнаты
    
    Args:
        room_code: Код комнаты
        message: Сообщение для отправки
        exclude: User ID которого исключить из рассылки
    """
    peers_to_notify = []
    
    async with rooms_lock:
        room = active_rooms.get(room_code)
        if not room:
            logger.warning(f"[BROADCAST] ⚠️ Комната {room_code} не найдена")
            return
        
        # Копируем список для итерации вне lock
        peers_to_notify = [
            (uid, peer.websocket) 
            for uid, peer in room.peers.items() 
            if uid != exclude
        ]
        
        logger.info(
            f"[BROADCAST] 📡 Отправка '{message.get('type')}' "
            f"в комнату {room_code} для {len(peers_to_notify)} участников"
        )
    
    if not peers_to_notify:
        logger.info(f"[BROADCAST] ℹ️ Нет получателей для сообщения в комнате {room_code}")
        return
    
    # Отправляем без удержания lock
    disconnected = []
    for user_id, ws in peers_to_notify:
        try:
            # Таймаут на отправку чтобы не зависнуть
            await asyncio.wait_for(ws.send_json(message), timeout=5.0)
            logger.debug(f"[BROADCAST] ✅ → {user_id}")
        except asyncio.TimeoutError:
            logger.error(f"[BROADCAST] ⏱️ Timeout отправки к {user_id}")
            disconnected.append(user_id)
        except Exception as e:
            logger.error(f"[BROADCAST] ❌ Ошибка отправки к {user_id}: {e}")
            disconnected.append(user_id)
    
    # Удаляем мертвые соединения
    for user_id in disconnected:
        await cleanup_peer(room_code, user_id)


async def cleanup_peer(room_code: str, user_id: str):
    """
    Удалить участника из комнаты и уведомить остальных
    
    Args:
        room_code: Код комнаты
        user_id: ID участника для удаления
    """
    peer_existed = False
    ws_to_close = None
    
    async with rooms_lock:
        room = active_rooms.get(room_code)
        if not room:
            logger.warning(f"[CLEANUP] ⚠️ Комната {room_code} не найдена")
            return
        
        # Удаляем peer
        peer = room.peers.pop(user_id, None)
        if peer:
            peer_existed = True
            ws_to_close = peer.websocket
            logger.info(
                f"[CLEANUP] 🗑️ Удален {user_id} из комнаты '{room_code}'. "
                f"Осталось участников: {len(room.peers)}"
            )
        
        # Удаляем пустую комнату
        if len(room.peers) == 0:
            del active_rooms[room_code]
            logger.info(f"[CLEANUP] 🏚️ Комната '{room_code}' удалена (пустая)")
    
    # Закрываем WebSocket вне lock
    if ws_to_close:
        try:
            await ws_to_close.close()
        except Exception as e:
            logger.debug(f"[CLEANUP] WebSocket уже закрыт для {user_id}: {e}")
    
    # Уведомляем остальных участников только если peer существовал
    if peer_existed:
        logger.info(f"[CLEANUP] 📣 Уведомляем комнату об уходе {user_id}")
        await broadcast_to_room(room_code, {
            "type": "peer_left",
            "peer_id": user_id
        })


# === ФОНОВАЯ ЗАДАЧА: ОЧИСТКА МЕРТВЫХ СОЕДИНЕНИЙ ===
async def cleanup_stale_connections():
    """
    Периодическая проверка и удаление зависших соединений
    Запускать через lifespan или startup event
    """
    while True:
        await asyncio.sleep(60)  # Каждую минуту
        
        try:
            now = datetime.utcnow()
            stale_threshold = 120  # 2 минуты без активности
            
            stale_peers_by_room = {}
            
            async with rooms_lock:
                for room_code, room in list(active_rooms.items()):
                    stale_peers = [
                        uid for uid, peer in room.peers.items()
                        if (now - peer.last_ping).total_seconds() > stale_threshold
                    ]
                    
                    if stale_peers:
                        stale_peers_by_room[room_code] = stale_peers
                        logger.warning(
                            f"[CLEANUP] ⚠️ Найдено {len(stale_peers)} зависших peers "
                            f"в комнате {room_code}: {stale_peers}"
                        )
            
            # Cleanup вне lock
            for room_code, stale_peers in stale_peers_by_room.items():
                for uid in stale_peers:
                    logger.warning(f"[CLEANUP] 🧹 Удаляю зависший peer: {uid}")
                    await cleanup_peer(room_code, uid)
        
        except Exception as e:
            logger.error(f"[CLEANUP] ❌ Ошибка очистки: {e}", exc_info=True)


# === UTILITY: Получить информацию о комнате (для отладки) ===
@router.get("/rooms/{room_code}/info")
async def get_room_info(room_code: str):
    """Получить информацию о комнате для отладки"""
    async with rooms_lock:
        room = active_rooms.get(room_code)
        if not room:
            return {"error": "Room not found", "room_code": room_code}
        
        return {
            "room_code": room_code,
            "created_at": room.created_at.isoformat(),
            "peer_count": len(room.peers),
            "peers": [
                {
                    "id": peer.user_id,
                    "audio_on": peer.audio_on,
                    "video_on": peer.video_on,
                    "screen_sharing": peer.screen_sharing,
                    "connected_at": peer.connected_at.isoformat(),
                    "last_ping": peer.last_ping.isoformat(),
                    "active_rtc_connections": list(peer.active_rtc_connections)
                }
                for peer in room.peers.values()
            ]
        }
