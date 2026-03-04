"""
FastAPI-приложение для предсказания диабета с JWT-аутентификацией и RBAC.
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional, Any, Coroutine

import onnxruntime as rt
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from starlette.responses import HTMLResponse

from src.config.config import (
    TOKEN_EXPIRE_DELTA,
    DEFAULT_ROLE,
    MODEL_PATH,
    STATIC_PATH,
)
from src.models import UserInDB, UserCreate, Token, PredictionRequest
from src.user_auth_utils import (
    authenticate_user,
    create_access_token,
    get_current_active_user,
    require_role,
    fake_users_db,
    get_password_hash,
    save_users,
)

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("diabetes-api")

app = FastAPI(title="Diabetes Prediction API", version="1.0")

# Загрузка ONNX-модели
try:
    sess = rt.InferenceSession(str(MODEL_PATH))
    input_name = sess.get_inputs()[0].name
    logger.info("ONNX модель загружена успешно.")
except Exception as e:
    logger.error(f"Ошибка загрузки модели: {e}")
    raise


@app.post("/auth/register", response_model=UserInDB, status_code=201)
async def register(user: UserCreate) -> UserInDB:
    """
    Регистрация нового пользователя.

    :param user: Данные нового пользователя.
    :return: Созданный пользователь.
    :raises HTTPException: При конфликте имён.
    """
    if user.username in fake_users_db:
        raise HTTPException(status_code=409, detail="Username already registered")
    hashed = get_password_hash(user.password)
    new_user = UserInDB(
        username=user.username,
        email=user.email,
        hashed_password=hashed,
        role=DEFAULT_ROLE,
    )
    fake_users_db[user.username] = new_user
    save_users(fake_users_db)
    logger.info(f"User '{user.username}' registered.")
    return new_user


@app.post("/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()) -> dict[str, str | int]:
    """
    Аутентификация пользователя и выдача JWT-токена.

    :param form_data: Данные формы (username, password).
    :return: JWT-токен.
    :raises HTTPException: При неверных учётных данных.
    """
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        logger.warning(f"Failed login attempt for {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"subject": user.username, "role": user.role})
    logger.info(f"User '{user.username}' logged in.")
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": int(TOKEN_EXPIRE_DELTA.total_seconds()),
    }


@app.post("/auth/logout")
async def logout(current_user: UserInDB = Depends(get_current_active_user)) -> dict:
    """
    Выход из системы (заглушка).

    :param current_user: Текущий аутентифицированный пользователь.
    :return: Сообщение об успешном выходе.
    """
    logger.info(f"User '{current_user.username}' logged out.")
    return {"message": "Successfully logged out"}


@app.get("/me")
async def read_users_me(current_user: UserInDB = Depends(get_current_active_user)) -> dict:
    """
    Возвращает профиль текущего пользователя.

    :param current_user: Текущий аутентифицированный пользователь.
    :return: Профиль пользователя.
    """
    return {
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
    }


@app.post("/predict")
async def predict(
    data: PredictionRequest,
    current_user: UserInDB = Depends(require_role("user")),
) -> dict:
    """
    Выполняет предсказание диабета на основе входных данных.
    Доступно для user и admin.

    :param data: Входные данные пациента.
    :param current_user: Текущий пользователь.
    :return: Результат предсказания.
    :raises HTTPException: При ошибках модели.
    """
    logger.info(f"User {current_user.username} requests /predict: {data}")

    input_data = [[data.Pregnancies, data.Glucose, data.BMI, data.Age]]
    try:
        pred = sess.run(None, {input_name: input_data})[0][0]
        prediction = 1 if pred > 0.5 else 0
        return {
            "prediction": prediction,
            "probability": round(float(pred), 4),
        }
    except Exception as e:
        logger.error(f"Inference failed: {e}")
        raise HTTPException(status_code=500, detail="Model error")


@app.get("/admin/metrics")
async def admin_metrics(current_user: UserInDB = Depends(require_role("admin"))) -> dict:
    """
    Админ-эндпоинт: метрики и информация о системе.
    Доступно только для admin.

    :param current_user: Текущий пользователь (должен быть admin).
    :return: Информация о системе.
    :raises HTTPException: При недостатке прав.
    """
    return {
        "message": "Admin metrics endpoint (stub)",
        "user": current_user.username,
        "role": current_user.role,
        "uptime": "up",
        "version": "1.0",
    }


@app.get("/", response_class=HTMLResponse)
async def serve_home() -> HTMLResponse:
    """
    Возвращает главную страницу index.html.

    :return: HTML-содержимое страницы.
    :raises HTTPException: При отсутствии файла.
    """
    index_path = Path(STATIC_PATH) / "index.html"
    try:
        with open(index_path, "r", encoding="utf-8") as f:
            content = f.read()
        return HTMLResponse(content=content)
    except FileNotFoundError:
        logger.error(f"Файл не найден: {index_path}")
        raise HTTPException(status_code=404, detail="Страница не найдена")
    except Exception as e:
        logger.error(f"Ошибка при чтении index.html: {e}")
        raise HTTPException(status_code=500, detail="Ошибка сервера")


if __name__ == "__main__":
    # Запуск сервера (только для разработки)
    uvicorn.run("src.main:app", host="127.0.0.1", port=8000, reload=True)