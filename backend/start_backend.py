#!/usr/bin/env python3
"""
Скрипт запуска backend сервиса парсера kad.arbitr.ru
"""

import os
import sys
import subprocess
import time
import webbrowser
import socket
import signal
import threading
from pathlib import Path

# Глобальная переменная для отслеживания состояния сервера
server_running = False
server_process = None

def signal_handler(signum, frame):
    """Обработчик сигналов для корректного завершения"""
    global server_running, server_process
    
    print(f"\n🛑 Получен сигнал {signum} (Ctrl+C), завершение работы...")
    print("⏹️  Остановка backend сервиса...")
    print("📝 Завершение работы парсера...")
    
    # Устанавливаем флаг остановки
    server_running = False
    
    # Если есть процесс сервера, завершаем его
    if server_process:
        try:
            server_process.terminate()
            print("✅ Процесс сервера завершен")
        except:
            pass
    
    print("✅ Backend сервис остановлен")
    print("👋 До свидания!")
    sys.exit(0)

def check_port_available(port):
    """Проверка доступности порта"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', port))
            return True
    except OSError:
        return False

def kill_process_on_port(port):
    """Завершение процесса на порту"""
    try:
        if sys.platform == "win32":
            # Windows
            result = subprocess.run(
                f'netstat -ano | findstr :{port}',
                shell=True,
                capture_output=True,
                text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if f':{port}' in line and 'LISTENING' in line:
                        parts = line.split()
                        if len(parts) >= 5:
                            pid = parts[-1]
                            subprocess.run(f'taskkill /F /PID {pid}', shell=True)
                            print(f"✅ Завершен процесс {pid} на порту {port}")
        else:
            # Linux/Mac
            result = subprocess.run(
                f'lsof -ti:{port}',
                shell=True,
                capture_output=True,
                text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                pid = result.stdout.strip()
                subprocess.run(f'kill -9 {pid}', shell=True)
                print(f"✅ Завершен процесс {pid} на порту {port}")
    except Exception as e:
        print(f"⚠️ Не удалось завершить процесс на порту {port}: {e}")

def check_python_version():
    """Проверка версии Python"""
    if sys.version_info < (3, 8):
        print("❌ Требуется Python 3.8 или выше")
        print(f"   Текущая версия: {sys.version}")
        return False
    print(f"✅ Python версия: {sys.version.split()[0]}")
    return True

def check_dependencies():
    """Проверка установленных зависимостей"""
    print("🔍 Проверка зависимостей...")
    
    required_packages = [
        'fastapi',
        'uvicorn',
        'selenium',
        'requests',
        'bs4'  # beautifulsoup4 импортируется как bs4
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - не установлен")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n📦 Установка недостающих пакетов: {', '.join(missing_packages)}")
        try:
            subprocess.check_call([
                sys.executable, '-m', 'pip', 'install', 
                '-r', 'requirements.txt', '--upgrade'
            ])
            print("✅ Зависимости установлены")
        except subprocess.CalledProcessError as e:
            print(f"❌ Ошибка установки зависимостей: {e}")
            return False
    
    return True

def check_chrome():
    """Проверка наличия Chrome/Chromium"""
    print("🔍 Проверка Chrome/Chromium...")
    
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium-browser",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    ]
    
    for path in chrome_paths:
        if os.path.exists(path):
            print(f"✅ Chrome найден: {path}")
            return True
    
    print("⚠️ Chrome не найден в стандартных путях")
    print("   Убедитесь, что Chrome установлен")
    return True  # Не блокируем запуск

def create_directories():
    """Создание необходимых директорий"""
    print("📁 Создание директорий...")
    
    directories = ['files', 'templates', 'logs']
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✅ {directory}/")
    
    return True

def start_backend():
    """Запуск backend сервиса"""
    global server_running, server_process
    
    print("🚀 Запуск backend сервиса...")
    
    # Настройка обработчиков сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Проверяем доступность порта
    port = 8000
    if not check_port_available(port):
        print(f"⚠️ Порт {port} занят, пытаемся освободить...")
        kill_process_on_port(port)
        time.sleep(2)
        
        if not check_port_available(port):
            print(f"❌ Порт {port} все еще занят")
            print("   Попробуйте:")
            print("   1. Закрыть другие приложения")
            print("   2. Перезагрузить компьютер")
            print("   3. Изменить порт в коде")
            return False
    
    try:
        # Импортируем и запускаем сервис
        from backend_service import app
        import uvicorn
        
        print("✅ Backend сервис запущен")
        print("📱 API доступен по адресу: http://127.0.0.1:8000")
        print("📋 Документация API: http://127.0.0.1:8000/docs")
        print("⏹️  Для остановки нажмите Ctrl+C")
        
        # Устанавливаем флаг запуска
        server_running = True
        
        # Запускаем сервер в отдельном потоке
        def run_server():
            global server_process
            try:
                uvicorn.run(
                    app,
                    host="127.0.0.1",
                    port=8000,
                    reload=False,
                    log_level="info",
                    access_log=True
                )
            except Exception as e:
                if server_running:  # Только если не остановлен принудительно
                    print(f"❌ Ошибка сервера: {e}")
        
        # Запускаем сервер
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        
        # Ждем завершения или прерывания
        try:
            while server_running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            signal_handler(signal.SIGINT, None)
        
    except Exception as e:
        print(f"❌ Ошибка запуска backend сервиса: {e}")
        return False
    
    return True

def main():
    """Основная функция"""
    print("=" * 60)
    print("🚀 ПАРСЕР KAD.ARBITR.RU - BACKEND СЕРВИС")
    print("=" * 60)
    
    # Проверяем, что мы в правильной директории
    if not os.path.exists('backend_service.py'):
        print("❌ Файл backend_service.py не найден")
        print("   Запустите скрипт из папки backend/")
        return False
    
    # Выполняем проверки
    if not check_python_version():
        return False
    
    if not check_dependencies():
        return False
    
    check_chrome()
    
    if not create_directories():
        return False
    
    print("\n" + "=" * 60)
    print("✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ")
    print("=" * 60)
    
    # Запускаем backend
    return start_backend()

if __name__ == "__main__":
    # Настройка обработчиков сигналов на уровне main
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        success = main()
        if not success:
            sys.exit(1)
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        sys.exit(1)