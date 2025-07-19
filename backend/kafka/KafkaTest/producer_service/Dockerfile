FROM python:3.10-slim
WORKDIR /app

# Install shared library dependencies
COPY kafka_lib ./kafka_lib
RUN pip install kafka-python aiokafka tenacity pydantic better_profanity

# Install producer-specific FastAPI code
COPY producer_service/ .
RUN pip install fastapi uvicorn

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
