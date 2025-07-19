FROM python:3.10-slim
WORKDIR /app

# Shared library
COPY kafka_lib ./kafka_lib
RUN pip install kafka-python tenacity pydantic

# Service code
COPY consumer_service/ .
RUN pip install fastapi uvicorn better_profanity aiokafka

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
