import json
import asyncio
import logging
from kafka import KafkaConsumer
from aiogram import Bot
from src.config import settings
from backend.parser_simplified import KadArbitrParser

logger = logging.getLogger(__name__)

class KafkaTaskConsumer:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.consumer = None
        self.parser = KadArbitrParser()
        self._connect()
    
    def _connect(self):
        try:
            self.consumer = KafkaConsumer(
                'parsing-tasks',
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                group_id='parsing-workers',
                value_deserializer=lambda v: json.loads(v.decode('utf-8')),
                key_deserializer=lambda k: k.decode('utf-8') if k else None,
                auto_offset_reset='earliest',
                enable_auto_commit=True
            )
            logger.info("✅ Kafka Consumer подключен")
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к Kafka: {e}")
            self.consumer = None
    
    async def process_tasks(self):
        """Основной цикл обработки задач"""
        if not self.consumer:
            logger.error("❌ Kafka Consumer не инициализирован")
            return
        
        logger.info("🔄 Запуск обработки задач из Kafka...")
        
        for message in self.consumer:
            try:
                task_data = message.value
                case_number = task_data['case_number']
                user_id = task_data['user_id']
                chat_id = task_data['chat_id']
                
                logger.info(f"📥 Получена задача: {case_number} для пользователя {user_id}")
                
                # Отправляем сообщение о начале обработки
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=f"🔍 Начинаю поиск дела: {case_number}\nОжидайте результаты..."
                )
                
                # Выполняем парсинг
                documents = await self._parse_case(case_number)
                
                # Отправляем результаты пользователю
                await self._send_results(chat_id, case_number, documents)
                
                logger.info(f"✅ Задача завершена: {case_number}")
                
            except Exception as e:
                logger.error(f"❌ Ошибка обработки задачи: {e}")
                # Отправляем сообщение об ошибке
                try:
                    await self.bot.send_message(
                        chat_id=task_data.get('chat_id', user_id),
                        text=f"❌ Произошла ошибка при обработке дела {case_number}"
                    )
                except:
                    pass
    
    async def _parse_case(self, case_number: str):
        """Парсит дело и возвращает список документов"""
        try:
            # Используем метод сбора ссылок вместо скачивания файлов
            documents = self.parser.collect_document_links(case_number)
            return documents
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга: {e}")
            return []
    
    async def _send_results(self, chat_id: int, case_number: str, documents: list):
        """Отправляет результаты пользователю"""
        if not documents:
            await self.bot.send_message(
                chat_id=chat_id,
                text=f"❌ По делу {case_number} не найдено документов"
            )
            return
        
        # Формируем сообщение с результатами
        message = f"✅ Найдено документов: {len(documents)}\n\n"
        
        for i, doc in enumerate(documents[:10], 1):  # Ограничиваем 10 документами
            doc_type = doc.get('type', 'PDF')
            doc_date = doc.get('date', 'дата неизвестна')
            message += f"{i}. {doc_type} ({doc_date})\n"
        
        message += f"\n📁 Полный список: {len(documents)} документов"
        
        await self.bot.send_message(
            chat_id=chat_id,
            text=message
        )
        
        # Отправляем файл со ссылками если нужно
        if len(documents) > 0:
            links_text = "\n".join([doc['url'] for doc in documents])
            # Можно отправить как файл если ссылок много
            if len(links_text) > 4000:
                await self.bot.send_document(
                    chat_id=chat_id,
                    document=("links.txt", links_text.encode())
                )
    
    def close(self):
        if self.consumer:
            self.consumer.close()
        if self.parser:
            self.parser.close()