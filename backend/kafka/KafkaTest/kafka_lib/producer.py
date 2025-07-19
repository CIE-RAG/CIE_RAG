from kafka import KafkaProducer
from kafka.errors import KafkaError
import json
import logging
import sys
from tenacity import retry, stop_after_attempt, wait_exponential

# Configure logging
logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("kafka.producer")

class KafkaProducerClient:
    def __init__(self, bootstrap_servers: str = "kafka:9092"):
        logger.debug(f"Attempting to connect to Kafka at {bootstrap_servers}")
        self.producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            acks="all",
            retries=5,
            linger_ms=100,
            batch_size=16384,
            compression_type="gzip"
        )
        logger.info("Successfully connected to Kafka")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def send(self, topic: str, key: str, message: str):
        logger.debug(f"Trying to Send to Kafka: {topic}, {message}")
        future = self.producer.send(
            topic=topic, 
            key=key.encode('utf-8') if key else None, 
            value=message
        )
        try:
            record_metadata = future.get(timeout=10)
            logger.info(f"Message sent to {topic}:{record_metadata.partition}:{record_metadata.offset}")
        except KafkaError as e:
            logger.error(f"Failed to send message: {e}")
            raise

    def flush(self):
        self.producer.flush()

    def close(self):
        self.producer.close()