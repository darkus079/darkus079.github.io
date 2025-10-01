"""
Тестовый скрипт для проверки новых стратегий PDF извлечения
"""

import os
import sys
import logging
from pathlib import Path

# Добавляем текущую директорию в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from advanced_pdf_strategies import AdvancedPDFExtractor, ControlledHTTPStrategy
from playwright_integration import PlaywrightPDFExtractorSync

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_controlled_http_strategy():
    """Тестирует стратегию управляемых HTTP запросов"""
    logger.info("🧪 Тестирование стратегии управляемых HTTP запросов")
    
    try:
        # Создаем тестовую папку
        test_dir = "test_files"
        os.makedirs(test_dir, exist_ok=True)
        
        # Создаем экстрактор
        strategy = ControlledHTTPStrategy(test_dir)
        
        # Тестовые данные
        case_url = "https://kad.arbitr.ru/Card/12345"
        html_content = """
        <html>
            <body>
                <a href="/Document/Pdf/12345">Скачать PDF</a>
                <a href="https://kad.arbitr.ru/Document/GetPdf/12345">Скачать PDF 2</a>
            </body>
        </html>
        """
        cookies = [
            {"name": "session_id", "value": "test123", "domain": "kad.arbitr.ru", "path": "/"},
            {"name": "auth_token", "value": "token456", "domain": "kad.arbitr.ru", "path": "/"}
        ]
        
        # Тестируем поиск URL
        pdf_urls = strategy.find_pdf_urls_in_html(html_content, case_url)
        logger.info(f"📄 Найдено PDF URL: {pdf_urls}")
        
        # Тестируем установку cookies
        strategy.set_cookies_from_browser(cookies)
        
        logger.info("✅ Тест стратегии HTTP запросов завершен")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка тестирования HTTP стратегии: {e}")
        return False

def test_playwright_strategy():
    """Тестирует стратегию перехвата сетевого трафика"""
    logger.info("🧪 Тестирование стратегии перехвата сетевого трафика")
    
    try:
        # Создаем тестовую папку
        test_dir = "test_files"
        os.makedirs(test_dir, exist_ok=True)
        
        # Создаем экстрактор
        extractor = PlaywrightPDFExtractorSync(test_dir)
        
        # Тестовый URL (не реальный, для проверки инициализации)
        test_url = "https://kad.arbitr.ru/Card/12345"
        
        logger.info("✅ Тест стратегии перехвата завершен (только инициализация)")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка тестирования стратегии перехвата: {e}")
        return False

def test_advanced_extractor():
    """Тестирует комбинированный экстрактор"""
    logger.info("🧪 Тестирование комбинированного экстрактора")
    
    try:
        # Создаем тестовую папку
        test_dir = "test_files"
        os.makedirs(test_dir, exist_ok=True)
        
        # Создаем экстрактор
        extractor = AdvancedPDFExtractor(test_dir)
        
        # Тестовые данные
        case_url = "https://kad.arbitr.ru/Card/12345"
        html_content = """
        <html>
            <body>
                <a href="/Document/Pdf/12345">Скачать PDF</a>
            </body>
        </html>
        """
        cookies = [
            {"name": "session_id", "value": "test123", "domain": "kad.arbitr.ru", "path": "/"}
        ]
        
        # Тестируем HTTP стратегию
        http_files = extractor.extract_with_controlled_http(case_url, html_content, cookies)
        logger.info(f"📄 HTTP стратегия: {len(http_files)} файлов")
        
        logger.info("✅ Тест комбинированного экстрактора завершен")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка тестирования комбинированного экстрактора: {e}")
        return False

def main():
    """Основная функция тестирования"""
    logger.info("🚀 Запуск тестов новых стратегий PDF извлечения")
    
    tests = [
        ("Управляемые HTTP запросы", test_controlled_http_strategy),
        ("Перехват сетевого трафика", test_playwright_strategy),
        ("Комбинированный экстрактор", test_advanced_extractor)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Тест: {test_name}")
        logger.info(f"{'='*50}")
        
        if test_func():
            passed += 1
            logger.info(f"✅ {test_name} - ПРОЙДЕН")
        else:
            logger.error(f"❌ {test_name} - ПРОВАЛЕН")
    
    logger.info(f"\n{'='*50}")
    logger.info(f"РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ: {passed}/{total} тестов пройдено")
    logger.info(f"{'='*50}")
    
    if passed == total:
        logger.info("🎉 Все тесты пройдены успешно!")
        return True
    else:
        logger.error("❌ Некоторые тесты провалены")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
