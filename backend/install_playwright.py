"""
Скрипт для установки Playwright и браузеров
"""

import subprocess
import sys
import logging

logger = logging.getLogger(__name__)

def install_playwright():
    """Устанавливает Playwright и браузеры"""
    try:
        logger.info("🎭 Установка Playwright...")
        
        # Устанавливаем Playwright
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", "playwright>=1.40.0"
        ])
        
        logger.info("✅ Playwright установлен")
        
        # Устанавливаем браузеры
        logger.info("🌐 Установка браузеров Playwright...")
        
        subprocess.check_call([
            sys.executable, "-m", "playwright", "install", "chromium"
        ])
        
        logger.info("✅ Браузеры Playwright установлены")
        
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Ошибка установки Playwright: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Неожиданная ошибка: {e}")
        return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    if install_playwright():
        print("✅ Playwright успешно установлен!")
    else:
        print("❌ Ошибка установки Playwright")
        sys.exit(1)
