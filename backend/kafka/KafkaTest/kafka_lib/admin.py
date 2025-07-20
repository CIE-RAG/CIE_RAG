from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError
from typing import List
import logging

logger = logging.getLogger("kafka.admin")

class KafkaAdmin:
    def __init__(self, bootstrap_servers: str = "kafka:9092"):
        self.admin = KafkaAdminClient(
            bootstrap_servers=bootstrap_servers,
            client_id="kafka-admin-client"
        )

    def create_topic(self, name: str, partitions: int = 3, replication: int = 1):
        """Idempotent topic creation"""
        topic = NewTopic(
            name=name,
            num_partitions=partitions,
            replication_factor=replication,
            topic_configs={
                "retention.ms": "120000",  # 7 days
                "cleanup.policy": "compact,delete"
            }
        )
        try:
            self.admin.create_topics([topic])
            logger.info(f"Created topic: {name}")
        except TopicAlreadyExistsError:
            logger.debug(f"Topic already exists: {name}")

    def delete_topic(self, name: str):
        self.admin.delete_topics([name])
        logger.info(f"Deleted topic: {name}")

    def list_topics(self) -> List[str]:
        return self.admin.list_topics()