# app/utils/auth.py
import asyncio
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
import base64
from jose import jwt
from passlib.context import CryptContext
from datetime import datetime, timedelta
from app.config import settings

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now() + timedelta(
        minutes=settings.auth.access_token_expire_minutes
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(
        to_encode,
        settings.auth.secret_key.get_secret_value(),
        algorithm=settings.auth.algorithm,
    )


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now() + timedelta(days=settings.auth.refresh_token_expire_days)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(
        to_encode,
        settings.auth.secret_key.get_secret_value(),
        algorithm=settings.auth.algorithm,
    )



from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
import base64

class SimpleRSA:
    """
    Упрощенный RSA класс с исправлениями
    """
    def __init__(self):
        self.key = {}  # Храним ключи по public_key_user
    
    async def generate(self, public_key_user: str) -> dict:
        """
        Генерация ключей - возвращает public_key сервера
        """
        if public_key_user in self.key:
            return {"public_key_server": self.key[public_key_user]["public_key_pem"]}
        
        # Генерируем ключи
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=1024,  # Уменьшили для простоты
        )
        public_key = private_key.public_key()
        
        # Сериализуем публичный ключ
        public_key_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
        
        # Сохраняем оба ключа
        self.key[public_key_user] = {
            "public_key": public_key,
            "private_key": private_key,
            "public_key_pem": public_key_pem
        }
        
        return {"public_key_server": public_key_pem}
    
    async def async_encode(self, message: str, public_key_user: str) -> str:
        """
        Шифрование сообщения публичным ключом пользователя
        """
        try:
            # Загружаем публичный ключ пользователя
            public_key = serialization.load_pem_public_key(
                public_key_user.encode('utf-8')
            )
            
            # Шифруем с более простым padding
            encrypted = public_key.encrypt(
                message.encode('utf-8'),
                padding.PKCS1v15()  # Более простой и надежный padding
            )
            return base64.b64encode(encrypted).decode('utf-8')
        except Exception as e:
            raise Exception(f"Ошибка шифрования: {e}")
    
    def sync_encode(self, message: str, public_key_user: str) -> str:
        """
        Синхронное шифрование
        """
        try:
            public_key = serialization.load_pem_public_key(
                public_key_user.encode('utf-8')
            )
            
            encrypted = public_key.encrypt(
                message.encode('utf-8'),
                padding.PKCS1v15()
            )
            return base64.b64encode(encrypted).decode('utf-8')
        except Exception as e:
            raise Exception(f"Ошибка шифрования: {e}")
    
    async def async_decode(self, encrypted_message: str, public_key_user: str) -> str:
        """
        Дешифрование сообщения приватным ключом сервера
        """
        try:
            # Используем public_key_user как ключ для поиска
            if public_key_user not in self.key:
                raise Exception("Ключ не найден")
            
            encrypted_bytes = base64.b64decode(encrypted_message)
            private_key = self.key[public_key_user]["private_key"]
            
            decrypted = private_key.decrypt(
                encrypted_bytes,
                padding.PKCS1v15()  # Тот же padding что и при шифровании
            )
            return decrypted.decode('utf-8')
        except Exception as e:
            raise Exception(f"Ошибка дешифрования: {e}")
    
    def sync_decode(self, encrypted_message: str, public_key_user: str) -> str:
        """
        Синхронное дешифрование
        """
        try:
            if public_key_user not in self.key:
                raise Exception("Ключ не найден")
            
            encrypted_bytes = base64.b64decode(encrypted_message)
            private_key = self.key[public_key_user]["private_key"]
            
            decrypted = private_key.decrypt(
                encrypted_bytes,
                padding.PKCS1v15()
            )
            return decrypted.decode('utf-8')
        except Exception as e:
            raise Exception(f"Ошибка дешифрования: {e}")
rs=SimpleRSA()
