import json
import logging
from kafka import KafkaProducer, KafkaConsumer
from src.config import settings

logger = logging.getLogger(__name__)

class KafkaManager:
    def __init__(self):
        self.producer = None
        self._connect_producer()
    
    def _connect_producer(self):
        """Подключает Kafka Producer"""
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                acks='all',
                retries=3,
                request_timeout_ms=30000,
                api_version=(2, 0, 2)
            )
            logger.info("✅ Kafka Producer подключен")
        except Exception as e:
            logger.error(f"❌ Ошибка подключения Kafka Producer: {e}")
            self.producer = None
    
    def send_parsing_task(self, task_data: dict):
        """Отправляет задачу на парсинг в Kafka"""
        if not self.producer:
            logger.error("❌ Kafka Producer не инициализирован")
            return False
        
        try:
            future = self.producer.send(
                'parsing-tasks', 
                value=task_data
            )
            # Ждем подтверждения
            future.get(timeout=10)
            logger.info(f"✅ Задача отправлена в Kafka: {task_data['case_number']}")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка отправки задачи в Kafka: {e}")
            return False
    
    def create_consumer(self):
        """Создает Kafka Consumer"""
        try:
            consumer = KafkaConsumer(
                'parsing-tasks',
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                group_id=settings.KAFKA_CONSUMER_GROUP,
                value_deserializer=lambda v: json.loads(v.decode('utf-8')),
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                api_version=(2, 0, 2)
            )
            logger.info("✅ Kafka Consumer создан")
            return consumer
        except Exception as e:
            logger.error(f"❌ Ошибка создания Kafka Consumer: {e}")
            return None
    
    def close(self):
        """Закрывает соединения"""
        if self.producer:
            self.producer.close()
            logger.info("✅ Kafka Producer закрыт")