import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message

from src.config import settings
from src.kafka_manager import KafkaManager
from src.rate_limiter import RateLimiter

# Инициализация
bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
rate_limiter = RateLimiter()
kafka_manager = KafkaManager()

# Configure rate limiter with settings (с проверками)
rate_limiter.global_daily_limit = getattr(settings, 'GLOBAL_DAILY_LIMIT', 10000)
rate_limiter.per_user_daily_limit = getattr(settings, 'PER_USER_DAILY_LIMIT', 500)
rate_limiter.request_timeout_seconds = getattr(settings, 'REQUEST_TIMEOUT_SECONDS', 10.0)

logger = logging.getLogger(__name__)

@dp.message(Command("start"))
async def cmd_start(message: Message):
    try:
        from src.keyboards import get_main_keyboard
        keyboard = get_main_keyboard()
    except ImportError:
        keyboard = None
    
    await message.answer(
        "🤖 Бот для поиска судебных дел с Kafka\n\n"
        "Отправьте номер дела (например: А50-5568/08)\n"
        "Или используйте команду /parse <номер_дела>",
        reply_markup=keyboard
    )

@dp.message(Command("stats"))
async def cmd_stats(message: Message):
    """Показать статистику"""
    user_stats = rate_limiter.get_user_stats(message.from_user.id)
    global_stats = rate_limiter.get_global_stats()
    
    stats_text = (
        f"📊 Ваша статистика:\n"
        f"• Запросов сегодня: {user_stats['daily_requests']}/{user_stats['daily_limit']}\n"
        f"• Активных пользователей: {global_stats['active_users']}\n"
        f"• Всего запросов: {global_stats['total_daily_requests']}/{global_stats['global_limit']}"
    )
    
    await message.answer(stats_text)

@dp.message(Command("parse"))
async def cmd_parse(message: Message):
    user_id = message.from_user.id
    
    # Проверка лимитов
    if not await rate_limiter.check_limit(user_id):
        user_stats = rate_limiter.get_user_stats(user_id)
        await message.answer(
            f"❌ Превышен лимит запросов.\n"
            f"Использовано: {user_stats['daily_requests']}/{user_stats['daily_limit']} сегодня"
        )
        return
    
    # Извлекаем номер дела
    text_parts = message.text.split()
    if len(text_parts) > 1:
        case_number = ' '.join(text_parts[1:]).strip()  # Берем все после /parse
    else:
        await message.answer("❌ Укажите номер дела: /parse А50-5568/08")
        return
    
    # Без валидации - принимаем любой текст как номер дела
    if not case_number:
        await message.answer("❌ Укажите номер дела: /parse А50-5568/08")
        return
    
    # Создаем задачу для Kafka
    task_data = {
        "case_number": case_number,
        "user_id": user_id,
        "chat_id": message.chat.id,
        "username": message.from_user.username or "unknown"
    }
    
    # Отправляем в Kafka
    success = kafka_manager.send_parsing_task(task_data)
    
    if success:
        await message.answer(f"✅ Задача принята в обработку: {case_number}\nОжидайте результаты в этом чате...")
        await rate_limiter.record_request(user_id)
    else:
        await message.answer("❌ Ошибка системы. Попробуйте позже.")

async def process_case_number(case_number: str, user_id: int, chat_id: int, username: str = "unknown"):
    """Обрабатывает номер дела (вынесенная логика)"""
    # Создаем задачу для Kafka
    task_data = {
        "case_number": case_number,
        "user_id": user_id,
        "chat_id": chat_id,
        "username": username
    }
    
    # Проверка лимитов
    if not await rate_limiter.check_limit(user_id):
        user_stats = rate_limiter.get_user_stats(user_id)
        return f"❌ Превышен лимит запросов.\nИспользовано: {user_stats['daily_requests']}/{user_stats['daily_limit']} сегодня"
    
    # Отправляем в Kafka
    success = kafka_manager.send_parsing_task(task_data)
    
    if success:
        await rate_limiter.record_request(user_id)
        return f"✅ Задача принята в обработку: {case_number}\nОжидайте результаты в этом чате..."
    else:
        return "❌ Ошибка системы. Попробуйте позже."

@dp.message()
async def handle_message(message: Message):
    """Обработка обычных сообщений с номерами дел"""
    text = message.text.strip()
    
    # Игнорируем команды
    if text.startswith('/'):
        return
    
    # Принимаем ЛЮБОЙ текст как номер дела (без валидации)
    if text and len(text) > 3:  # Минимальная длина чтобы избежать случайных сообщений
        # Обрабатываем напрямую без изменения message.text
        result = await process_case_number(
            case_number=text,
            user_id=message.from_user.id,
            chat_id=message.chat.id,
            username=message.from_user.username or "unknown"
        )
        await message.answer(result)
    else:
        await message.answer(
            "Отправьте номер дела (например: А50-5568/08)\n"
            "Или используйте команду /parse <номер_дела>"
        )

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info("🚀 Запуск бота с Kafka...")
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"❌ Ошибка запуска бота: {e}")
    finally:
        kafka_manager.close()
        await bot.close()

if __name__ == "__main__":
    asyncio.run(main())