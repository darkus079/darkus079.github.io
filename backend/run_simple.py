#!/usr/bin/env python3
"""
Простой запуск backend сервиса
"""

import os
import sys
import uvicorn

# Добавляем текущую папку в путь
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Импортируем приложение
from backend_service import app

if __name__ == "__main__":
    print("🚀 Простой запуск backend сервиса")
    print("📱 API: http://0.0.0.0:8000")
    print("📋 Docs: http://0.0.0.0:8000/docs")
    print("⏹️  Ctrl+C для остановки")
    
    try:
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            reload=False,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\n👋 Остановка сервиса...")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)
