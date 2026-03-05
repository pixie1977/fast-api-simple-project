"""
Модуль с утилитами аутентификации и авторизации.
Содержит функции для работы с паролями, JWT и зависимостями FastAPI.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from src.config.config import (
    SECRET_KEY,
    ALGORITHM,
    TOKEN_EXPIRE_DELTA,
)
from src.models import UserInDB

# Путь к файлу с пользователями
USERS_FILE = Path(__file__).parent.parent / "data" / "users.json"


# Безопасность
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def load_users() -> dict:
    """
    Загружает пользователей из JSON-файла.

    :return: Словарь пользователей в формате {username: UserInDB}.
    """
    if USERS_FILE.exists():
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            users_data = json.load(f)
            return {
                username: UserInDB(**user) for username, user in users_data.items()
            }
    return {}


def save_users(users_db: dict) -> None:
    """
    Сохраняет пользователей в JSON-файл.

    :param users_db: Словарь пользователей для сохранения.
    """
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {
                username: user.dict()
                for username, user in users_db.items()
            },
            f,
            ensure_ascii=False,
            indent=2,
        )


# Хранилище пользователей (загружается из JSON-файла)
fake_users_db = load_users()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверяет, соответствует ли открытый пароль хэшу.

    :param plain_password: Открытый пароль (максимум 72 символа).
    :param hashed_password: Хэш пароля.
    :return: True, если пароли совпадают.
    """
    return pwd_context.verify(secret=plain_password[:72], hash=hashed_password)


def get_password_hash(password: str) -> str:
    """
    Возвращает хэш пароля.

    :param password: Пароль в открытом виде (максимум 72 символа).
    :return: Хэшированный пароль.
    """
    return pwd_context.hash(password[:72])


def create_access_token(data: dict) -> str:
    """
    Создаёт JWT-токен с заданными данными.

    :param data: Данные для включения в токен (например, subject, role).
    :return: Закодированный JWT-токен.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + TOKEN_EXPIRE_DELTA
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_user(username: str) -> Optional["UserInDB"]:
    """
    Возвращает пользователя по имени.

    :param username: Имя пользователя.
    :return: Объект UserInDB или None, если не найден.
    """
    return fake_users_db.get(username)


def authenticate_user(username: str, password: str) -> Optional["UserInDB"]:
    """
    Аутентифицирует пользователя по логину и паролю.

    :param username: Имя пользователя.
    :param password: Пароль.
    :return: Объект пользователя или False при ошибке.
    """
    user = get_user(username)
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)]
) -> "UserInDB":
    """
    Извлекает текущего пользователя из JWT-токена.

    :param token: Bearer-токен из заголовка Authorization.
    :return: Объект пользователя.
    :raises HTTPException: При невалидном токене.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("subject")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = get_user(username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: Annotated["UserInDB", Depends(get_current_user)]
) -> "UserInDB":
    """
    Проверяет, активен ли пользователь.

    :param current_user: Объект текущего пользователя.
    :return: Тот же объект (гарантия активности).
    """
    return current_user


def require_role(required_role: str):
    """
    Фабрика зависимостей: требует, чтобы у пользователя была минимум указанная роль.

    :param required_role: Минимальная требуемая роль ('user', 'admin').
    :return: Зависимость для использования в эндпоинтах.
    """
    async def role_checker(
        current_user: "UserInDB" = Depends(get_current_active_user)
    ) -> "UserInDB":
        roles = ["user", "admin"]
        if roles.index(current_user.role) < roles.index(required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user
    return role_checker