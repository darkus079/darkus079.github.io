import asyncio
import logging
import os
from kafka import KafkaConsumer
from aiogram import Bot
from src.config import settings
from src.download_service import DownloadService
import json

logger = logging.getLogger(__name__)

class ParsingWorker:
    def __init__(self, worker_id: str = "worker-1"):
        self.worker_id = worker_id
        self.bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        self.download_service = DownloadService()
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
        """Обрабатывает одну задачу со скачиванием файлов"""
        case_number = task_data['case_number']
        user_id = task_data['user_id']
        chat_id = task_data['chat_id']
        
        logger.info(f"📥 {self.worker_id} получил задачу: {case_number}")
        
        try:
            # Уведомляем о начале обработки
            await self.bot.send_message(
                chat_id=chat_id,
                text=f"🔍 Обработка дела: {case_number}\n⏳ Скачивание документов... Это займет 1-2 минуты"
            )
            
            # ВРЕМЕННО: Используем известный UUID для тестирования
            known_uuids = {
                "А50-5568/08": "67f6384a-144d-4102-8831-e5c9a1a4c7bc",
                "А40-123456/2024": "67f6384a-144d-4102-8831-e5c9a1a4c7bc",  # тот же для теста
            }
            
            case_uuid = known_uuids.get(case_number)
            
            if not case_uuid:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ Дело {case_number} временно не поддерживается для скачивания.\nИспользуйте: А50-5568/08"
                )
                return
            
            # Скачиваем документы
            logger.info(f"🔄 Скачивание документов для UUID: {case_uuid}")
            archive_path = self.download_service.download_case_documents(case_uuid)
            
            # Отправляем архив
            await self._send_archive(chat_id, case_number, archive_path)
            
            logger.info(f"✅ {self.worker_id} завершил задачу: {case_number}")
            
        except Exception as e:
            logger.error(f"❌ {self.worker_id} ошибка обработки задачи {case_number}: {e}")
            await self._send_error(chat_id, case_number, str(e))
    
    async def _send_archive(self, chat_id: int, case_number: str, archive_path: str):
        """Отправляет ZIP-архив пользователю"""
        if not archive_path or not os.path.exists(archive_path):
            await self.bot.send_message(
                chat_id=chat_id,
                text=f"❌ Не удалось скачать документы для дела: {case_number}"
            )
            return
        
        try:
            # Читаем файл в память и создаем BufferedInputFile
            with open(archive_path, 'rb') as f:
                file_data = f.read()
            
            from aiogram.types import BufferedInputFile
            
            filename = f"documents_{case_number.replace('/', '_')}.zip"
            document = BufferedInputFile(file_data, filename=filename)
            
            # Отправляем архив
            await self.bot.send_document(
                chat_id=chat_id,
                document=document,
                caption=f"📦 Документы по делу: {case_number}"
            )
            
            # Уведомляем об успехе
            await self.bot.send_message(
                chat_id=chat_id,
                text=f"✅ Документы по делу {case_number} успешно скачаны и отправлены!"
            )
            
            # Очищаем временный архив
            self.download_service.cleanup_archive(archive_path)
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки архива: {e}")
            await self.bot.send_message(
                chat_id=chat_id,
                text=f"❌ Ошибка отправки документов: {e}"
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
        await self.bot.close()
        logger.info(f"🛑 {self.worker_id} остановлен")