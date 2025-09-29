#!/usr/bin/env python3
"""
Скрипт запуска парсера kad.arbitr.ru с веб-интерфейсом
"""

import os
import sys
import subprocess
import webbrowser
import time
from pathlib import Path

def check_requirements():
    """Проверяет наличие необходимых зависимостей"""
    print("🔍 Проверка зависимостей...")
    
    try:
        import fastapi
        import uvicorn
        import selenium
        print("✅ Основные зависимости найдены")
    except ImportError as e:
        print(f"❌ Отсутствуют зависимости: {e}")
        print("📦 Установите зависимости: pip install -r requirements.txt")
        return False
    
    try:
        import undetected_chromedriver
        print("✅ undetected-chromedriver найден")
    except ImportError:
        print("⚠️  undetected-chromedriver не найден")
        print("💡 Рекомендуется установить: pip install undetected-chromedriver")
        print("⚡ Будет использован обычный Chrome WebDriver")
    
    return True

def create_directories():
    """Создает необходимые папки"""
    print("📁 Создание необходимых папок...")
    
    directories = ["files", "templates"]
    for dir_name in directories:
        Path(dir_name).mkdir(exist_ok=True)
    
    print("✅ Папки созданы")

def check_chrome():
    """Проверяет наличие Google Chrome"""
    print("🌐 Проверка Google Chrome...")
    
    # Попробуем импортировать selenium и создать драйвер
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        # Попробуем создать драйвер (не инициализируем полностью)
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            ChromeDriverManager().install()
            print("✅ Google Chrome и ChromeDriver доступны")
            return True
        except Exception as e:
            print(f"⚠️  Проблема с Chrome: {e}")
            print("💡 Убедитесь что Google Chrome установлен")
            return True  # Продолжаем запуск, ошибка может быть обработана в коде
            
    except Exception as e:
        print(f"❌ Ошибка проверки Chrome: {e}")
        return False

def main():
    """Основная функция запуска"""
    print("🚀 Запуск парсера kad.arbitr.ru")
    print("=" * 50)
    
    # Проверки
    if not check_requirements():
        input("\nНажмите Enter для выхода...")
        return
    
    create_directories()
    check_chrome()
    
    print("\n" + "=" * 50)
    print("🌟 Запуск веб-сервера...")
    print("📱 Веб-интерфейс: http://localhost:8000")
    print("⏹️  Для остановки: Ctrl+C")
    print("=" * 50)
    
    # Небольшая задержка
    time.sleep(2)
    
    try:
        # Открываем браузер автоматически через 3 секунды
        def open_browser():
            time.sleep(3)
            try:
                webbrowser.open("http://localhost:8000")
                print("🌐 Браузер открыт автоматически")
            except Exception:
                print("💡 Откройте браузер вручную: http://localhost:8000")
        
        import threading
        browser_thread = threading.Thread(target=open_browser, daemon=True)
        browser_thread.start()
        
        # Запускаем FastAPI приложение
        os.system("python app.py")
        
    except KeyboardInterrupt:
        print("\n\n🛑 Получен сигнал завершения")
        print("👋 Парсер остановлен")
    except Exception as e:
        print(f"\n❌ Ошибка запуска: {e}")
        print("💡 Попробуйте запустить: python app.py")
    
    input("\nНажмите Enter для выхода...")

if __name__ == "__main__":
    main()
