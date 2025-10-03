#!/usr/bin/env python3
"""
Тест для проверки исправлений
"""

import os
import logging
from parser_simplified import KadArbitrParser

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_get_downloaded_files():
    """Тестирует метод get_downloaded_files"""
    logger.info("🧪 Тестирование метода get_downloaded_files...")
    
    # Создаем парсер
    parser = KadArbitrParser()
    
    # Получаем список файлов
    files = parser.get_downloaded_files()
    
    logger.info(f"📁 Найдено файлов: {len(files)}")
    
    if files:
        for file_path in files:
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path)
                filename = os.path.basename(file_path)
                logger.info(f"   ✅ {filename} ({file_size} байт)")
            else:
                logger.warning(f"   ❌ Файл не существует: {file_path}")
    else:
        logger.info("   📁 Файлы не найдены")
    
    logger.info("✅ Тест get_downloaded_files завершен")

def test_file_download_simulation():
    """Симулирует процесс скачивания файлов"""
    logger.info("🧪 Тестирование симуляции скачивания...")
    
    # Создаем тестовый файл
    test_file = os.path.join("files", "test_document.pdf")
    os.makedirs("files", exist_ok=True)
    
    with open(test_file, "w") as f:
        f.write("Test PDF content")
    
    logger.info(f"📄 Создан тестовый файл: {test_file}")
    
    # Тестируем парсер
    parser = KadArbitrParser()
    files = parser.get_downloaded_files()
    
    logger.info(f"📁 Парсер нашел файлов: {len(files)}")
    
    # Проверяем, что файл найден
    test_found = any("test_document.pdf" in file_path for file_path in files)
    
    if test_found:
        logger.info("✅ Тестовый файл найден парсером")
    else:
        logger.warning("❌ Тестовый файл не найден парсером")
    
    # Очищаем тестовый файл
    if os.path.exists(test_file):
        os.remove(test_file)
        logger.info("🗑️ Тестовый файл удален")
    
    logger.info("✅ Тест симуляции завершен")

if __name__ == "__main__":
    test_get_downloaded_files()
    test_file_download_simulation()
