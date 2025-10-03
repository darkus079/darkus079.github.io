#!/usr/bin/env python3
"""
Тестовый скрипт для проверки настроек автоматического скачивания PDF
"""

import os
import time
import logging
from selenium_config import (
    create_standard_chrome_options, 
    setup_pdf_download_script,
    test_pdf_download_setup
)
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_pdf_download():
    """Тестирует настройки автоматического скачивания PDF"""
    
    # Создаем папку для скачивания
    downloads_dir = os.path.join(os.getcwd(), "test_downloads")
    os.makedirs(downloads_dir, exist_ok=True)
    logger.info(f"📁 Папка для скачивания: {downloads_dir}")
    
    # Создаем настройки Chrome
    options = create_standard_chrome_options(downloads_dir)
    
    # Инициализируем драйвер
    try:
        driver_path = ChromeDriverManager().install()
        service = Service(driver_path)
        driver = webdriver.Chrome(service=service, options=options)
        logger.info("✅ Chrome драйвер инициализирован")
        
        # Настраиваем JavaScript для принудительного скачивания PDF
        setup_pdf_download_script(driver)
        
        # Тестируем настройки
        test_pdf_download_setup(driver)
        
        # Тестируем с реальным PDF с kad.arbitr.ru
        logger.info("🧪 Тестирование с реальным PDF...")
        test_url = "https://kad.arbitr.ru/Document/Pdf/12345678-1234-1234-1234-123456789012/12345678-1234-1234-1234-123456789012/12345678-1234-1234-1234-123456789012.pdf"
        
        try:
            driver.get(test_url)
            time.sleep(5)
            
            current_url = driver.current_url
            logger.info(f"📍 Текущий URL: {current_url}")
            
            # Проверяем, что PDF не открылся в браузере
            if current_url == test_url:
                logger.info("✅ PDF не открылся в браузере (должен был скачаться)")
            else:
                logger.warning(f"⚠️ PDF открылся в браузере: {current_url}")
                
        except Exception as e:
            logger.warning(f"⚠️ Ошибка тестирования реального PDF: {e}")
        
        # Проверяем скачанные файлы
        downloaded_files = os.listdir(downloads_dir)
        logger.info(f"📄 Скачанные файлы: {downloaded_files}")
        
        if downloaded_files:
            logger.info("✅ Файлы успешно скачаны!")
            for file in downloaded_files:
                file_path = os.path.join(downloads_dir, file)
                file_size = os.path.getsize(file_path)
                logger.info(f"   📄 {file} ({file_size} байт)")
        else:
            logger.warning("⚠️ Файлы не скачались")
        
        # Закрываем драйвер
        driver.quit()
        logger.info("✅ Тест завершен")
        
    except Exception as e:
        logger.error(f"❌ Ошибка тестирования: {e}")

if __name__ == "__main__":
    test_pdf_download()
