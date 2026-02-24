import os
from pathlib import Path

from dotenv import load_dotenv

# Определяем текущую директорию
CURRENT_DIRECTORY = Path(__file__).parent.resolve()

# Загружаем .env (если есть)
load_dotenv(dotenv_path=CURRENT_DIRECTORY.parent / ".env")

# MODEL_PATH — читаем из переменной окружения или используем значение по умолчанию
MODEL_PATH = os.getenv("MODEL_PATH")
if not MODEL_PATH:
    MODEL_PATH = CURRENT_DIRECTORY.parent / "model" / "diabetes_model.onnx"
# Преобразуем в строку
MODEL_PATH = str(MODEL_PATH)

# STATIC_PATH — путь к статическим файлам
STATIC_PATH = os.getenv("STATIC_PATH")
if not STATIC_PATH:
    STATIC_PATH = CURRENT_DIRECTORY.parent / "static"
# Преобразуем в строку
STATIC_PATH = str(STATIC_PATH)

# Путь монтирования в API (должен быть строкой и начинаться с "/")
STATIC_MOUNT_PATH = os.getenv("STATIC_MOUNT_PATH", "/static")
assert isinstance(STATIC_MOUNT_PATH, str), "STATIC_MOUNT_PATH must be a string"
assert STATIC_MOUNT_PATH.startswith("/"), "STATIC_MOUNT_PATH must start with '/'"