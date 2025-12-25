#!/usr/bin/env python3
"""
Скрипт для запуска Kafka Worker
"""

import asyncio
import logging
import sys
import os

# Настройка путей
project_root = os.path.dirname(os.path.dirname(__file__))
tg_bot_path = os.path.dirname(__file__)
src_path = os.path.join(tg_bot_path, 'src')
sys.path.insert(0, project_root)
sys.path.insert(0, tg_bot_path)
sys.path.insert(0, src_path)
backend_path = os.path.join(project_root, 'backend')
sys.path.insert(0, backend_path)

from tg_bot.src.worker import ParsingWorker

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger = logging.getLogger(__name__)
    
    # Создаем worker
    worker = ParsingWorker("worker-1")
    
    try:
        logger.info("👷 Запуск Kafka Worker...")
        await worker.start()
    except KeyboardInterrupt:
        logger.info("🛑 Остановка worker по запросу пользователя...")
    except Exception as e:
        logger.error(f"❌ Ошибка worker: {e}")
    finally:
        await worker.stop()
        logger.info("👋 Worker завершил работу")

if __name__ == "__main__":
    asyncio.run(main())