# Kafka Library Consumer Client
# Async Kafka Consumer using aiokafka for real-time message streaming

from aiokafka import AIOKafkaConsumer
from kafka import TopicPartition, KafkaConsumer as SyncKafkaConsumer
from kafka.errors import NoBrokersAvailable
import json
import logging
from typing import Dict, Any, AsyncIterator, List
from tenacity import retry, stop_after_attempt, wait_exponential
import asyncio
from better_profanity import profanity

logger = logging.getLogger("kafka.consumer")

class KafkaConsumerClient:
    def __init__(
        self,
        topic: str,
        group_id: str,
        bootstrap_servers: str = "kafka:9092",
        auto_offset_reset: str = "earliest"
    ):
        self.topic = topic
        self.group_id = group_id
        self.bootstrap_servers = bootstrap_servers
        self.auto_offset_reset = auto_offset_reset
        self.consumer = None
        self.running = False

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def get_all_messages(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Fetch all available messages from the topic (non-blocking)"""
        profanity.load_censor_words()
        logger.info(f"Fetching messages from topic: {self.topic}")

        consumer = SyncKafkaConsumer(
            bootstrap_servers=self.bootstrap_servers,
            auto_offset_reset=self.auto_offset_reset,
            enable_auto_commit=False,
            value_deserializer=lambda x: json.loads(x.decode("utf-8")) if x else None,
            consumer_timeout_ms=1000
        )

        try:
            partitions = consumer.partitions_for_topic(self.topic)
            if not partitions:
                logger.warning(f"No partitions found for topic: {self.topic}")
                return []

            topic_partitions = [TopicPartition(self.topic, p) for p in partitions]
            consumer.assign(topic_partitions)
            consumer.seek_to_beginning()

            messages = []
            for _ in range(limit):
                batch = consumer.poll(timeout_ms=500)
                if not batch:
                    break

                for _, records in batch.items():
                    for msg in records:
                        value = msg.value
                        if self.topic == "query" and isinstance(value, dict) and "message" in value:
                            if profanity.contains_profanity(value["message"]):
                                value["message"] = profanity.censor(value["message"])

                        messages.append({
                            "topic": msg.topic,
                            "partition": msg.partition,
                            "offset": msg.offset,
                            "key": msg.key.decode() if msg.key else None,
                            "value": value,
                            "timestamp": msg.timestamp
                        })

            logger.info(f"Fetched {len(messages)} messages from {self.topic}")
            return messages

        finally:
            consumer.close()

    async def consume_async(self) -> AsyncIterator[Dict[str, Any]]:
        """Async generator to yield messages one-by-one in real-time"""
        profanity.load_censor_words()
        self.consumer = AIOKafkaConsumer(
            self.topic,
            loop=asyncio.get_event_loop(),
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            auto_offset_reset=self.auto_offset_reset,
            enable_auto_commit=True,
            value_deserializer=lambda x: json.loads(x.decode("utf-8")) if x else None
        )

        await self.consumer.start()
        self.running = True
        logger.info(f"Started async consumer on topic: {self.topic}")

        try:
            async for msg in self.consumer:
                value = msg.value
                if self.topic == "query" and isinstance(value, dict) and "message" in value:
                    if profanity.contains_profanity(value["message"]):
                        value["message"] = profanity.censor(value["message"])

                yield {
                    "topic": msg.topic,
                    "partition": msg.partition,
                    "offset": msg.offset,
                    "key": msg.key.decode() if msg.key else None,
                    "value": value,
                    "timestamp": msg.timestamp
                }
        finally:
            if self.consumer:
                await self.consumer.stop()
                logger.info(f"Stopped async consumer on topic: {self.topic}")
            self.running = False

    async def get_next_message(self) -> Dict[str, Any]:
        """
        Fetch the next unconsumed message for the topic using Kafka's committed offset.
        Ensures FIFO message consumption, one message at a time.
        """
        profanity.load_censor_words()

        consumer = AIOKafkaConsumer(
            self.topic,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            auto_offset_reset=self.auto_offset_reset,
            enable_auto_commit=True,
            value_deserializer=lambda x: json.loads(x.decode("utf-8")) if x else None
        )

        await consumer.start()
        try:
            msg = await consumer.getone()
            value = msg.value

            if self.topic == "query" and isinstance(value, dict) and "message" in value:
                if profanity.contains_profanity(value["message"]):
                    value["message"] = profanity.censor(value["message"])

            return {
                "topic": msg.topic,
                "partition": msg.partition,
                "offset": msg.offset,
                "key": msg.key.decode() if msg.key else None,
                "value": value,
                "timestamp": msg.timestamp
            }

        except Exception as e:
            logger.error(f"Error fetching next message: {e}")
            raise e
        finally:
            await consumer.stop()

    def stop(self):
        """Stop the async consumer"""
        self.running = False

    def close(self):
        """Close the sync consumer"""
        if self.consumer:
            try:
                if hasattr(self.consumer, 'close'):
                    self.consumer.close()
            except Exception as e:
                logger.error(f"Error closing consumer: {e}")
            finally:
                self.consumer = None
