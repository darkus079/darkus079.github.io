#!/usr/bin/env python3
"""
Скрипт тестирования интеграции frontend и backend
"""

import requests
import time
import json
import sys
from datetime import datetime

# Конфигурация
BACKEND_URL = "http://localhost:8000"
TEST_CASE_NUMBER = "А84-12036/2023"  # Тестовый номер дела

def test_backend_health():
    """Тест доступности backend"""
    print("🔍 Тест 1: Проверка доступности backend...")
    
    try:
        response = requests.get(f"{BACKEND_URL}/api/health", timeout=5)
        
        if response.status_code == 200:
            health = response.json()
            print(f"✅ Backend доступен: {health['status']}")
            print(f"   Парсер доступен: {health['parser_available']}")
            print(f"   Размер очереди: {health['queue_size']}")
            return True
        else:
            print(f"❌ Backend недоступен: HTTP {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка подключения к backend: {e}")
        return False

def test_api_endpoints():
    """Тест API эндпоинтов"""
    print("\n🔍 Тест 2: Проверка API эндпоинтов...")
    
    endpoints = [
        ("GET", "/api/status", "Статус парсинга"),
        ("GET", "/api/files", "Список файлов"),
        ("GET", "/api/history", "История парсинга"),
    ]
    
    success_count = 0
    
    for method, endpoint, description in endpoints:
        try:
            if method == "GET":
                response = requests.get(f"{BACKEND_URL}{endpoint}", timeout=5)
            else:
                response = requests.post(f"{BACKEND_URL}{endpoint}", timeout=5)
            
            if response.status_code == 200:
                print(f"✅ {description}: OK")
                success_count += 1
            else:
                print(f"❌ {description}: HTTP {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"❌ {description}: {e}")
    
    print(f"📊 Результат: {success_count}/{len(endpoints)} эндпоинтов работают")
    return success_count == len(endpoints)

def test_parsing_workflow():
    """Тест полного цикла парсинга"""
    print(f"\n🔍 Тест 3: Тестирование парсинга дела {TEST_CASE_NUMBER}...")
    
    try:
        # 1. Отправляем запрос на парсинг
        print("   📡 Отправка запроса на парсинг...")
        parse_response = requests.post(
            f"{BACKEND_URL}/api/parse",
            json={"case_number": TEST_CASE_NUMBER},
            timeout=10
        )
        
        if parse_response.status_code != 200:
            print(f"   ❌ Ошибка отправки запроса: HTTP {parse_response.status_code}")
            return False
        
        parse_data = parse_response.json()
        print(f"   ✅ Запрос принят: {parse_data['message']}")
        
        # 2. Мониторим статус парсинга
        print("   📊 Мониторинг статуса парсинга...")
        max_wait_time = 300  # 5 минут
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            status_response = requests.get(f"{BACKEND_URL}/api/status", timeout=5)
            
            if status_response.status_code == 200:
                status = status_response.json()
                print(f"   📊 Статус: {status['progress']}")
                
                if not status['is_parsing']:
                    print(f"   ✅ Парсинг завершен")
                    break
            else:
                print(f"   ❌ Ошибка получения статуса: HTTP {status_response.status_code}")
                return False
            
            time.sleep(2)
        else:
            print("   ⏰ Превышено время ожидания")
            return False
        
        # 3. Проверяем список файлов
        print("   📁 Проверка списка файлов...")
        files_response = requests.get(f"{BACKEND_URL}/api/files", timeout=5)
        
        if files_response.status_code == 200:
            files_data = files_response.json()
            files_count = len(files_data['files'])
            print(f"   ✅ Найдено файлов: {files_count}")
            
            if files_count > 0:
                print("   📄 Список файлов:")
                for file_info in files_data['files'][:5]:  # Показываем первые 5
                    print(f"      - {file_info['name']} ({file_info['size']} байт)")
                
                if files_count > 5:
                    print(f"      ... и еще {files_count - 5} файлов")
                
                return True
            else:
                print("   ⚠️ Файлы не найдены")
                return False
        else:
            print(f"   ❌ Ошибка получения списка файлов: HTTP {files_response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Ошибка тестирования парсинга: {e}")
        return False

def test_cors_headers():
    """Тест CORS заголовков"""
    print("\n🔍 Тест 4: Проверка CORS заголовков...")
    
    try:
        # Отправляем OPTIONS запрос для проверки CORS
        response = requests.options(
            f"{BACKEND_URL}/api/parse",
            headers={
                "Origin": "https://darkus079.github.io",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
            },
            timeout=5
        )
        
        if response.status_code == 200:
            cors_headers = {
                "Access-Control-Allow-Origin": response.headers.get("Access-Control-Allow-Origin"),
                "Access-Control-Allow-Methods": response.headers.get("Access-Control-Allow-Methods"),
                "Access-Control-Allow-Headers": response.headers.get("Access-Control-Allow-Headers"),
            }
            
            print("   ✅ CORS заголовки:")
            for header, value in cors_headers.items():
                if value:
                    print(f"      {header}: {value}")
                else:
                    print(f"      ❌ {header}: отсутствует")
            
            return all(cors_headers.values())
        else:
            print(f"   ❌ Ошибка CORS: HTTP {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Ошибка тестирования CORS: {e}")
        return False

def test_file_download():
    """Тест скачивания файла"""
    print("\n🔍 Тест 5: Тестирование скачивания файла...")
    
    try:
        # Получаем список файлов
        files_response = requests.get(f"{BACKEND_URL}/api/files", timeout=5)
        
        if files_response.status_code != 200:
            print("   ❌ Не удалось получить список файлов")
            return False
        
        files_data = files_response.json()
        
        if not files_data['files']:
            print("   ⚠️ Нет файлов для тестирования скачивания")
            return True
        
        # Пытаемся скачать первый файл
        first_file = files_data['files'][0]
        filename = first_file['name']
        
        print(f"   📥 Скачивание файла: {filename}")
        
        download_response = requests.get(
            f"{BACKEND_URL}/api/download/{filename}",
            timeout=10
        )
        
        if download_response.status_code == 200:
            content_length = len(download_response.content)
            print(f"   ✅ Файл скачан: {content_length} байт")
            return True
        else:
            print(f"   ❌ Ошибка скачивания: HTTP {download_response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Ошибка тестирования скачивания: {e}")
        return False

def main():
    """Основная функция тестирования"""
    print("=" * 60)
    print("🧪 ТЕСТИРОВАНИЕ ИНТЕГРАЦИИ FRONTEND И BACKEND")
    print("=" * 60)
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Время тестирования: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    tests = [
        ("Доступность backend", test_backend_health),
        ("API эндпоинты", test_api_endpoints),
        ("CORS заголовки", test_cors_headers),
        ("Парсинг дела", test_parsing_workflow),
        ("Скачивание файла", test_file_download),
    ]
    
    passed_tests = 0
    total_tests = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed_tests += 1
        except Exception as e:
            print(f"❌ Критическая ошибка в тесте '{test_name}': {e}")
    
    print("\n" + "=" * 60)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    print("=" * 60)
    print(f"Пройдено тестов: {passed_tests}/{total_tests}")
    
    if passed_tests == total_tests:
        print("✅ ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        print("🎉 Интеграция frontend и backend работает корректно")
        return True
    else:
        print("❌ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ")
        print("🔧 Проверьте настройки и логи backend сервиса")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⏹️  Тестирование прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        sys.exit(1)
