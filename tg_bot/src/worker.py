import asyncio
import logging
from kafka import KafkaConsumer
from aiogram import Bot
from src.config import settings
from backend.parser_simplified import KadArbitrParser
import json

logger = logging.getLogger(__name__)

class ParsingWorker:
    def __init__(self, worker_id: str = "worker-1"):
        self.worker_id = worker_id
        self.bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        self.parser = KadArbitrParser()
        self.consumer = None
        self.is_running = False
    
    async def start(self):
        """Запускает worker"""
        logger.info(f"👷 Запуск {self.worker_id}...")
        
        try:
            self.consumer = KafkaConsumer(
                'parsing-tasks',
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                group_id='parsing-workers',
                value_deserializer=lambda v: json.loads(v.decode('utf-8')),
                auto_offset_reset='earliest',
                enable_auto_commit=True
            )
            logger.info("✅ Kafka Consumer подключен")
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к Kafka: {e}")
            return
        
        self.is_running = True
        await self._process_messages()
    
    async def _process_messages(self):
        """Обрабатывает сообщения из Kafka"""
        logger.info(f"🔄 {self.worker_id} начал обработку сообщений...")
        
        for message in self.consumer:
            if not self.is_running:
                break
                
            try:
                task_data = message.value
                await self._process_task(task_data)
            except Exception as e:
                logger.error(f"❌ {self.worker_id} ошибка обработки сообщения: {e}")
    
    async def _process_task(self, task_data: dict):
        """Обрабатывает одну задачу"""
        case_number = task_data['case_number']
        user_id = task_data['user_id']
        chat_id = task_data['chat_id']
        
        logger.info(f"📥 {self.worker_id} получил задачу: {case_number}")
        
        try:
            # Уведомляем о начале обработки
            await self.bot.send_message(
                chat_id=chat_id,
                text=f"🔍 Начинаю поиск дела: {case_number}\n⏳ Это займет около 1-2 минут..."
            )
            
            # Выполняем парсинг
            logger.info(f"🔄 {self.worker_id} парсит дело: {case_number}")
            documents = self.parser.collect_document_links(case_number)
            
            # Отправляем результаты
            await self._send_results(chat_id, case_number, documents)
            
            logger.info(f"✅ {self.worker_id} завершил задачу: {case_number}")
            
        except Exception as e:
            logger.error(f"❌ {self.worker_id} ошибка обработки задачи {case_number}: {e}")
            await self._send_error(chat_id, case_number, str(e))
    
    async def _send_results(self, chat_id: int, case_number: str, documents: list):
        """Отправляет результаты пользователю с ссылками на PDF"""
        if not documents:
            await self.bot.send_message(
                chat_id=chat_id,
                text=f"❌ По делу {case_number} не найдено документов"
            )
            return
        
        # Формируем сообщение со ссылками
        message_lines = [f"✅ Найдено документов: {len(documents)}\n\n"]
        
        for i, doc in enumerate(documents[:15], 1):  # Ограничиваем 15 документами
            doc_name = doc.get('name', f'Документ {i}')
            doc_type = doc.get('type', 'PDF')
            doc_url = doc.get('url', '')
            doc_date = doc.get('date', '')
            
            date_str = f" ({doc_date})" if doc_date else ""
            
            if doc_url:
                message_lines.append(f"{i}. {doc_type}{date_str}: {doc_name}\n{doc_url}")
            else:
                message_lines.append(f"{i}. {doc_type}{date_str}: {doc_name} (ссылка недоступна)")
            
            # Добавляем пустую строку между документами для читаемости
            message_lines.append("")
        
        message = "\n".join(message_lines)
        
        # Если сообщение слишком длинное, разбиваем на части
        if len(message) > 4000:
            parts = [message[i:i+4000] for i in range(0, len(message), 4000)]
            for part in parts:
                await self.bot.send_message(
                    chat_id=chat_id, 
                    text=part,
                    disable_web_page_preview=True
                )
        else:
            await self.bot.send_message(
                chat_id=chat_id, 
                text=message,
                disable_web_page_preview=True
            )
    
    async def _send_error(self, chat_id: int, case_number: str, error: str):
        """Отправляет сообщение об ошибке"""
        error_message = (
            f"❌ Ошибка при обработке дела {case_number}\n\n"
            f"Ошибка: {error}\n\n"
            f"Попробуйте позже или проверьте правильность номера дела."
        )
        await self.bot.send_message(chat_id=chat_id, text=error_message)
    
    async def stop(self):
        """Останавливает worker"""
        self.is_running = False
        if self.consumer:
            self.consumer.close()
        if self.parser:
            self.parser.close()
        await self.bot.close()
        logger.info(f"🛑 {self.worker_id} остановлен")