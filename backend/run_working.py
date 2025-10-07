#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Рабочий запуск backend сервиса с исправлениями
"""

import os
import sys
import signal
import uvicorn
import threading
import time

# Добавляем текущую папку в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Импортируем приложение
from backend_service import app, shutdown_event, parser

def signal_handler(signum, frame):
    """Обработчик сигналов для корректного завершения"""
    print(f"\n🛑 Получен сигнал {signum}, завершение работы...")
    shutdown_event.set()
    
    # Закрываем парсер если он есть
    if parser:
        try:
            parser.close()
        except:
            pass
    
    print("✅ Backend сервис остановлен")
    sys.exit(0)

def check_port(port):
    """Проверка доступности порта"""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('127.0.0.1', port))
            return True
    except OSError:
        return False

def kill_process_on_port(port):
    """Завершение процесса на порту"""
    try:
        if sys.platform == "win32":
            # Windows
            import subprocess
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
    except Exception as e:
        print(f"⚠️ Не удалось завершить процесс на порту {port}: {e}")

if __name__ == "__main__":
    # Настройка обработчиков сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Проверяем порт
    port = 8000
    if not check_port(port):
        print(f"⚠️ Порт {port} занят, пытаемся освободить...")
        kill_process_on_port(port)
        time.sleep(2)
        
        if not check_port(port):
            print(f"❌ Порт {port} все еще занят")
            print("   Попробуйте:")
            print("   1. Закрыть другие приложения")
            print("   2. Перезагрузить компьютер")
            sys.exit(1)
    
    print("🚀 Запуск backend сервиса парсера kad.arbitr.ru")
    print("📱 API: http://0.0.0.0:8000")
    print("📋 Docs: http://0.0.0.0:8000/docs")
    print("⏹️  Ctrl+C для остановки")
    
    try:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            reload=False,
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        print("\n👋 Остановка сервиса...")
        signal_handler(signal.SIGINT, None)
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)
