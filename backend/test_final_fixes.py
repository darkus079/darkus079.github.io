#!/usr/bin/env python3
"""
Тест для проверки финальных исправлений
"""

import os
import logging
from parser_simplified import KadArbitrParser

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_api_endpoints():
    """Тестирует API эндпоинты"""
    logger.info("🧪 Тестирование API эндпоинтов...")
    
    # Создаем тестовый файл
    test_file = os.path.join("files", "test_api_document.pdf")
    os.makedirs("files", exist_ok=True)
    
    with open(test_file, "w") as f:
        f.write("Test PDF content for API")
    
    logger.info(f"📄 Создан тестовый файл: {test_file}")
    
    # Тестируем парсер
    parser = KadArbitrParser()
    files = parser.get_downloaded_files()
    
    logger.info(f"📁 Парсер нашел файлов: {len(files)}")
    
    # Проверяем, что файл найден
    test_found = any("test_api_document.pdf" in file_path for file_path in files)
    
    if test_found:
        logger.info("✅ Тестовый файл найден парсером")
        
        # Проверяем, что файл существует
        for file_path in files:
            if "test_api_document.pdf" in file_path:
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path)
                    logger.info(f"   ✅ Файл существует: {file_path} ({file_size} байт)")
                else:
                    logger.warning(f"   ❌ Файл не существует: {file_path}")
    else:
        logger.warning("❌ Тестовый файл не найден парсером")
    
    # Очищаем тестовый файл
    if os.path.exists(test_file):
        os.remove(test_file)
        logger.info("🗑️ Тестовый файл удален")
    
    logger.info("✅ Тест API эндпоинтов завершен")

def test_file_download_simulation():
    """Симулирует процесс скачивания файлов с новой логикой вкладок"""
    logger.info("🧪 Тестирование симуляции скачивания с вкладками...")
    
    # Создаем несколько тестовых файлов
    test_files = [
        "test_document_1.pdf",
        "test_document_2.pdf",
        "test_document_3.pdf"
    ]
    
    os.makedirs("files", exist_ok=True)
    
    for filename in test_files:
        file_path = os.path.join("files", filename)
        with open(file_path, "w") as f:
            f.write(f"Test PDF content for {filename}")
        logger.info(f"📄 Создан тестовый файл: {filename}")
    
    # Тестируем парсер
    parser = KadArbitrParser()
    files = parser.get_downloaded_files()
    
    logger.info(f"📁 Парсер нашел файлов: {len(files)}")
    
    # Проверяем, что все файлы найдены
    found_files = []
    for file_path in files:
        filename = os.path.basename(file_path)
        if filename in test_files:
            found_files.append(filename)
            logger.info(f"   ✅ Найден: {filename}")
    
    if len(found_files) == len(test_files):
        logger.info("✅ Все тестовые файлы найдены")
    else:
        logger.warning(f"⚠️ Найдено {len(found_files)} из {len(test_files)} файлов")
    
    # Очищаем тестовые файлы
    for filename in test_files:
        file_path = os.path.join("files", filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"🗑️ Удален: {filename}")
    
    logger.info("✅ Тест симуляции скачивания завершен")

if __name__ == "__main__":
    test_api_endpoints()
    test_file_download_simulation()
