from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings as _BaseSettings
from pydantic_settings import SettingsConfigDict
from sqlalchemy import URL


class BaseSettings(_BaseSettings):  # Создаем свой BaseSettings
    model_config = SettingsConfigDict(
        extra="ignore",  # Игнорируем лишние поля
        env_file=".env",  # Обозначаем файл где содержаться переменные окружения
        env_file_encoding="utf-8",  # Кодировка файла чтобы не было кракозябр
    )


class PostgresConfig(BaseSettings, env_prefix="POSTGRES_"):
    """Конфиг для базы данных postgres"""

    host: str = Field(
        ..., description="Айпи где расположена база данных", example="123.52.13.16"
    )
    port: int = Field(
        ..., description="Порт по которому работает база данных", example=5432
    )
    user: str = Field(
        ..., description="Пользователь в базе данных", example="products_user"
    )
    password: SecretStr = Field(
        ...,
        description="Пароль от пользователя в базе данных",
        example="123***********",
    )
    db: str = Field(
        ...,
        description="Название базы данных к которой подключаемся",
        example="products_db",
    )

    def build_dsn(self) -> str:
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.user,
            password=self.password.get_secret_value(),
            host=self.host,
            port=self.port,
            database=self.db,
        ).render_as_string(hide_password=False)


class AuthConfig(BaseSettings, env_prefix="AUTH_"):
    """Конфигурация аутентификации"""

    secret_key: SecretStr = Field(
        ...,
        description="Секретный ключ для JWT",
        example="your-256-bit-secret-key-change-in-production",
    )
    algorithm: str = Field(default="HS256", description="Алгоритм шифрования")
    access_token_expire_minutes: int = Field(
        default=30, description="Время жизни access токена в минутах"
    )
    refresh_token_expire_days: int = Field(
        default=7, description="Время жизни refresh токена в днях"
    )

    cookie_secure: bool = Field(
        default=True,  # False для разработки, True для продакшена
        description="Использовать secure cookies (только HTTPS)",
    )
    cookie_httponly: bool = Field(default=True, description="HttpOnly флаг для cookies")
    cookie_samesite: str = Field(
        default="none", description="SameSite политика для cookies"
    )
    cookie_domain: str | None = Field(
        default=None, description="domain политика для cookies"
    )

class Config(BaseSettings):
    """
    Основной конфиг который будем инициализировать
    """

    auth: AuthConfig = Field(default_factory=AuthConfig)
    postgres: PostgresConfig = Field(default_factory=PostgresConfig)


settings = Config()
