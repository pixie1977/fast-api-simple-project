"""
Модели данных для приложения.
Определяет Pydantic-модели для пользователей, токенов и запросов предсказания.
"""

from typing import Optional

from pydantic import BaseModel, Field


class UserInDB(BaseModel):
    """
    Модель пользователя с хэшированным паролем и ролью.

    :ivar username: Имя пользователя.
    :ivar email: Email пользователя.
    :ivar hashed_password: Хэш пароля.
    :ivar role: Роль пользователя ('user', 'admin').
    """
    username: str
    email: str
    hashed_password: str
    role: str


class Token(BaseModel):
    """
    Модель ответа с JWT-токеном.

    :ivar access_token: Сам JWT-токен.
    :ivar token_type: Тип токена (по умолчанию 'bearer').
    :ivar expires_in: Время жизни токена в секундах.
    """
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    """
    Данные, извлечённые из токена.

    :ivar subject: Идентификатор пользователя (sub).
    :ivar role: Роль пользователя.
    """
    subject: Optional[str] = None
    role: Optional[str] = None


class UserCreate(BaseModel):
    """
    Модель для регистрации нового пользователя.

    :ivar username: Имя пользователя (минимум 3 символа).
    :ivar email: Email (должен соответствовать шаблону).
    :ivar password: Пароль (минимум 6 символов).
    """
    username: str = Field(..., min_length=3)
    email: str = Field(
        ..., pattern=r".+@.+\.(com|ru|org)", description="Email пользователя"
    )
    password: str = Field(..., min_length=6)


class PredictionRequest(BaseModel):
    """
    Модель входных данных для предсказания диабета.

    :ivar Pregnancies: Количество беременностей (0–20).
    :ivar Glucose: Уровень глюкозы в плазме натощак (50–200 mg/dL).
    :ivar BMI: Индекс массы тела (15–50).
    :ivar Age: Возраст (18–90 лет).
    """
    Pregnancies: int = Field(
        ..., ge=0, le=20, description="Количество беременностей"
    )
    Glucose: float = Field(
        ..., ge=50, le=200, description="Уровень глюкозы (mg/dL)"
    )
    BMI: float = Field(
        ..., ge=15, le=50, description="Индекс массы тела"
    )
    Age: int = Field(
        ..., ge=18, le=90, description="Возраст"
    )