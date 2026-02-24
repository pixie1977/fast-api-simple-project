FROM python:3.12-slim

WORKDIR /app

ENV MODEL_PATH=/app/src/model/diabetes_model.onnx \
    STATIC_DIR=/app/src/static

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 80

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "80"]