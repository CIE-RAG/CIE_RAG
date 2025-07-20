FROM python:3.10-slim
WORKDIR /app

COPY input_api_service/ .

RUN pip install fastapi uvicorn httpx python-multipart

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
