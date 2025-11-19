from __future__ import annotations

import asyncio
import os
from contextlib import suppress
from typing import Any, Dict

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramNetworkError
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery
from loguru import logger

from config import settings, state
from keyboards import main_menu_kb, parse_controls_kb
from queue_manager import queue_manager
from rate_limiter import global_counter


class UserStates(StatesGroup):
    waiting_for_case_number = State()


def is_admin(user_id: int) -> bool:
    return user_id in settings.ADMIN_IDS


async def on_update_message(message: Message, update: Any):
    if isinstance(update, dict) and update.get("type") == "result_links":
        links = update.get("links", [])
        case = update.get("case")
        chunks = []
        chunk = []
        total = 0
        for link in links:
            total += 1
            name = link.get("name") or "Document"
            url = link.get("url")
            date = link.get("date") or ""
            line = f"{total}. {name} {f'({date})' if date else ''}\n{url}"
            if sum(len(l) for l in chunk) + len(line) > 3500:
                chunks.append("\n".join(chunk))
                chunk = []
            chunk.append(line)
        if chunk:
            chunks.append("\n".join(chunk))

        header = f"Дело {case}. Найдено ссылок: {len(links)}"
        await message.answer(header)
        for part in chunks:
            await message.answer(part)
        return

    # string updates
    text = str(update)
    if text:
        await message.answer(text)


async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "unknown"
    logger.info(f"👋 /start command from user {user_id} (@{username})")
    await message.answer(
        "Привет! Отправьте /parse для запуска парсинга дела. ",
        reply_markup=main_menu_kb(),
    )


async def cmd_help(message: Message):
    await message.answer(
        "/parse — запустить парсинг\n"
        "/status — текущий статус\n"
        "/links — показать ссылки по номеру дела\n"
        "/history — история дел (бэкенд)\n"
        "/mode — переключение режима (links/download)\n"
        "/cancel — отменить текущую задачу\n"
        "/backend — показать текущий backend URL",
    )


async def cmd_mode(message: Message):
    state.default_mode = "download" if state.default_mode == "links" else "links"
    await message.answer(f"Режим: {state.default_mode}")


async def cmd_parse(message: Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username or "unknown"

    logger.info(f"🔍 /parse command from user {user_id} (@{username})")

    if queue_manager.has_active(user_id):
        logger.warning(f"🚫 User {user_id} has active task, rejecting new parse")
        await message.answer("У вас уже есть активная задача. Подождите завершения или отмените /cancel.")
        return

    await state.set_state(UserStates.waiting_for_case_number)
    await message.answer("Введите номер дела (например: А84-9028/2022):")


async def cmd_status(message: Message):
    current = queue_manager.get_user_status(message.from_user.id)
    if current:
        await message.answer(f"Выполняется: {current}")
    else:
        await message.answer("Активных задач нет")


async def cmd_links(message: Message, state: FSMContext):
    user_id = message.from_user.id

    if queue_manager.has_active(user_id):
        await message.answer("У вас уже есть активная задача. Подождите завершения или отмените /cancel.")
        return

    # Устанавливаем специальный флаг для режима links
    await state.set_state(UserStates.waiting_for_case_number)
    await state.update_data(mode="links")
    await message.answer("Введите номер дела для получения ссылок (например: А84-9028/2022):")


async def process_case_number(message: Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username or "unknown"
    case_number = message.text.strip()

    logger.info(f"📝 Received case number from user {user_id} (@{username}): '{case_number}'")

    # Получаем данные состояния
    data = await state.get_data()
    mode = data.get("mode", "parse")  # по умолчанию парсинг

    # Очищаем состояние
    await state.clear()

    # Проверяем лимиты
    ok, reason = global_counter.try_consume(user_id, 1)
    if not ok:
        logger.warning(f"🚫 Rate limit hit for user {user_id}: {reason}")
        await message.answer(reason)
        return

    if mode == "links":
        # Режим получения ссылок
        async def temp_update(upd):
            await on_update_message(message, upd)
        try:
            await queue_manager.submit(user_id, case_number, temp_update)
        except Exception as e:
            await message.answer(f"Ошибка: {e}")
    else:
        # Режим полного парсинга
        logger.info(f"✅ Submitting parse task for user {user_id}, case: {case_number}")
        await queue_manager.submit(
            user_id=user_id,
            case_number=case_number,
            on_update=lambda upd: on_update_message(message, upd),
        )
        await message.answer("Задача отправлена. Ожидайте обновлений.", reply_markup=parse_controls_kb(case_number))


async def cmd_history(message: Message):
    entries = queue_manager.get_history()
    if not entries:
        await message.answer("История пуста")
        return
    lines = []
    for i, h in enumerate(reversed(entries), 1):
        ok = "✅" if h.get("success") else "❌"
        lines.append(f"{i}. {ok} {h.get('case_number')} ({h.get('links_count', 0)})")
    await message.answer("\n".join(lines))


async def cmd_cancel(message: Message):
    ok = await queue_manager.cancel(message.from_user.id)
    await message.answer("Отменено" if ok else "Нет активной задачи")


async def admin_reinit(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("Локальный режим: reinit недоступен (драйвер создаётся на задачу)")


async def admin_health(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("Локальный режим: health = ok")


async def admin_set_backend(message: Message, command: CommandObject):
    if not is_admin(message.from_user.id):
        return
    await message.answer("Локальный режим: настройка BACKEND не требуется")


async def admin_diagnostics(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("Диагностика: Chrome/driver проверяются в момент задачи. Смотрите логи контейнера.")


async def admin_logs(message: Message):
    if not is_admin(message.from_user.id):
        return
    # Simple in-memory logging via loguru isn't persisted; notify
    await message.answer("Логи в контейнере. Используйте docker logs для выгрузки.")


async def cmd_backend(message: Message):
    await message.answer("Локальный режим парсинга включён")


async def on_callback(call: CallbackQuery):
    data = call.data or ""
    if data.startswith("status"):
        await cmd_status(call.message)
    elif data.startswith("cancel"):
        await cmd_cancel(call.message)
    elif data.startswith("mode"):
        await cmd_mode(call.message)
    await call.answer()


async def main() -> None:
    logger.info("🚀 Starting Telegram bot...")

    log_level = settings.LOG_LEVEL.upper()
    logger.remove()
    logger.add(lambda msg: print(msg, end=""), level=log_level)

    logger.info(f"📋 Log level set to: {log_level}")
    logger.debug(f"🤖 Bot token: {settings.TELEGRAM_BOT_TOKEN[:10]}...")
    logger.debug(f"👥 Admin IDs: {settings.ADMIN_IDS}")
    logger.debug(f"⚙️ Default mode: {settings.DEFAULT_MODE}")
    logger.debug(f"📊 Global limit: {settings.GLOBAL_DAILY_LIMIT}, Per user: {settings.PER_USER_DAILY_LIMIT}")

    logger.info("🔧 Initializing bot and dispatcher...")
    try:
        bot = Bot(token=settings.TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode=None))
        dp = Dispatcher(storage=MemoryStorage())
        logger.info("✅ Bot and dispatcher initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize bot: {e}")
        return

    logger.info("📝 Registering message handlers...")
    dp.message.register(cmd_start, Command("start"))
    dp.message.register(cmd_help, Command("help"))
    dp.message.register(cmd_mode, Command("mode"))
    dp.message.register(cmd_parse, Command("parse"))
    dp.message.register(cmd_status, Command("status"))
    dp.message.register(cmd_links, Command("links"))
    dp.message.register(cmd_history, Command("history"))
    dp.message.register(cmd_cancel, Command("cancel"))
    dp.message.register(cmd_backend, Command("backend"))

    # Register text message handler for case number input
    dp.message.register(process_case_number, StateFilter(UserStates.waiting_for_case_number))

    logger.info("✅ Basic commands registered")

    logger.info("👑 Registering admin commands...")
    dp.message.register(admin_reinit, Command("reinit"))
    dp.message.register(admin_health, Command("health"))
    dp.message.register(admin_set_backend, Command("set_backend"))
    dp.message.register(admin_diagnostics, Command("diagnostics"))
    dp.message.register(admin_logs, Command("logs"))
    logger.info("✅ Admin commands registered")

    logger.info("🎛️ Registering callback handlers...")
    dp.callback_query.register(on_callback, F.data)
    logger.info("✅ Callback handlers registered")

    allowed_updates = dp.resolve_used_update_types()
    logger.info(f"🔄 Allowed updates: {allowed_updates}")
    logger.info("🌐 Starting polling...")

    # Main polling loop with retry logic
    retry_count = 0
    max_retries = 10

    while retry_count < max_retries:
        try:
            logger.info(f"🔄 Starting polling (attempt {retry_count + 1}/{max_retries})...")
            await dp.start_polling(bot, allowed_updates=allowed_updates)
            break  # Success, exit loop

        except TelegramNetworkError as e:
            retry_count += 1
            logger.warning(f"🌐 Network error (attempt {retry_count}/{max_retries}): {e}")

            if retry_count < max_retries:
                wait_time = min(30 * retry_count, 300)  # Exponential backoff, max 5 minutes
                logger.info(f"⏳ Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
            else:
                logger.error("❌ Max retries exceeded. Giving up.")
                raise

        except Exception as e:
            logger.error(f"❌ Unexpected error during polling: {e}")
            # For unexpected errors, don't retry automatically
            raise


if __name__ == "__main__":
    asyncio.run(main())


