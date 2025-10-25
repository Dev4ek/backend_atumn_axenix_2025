from typing import Dict, List, Optional
from datetime import datetime, timedelta
import asyncio
from collections import defaultdict


class NotificationService:
    def __init__(self):
        self.room_subscribers: Dict[int, List[str]] = defaultdict(list)
        self.pending_notifications: Dict[int, List[Dict]] = defaultdict(list)
        self.last_message_ids: Dict[int, int] = {}
        
    def subscribe_user(self, room_id: int, user_token: str):
        """Подписка пользователя на уведомления комнаты"""
        if user_token not in self.room_subscribers[room_id]:
            self.room_subscribers[room_id].append(user_token)
    
    def unsubscribe_user(self, room_id: int, user_token: str):
        """Отписка пользователя от уведомлений"""
        if user_token in self.room_subscribers[room_id]:
            self.room_subscribers[room_id].remove(user_token)
    
    def add_notification(self, room_id: int, notification: Dict):
        """Добавление уведомления для комнаты"""
        self.pending_notifications[room_id].append({
            **notification,
            "timestamp": datetime.utcnow()
        })
        
        # Ограничиваем историю уведомлений
        if len(self.pending_notifications[room_id]) > 50:
            self.pending_notifications[room_id] = self.pending_notifications[room_id][-50:]
    
    def get_pending_notifications(self, room_id: int, last_check: datetime) -> List[Dict]:
        """Получение уведомлений после указанной даты"""
        return [
            notif for notif in self.pending_notifications[room_id]
            if notif["timestamp"] > last_check
        ]
    
    def update_last_message_id(self, room_id: int, message_id: int):
        """Обновление ID последнего сообщения в комнате"""
        self.last_message_ids[room_id] = message_id
    
    def get_new_messages_count(self, room_id: int, last_message_id: int) -> int:
        """Получение количества новых сообщений"""
        current_last_id = self.last_message_ids.get(room_id, 0)
        return max(0, current_last_id - last_message_id)


notification_service = NotificationService()