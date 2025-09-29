#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Быстрый тест backend сервиса
"""

import requests
import time
import sys
import os

# Устанавливаем кодировку UTF-8
os.environ['PYTHONIOENCODING'] = 'utf-8'

def test_backend():
    """Быстрый тест доступности backend"""
    print("Тестирование backend сервиса...")
    
    try:
        # Тест health check
        response = requests.get("http://127.0.0.1:8000/api/health", timeout=5)
        
        if response.status_code == 200:
            health = response.json()
            print("Backend доступен!")
            print(f"   Статус: {health['status']}")
            print(f"   Парсер: {health['parser_available']}")
            print(f"   Очередь: {health['queue_size']}")
            return True
        else:
            print(f"Backend недоступен: HTTP {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("Не удается подключиться к backend")
        print("   Убедитесь, что сервис запущен на 127.0.0.1:8000")
        return False
    except Exception as e:
        print(f"Ошибка: {e}")
        return False

def test_api_endpoints():
    """Тест основных API эндпоинтов"""
    print("\nТестирование API эндпоинтов...")
    
    endpoints = [
        ("GET", "/api/status", "Статус"),
        ("GET", "/api/files", "Файлы"),
        ("GET", "/api/history", "История"),
    ]
    
    for method, endpoint, name in endpoints:
        try:
            response = requests.get(f"http://127.0.0.1:8000{endpoint}", timeout=5)
            if response.status_code == 200:
                print(f"{name}: OK")
            else:
                print(f"{name}: HTTP {response.status_code}")
        except Exception as e:
            print(f"{name}: {e}")

if __name__ == "__main__":
    print("=" * 50)
    print("БЫСТРЫЙ ТЕСТ BACKEND СЕРВИСА")
    print("=" * 50)
    
    if test_backend():
        test_api_endpoints()
        print("\nBackend работает корректно!")
    else:
        print("\nBackend недоступен!")
        print("\nРешения:")
        print("1. Запустите backend: cd backend && python run_working.py")
        print("2. Проверьте, что порт 8000 свободен")
        print("3. Проверьте логи в backend.log")
        sys.exit(1)
