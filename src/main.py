import logging
import secrets
from pathlib import Path
from typing import Annotated

import onnxruntime as rt
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from src.config.config import MODEL_PATH, STATIC_PATH, STATIC_MOUNT_PATH

app = FastAPI()
security = HTTPBasic()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("diabetes-api")

# Загружаем ONNX-модель
try:
    sess = rt.InferenceSession(MODEL_PATH)
    input_name = sess.get_inputs()[0].name
    logger.info(f"ONNX модель загружена успешно: {MODEL_PATH}")
except Exception as e:
    logger.error(f"Ошибка загрузки модели по пути {MODEL_PATH}: {e}")
    raise e


def verify_user(credentials: HTTPBasicCredentials = Depends(security)) -> str:
    """
    Проверяет учётные данные пользователя с помощью Basic Auth.
    """
    is_correct_username = secrets.compare_digest(credentials.username, "demo_user")
    is_correct_password = secrets.compare_digest(credentials.password, "demo_pass")
    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


# Монтируем статику — используем правильный путь из config
app.mount(STATIC_MOUNT_PATH, StaticFiles(directory=STATIC_PATH), name="static")


@app.get("/", response_class=HTMLResponse)
async def serve_home() -> HTMLResponse:
    """Возвращает главную страницу."""
    with open(Path(STATIC_PATH) / "index.html", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/greeting")
def greeting():
    """Публичный эндпоинт приветствия."""
    logger.info("GET /greeting accessed")
    return {"message": "Welcome to Diabetes Prediction API!"}


class PredictionRequest(BaseModel):
    """Модель входных данных для предсказания диабета."""

    Pregnancies: int = Field(..., ge=0, le=20, description="Количество беременностей")
    Glucose: float = Field(..., ge=50, le=200, description="Уровень глюкозы в плазме")
    BMI: float = Field(..., ge=15, le=50, description="Индекс массы тела")
    Age: int = Field(..., ge=18, le=90, description="Возраст")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "Pregnancies": 2,
                    "Glucose": 140,
                    "BMI": 35.5,
                    "Age": 32,
                }
            ]
        }
    }


@app.post("/predict")
def predict(
    data: PredictionRequest,
    username: Annotated[str, Depends(verify_user)],
):
    """Защищённый эндпоинт для предсказания диабета."""
    logger.info(f"Пользователь {username} делает запрос к /predict: {data.model_dump()}")

    input_data = [[data.Pregnancies, data.Glucose, data.BMI, data.Age]]

    try:
        pred = sess.run(None, {input_name: input_data})[0][0]
        prediction = 1 if pred > 0.5 else 0
        logger.info(f"Предсказание: {prediction}, вероятность={pred:.4f}")
        return {"prediction": prediction}
    except Exception as e:
        logger.error(f"Ошибка при выполнении инференса: {e}")
        raise HTTPException(status_code=500, detail="Model inference failed")


if __name__ == "__main__":
    uvicorn.run("src.main:app", host="127.0.0.1", port=8000, reload=True)