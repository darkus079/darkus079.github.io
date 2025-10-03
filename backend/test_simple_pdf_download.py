#!/usr/bin/env python3
"""
Простой тест для проверки автоматического скачивания PDF
"""

import os
import time
import logging
from selenium_config import (
    create_standard_chrome_options, 
    get_downloads_directory,
    move_downloaded_files
)
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_simple_pdf_download():
    """Тестирует простое скачивание PDF"""
    
    # Создаем настройки Chrome
    options = create_standard_chrome_options()
    
    # Инициализируем драйвер
    try:
        driver_path = ChromeDriverManager().install()
        service = Service(driver_path)
        driver = webdriver.Chrome(service=service, options=options)
        logger.info("✅ Chrome драйвер инициализирован")
        
        # Тестируем с реальным PDF
        test_url = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
        logger.info(f"🧪 Тестирование с PDF: {test_url}")
        
        # Переходим по ссылке
        driver.get(test_url)
        time.sleep(5)
        
        current_url = driver.current_url
        logger.info(f"📍 Текущий URL: {current_url}")
        
        # Проверяем, что PDF не открылся в браузере
        if current_url == test_url:
            logger.info("✅ PDF не открылся в браузере (должен был скачаться)")
        else:
            logger.warning(f"⚠️ PDF открылся в браузере: {current_url}")
        
        # Перемещаем скачанные файлы
        downloads_dir = get_downloads_directory()
        target_dir = os.path.join(os.getcwd(), "files")
        
        logger.info("📁 Перемещение скачанных файлов...")
        moved_files = move_downloaded_files(downloads_dir, target_dir, "TEST_CASE")
        
        if moved_files:
            logger.info("✅ Файлы успешно перемещены!")
            for file in moved_files:
                file_size = os.path.getsize(file)
                logger.info(f"   📄 {os.path.basename(file)} ({file_size} байт)")
        else:
            logger.warning("⚠️ Файлы не найдены для перемещения")
        
        # Закрываем драйвер
        driver.quit()
        logger.info("✅ Тест завершен")
        
    except Exception as e:
        logger.error(f"❌ Ошибка тестирования: {e}")

if __name__ == "__main__":
    test_simple_pdf_download()
