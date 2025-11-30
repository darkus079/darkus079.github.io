import json
import logging
from aiogram import Bot
from kafka import KafkaProducer
from src.config import settings

logger = logging.getLogger(__name__)

class KafkaTaskProducer:
    def __init__(self):
        self.producer = None
        self._connect()
    
    def _connect(self):
        try:
            self.producer = KafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None,
                acks='all',
                retries=3
            )
            logger.info("✅ Kafka Producer подключен")
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к Kafka: {e}")
            self.producer = None
    
    async def send_parsing_task(self, case_number: str, user_id: int, chat_id: int):
        """Отправляет задачу на парсинг в Kafka"""
        if not self.producer:
            logger.error("❌ Kafka Producer не инициализирован")
            return False
        
        try:
            task_data = {
                "case_number": case_number,
                "user_id": user_id,
                "chat_id": chat_id,
                "timestamp": time.time()
            }
            
            # Отправляем в топик для парсинга
            future = self.producer.send(
                'parsing-tasks', 
                value=task_data,
                key=str(user_id)  # Группируем по пользователю
            )
            
            # Ждем подтверждения
            future.get(timeout=10)
            logger.info(f"✅ Задача отправлена в Kafka: {case_number} для пользователя {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки задачи в Kafka: {e}")
            return False
    
    def close(self):
        if self.producer:
            self.producer.close()