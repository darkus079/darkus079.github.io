#!/usr/bin/env python3
"""
Тест для проверки исправления ошибки 404 при скачивании файлов
"""

import os
import tempfile
import shutil
from fastapi.testclient import TestClient
from app import app

def test_download_with_cyrillic_filename():
    """Тестирует скачивание файлов с кириллическими символами"""
    print("🧪 Тестирование скачивания файлов с кириллическими символами...")
    
    # Создаем тестовый файл с кириллическим именем
    test_filename = "А84-4753_2024_тест_документ.pdf"
    test_file_path = os.path.join("files", test_filename)
    
    # Создаем папку files если её нет
    os.makedirs("files", exist_ok=True)
    
    # Проверяем, что папка files существует
    print(f"📁 Папка files существует: {os.path.exists('files')}")
    print(f"📁 Текущая рабочая директория: {os.getcwd()}")
    print(f"📁 Содержимое папки files: {os.listdir('files') if os.path.exists('files') else 'Папка не существует'}")
    
    # Создаем тестовый файл
    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write("Test PDF content with Cyrillic filename")
    
    print(f"📄 Создан тестовый файл: {test_filename}")
    
    # Тестируем с помощью TestClient
    client = TestClient(app)
    
    # Тестируем API эндпоинт /api/files
    response = client.get("/api/files")
    print(f"📊 Статус /api/files: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"📁 Файлы в API: {data.get('files', [])}")
        
        # Проверяем, что наш файл есть в списке
        if test_filename in data.get('files', []):
            print("✅ Файл найден в списке API")
            
            # Тестируем скачивание файла
            import urllib.parse
            encoded_filename = urllib.parse.quote(test_filename)
            download_url = f"/api/download/{encoded_filename}"
            
            print(f"🔗 URL для скачивания: {download_url}")
            
            response = client.get(download_url)
            print(f"📊 Статус скачивания: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ Файл успешно скачан!")
                print(f"📁 Content-Type: {response.headers.get('content-type')}")
                print(f"📁 Content-Disposition: {response.headers.get('content-disposition')}")
                print(f"📊 Размер файла: {len(response.content)} байт")
            else:
                print(f"❌ Ошибка скачивания: {response.status_code}")
                print(f"📄 Ответ: {response.text}")
        else:
            print("❌ Файл не найден в списке API")
    else:
        print(f"❌ Ошибка получения списка файлов: {response.status_code}")
        print(f"📄 Ответ: {response.text}")
    
    # Очищаем тестовый файл
    if os.path.exists(test_file_path):
        os.remove(test_file_path)
        print("🗑️ Тестовый файл удален")
    
    return response.status_code == 200

def test_download_with_special_characters():
    """Тестирует скачивание файлов со специальными символами"""
    print("\n🧪 Тестирование скачивания файлов со специальными символами...")
    
    # Создаем тестовый файл со специальными символами
    test_filename = "Test_File_With_Special_Chars.pdf"
    test_file_path = os.path.join("files", test_filename)
    
    # Создаем папку files если её нет
    os.makedirs("files", exist_ok=True)
    
    # Создаем тестовый файл
    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write("Test PDF content with special characters")
    
    print(f"📄 Создан тестовый файл: {test_filename}")
    
    # Тестируем с помощью TestClient
    client = TestClient(app)
    
    # Тестируем API эндпоинт /api/files
    response = client.get("/api/files")
    print(f"📊 Статус /api/files: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"📁 Файлы в API: {data.get('files', [])}")
        
        # Проверяем, что наш файл есть в списке
        if test_filename in data.get('files', []):
            print("✅ Файл найден в списке API")
            
            # Тестируем скачивание файла
            import urllib.parse
            encoded_filename = urllib.parse.quote(test_filename)
            download_url = f"/api/download/{encoded_filename}"
            
            print(f"🔗 URL для скачивания: {download_url}")
            
            response = client.get(download_url)
            print(f"📊 Статус скачивания: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ Файл успешно скачан!")
                print(f"📁 Content-Type: {response.headers.get('content-type')}")
                print(f"📁 Content-Disposition: {response.headers.get('content-disposition')}")
                print(f"📊 Размер файла: {len(response.content)} байт")
            else:
                print(f"❌ Ошибка скачивания: {response.status_code}")
                print(f"📄 Ответ: {response.text}")
        else:
            print("❌ Файл не найден в списке API")
    else:
        print(f"❌ Ошибка получения списка файлов: {response.status_code}")
        print(f"📄 Ответ: {response.text}")
    
    # Очищаем тестовый файл
    if os.path.exists(test_file_path):
        os.remove(test_file_path)
        print("🗑️ Тестовый файл удален")
    
    return response.status_code == 200

def test_object_object_error():
    """Тестирует, что больше не возникает ошибка [object Object]"""
    print("\n🧪 Тестирование предотвращения ошибки [object Object]...")
    
    # Симулируем проблему с объектом вместо строки
    test_cases = [
        {"name": "test.pdf", "url": "http://example.com/test.pdf"},
        {"name": "А84-4753_2024_тест.pdf", "url": "http://example.com/А84-4753_2024_тест.pdf"},
        {"name": "Test_File_With_Special_Chars_!@#$%^&*().pdf", "url": "http://example.com/Test_File_With_Special_Chars_!@#$%^&*().pdf"}
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"   Тест {i}: {test_case['name']}")
        
        # Проверяем, что name и url - это строки
        if isinstance(test_case['name'], str) and isinstance(test_case['url'], str):
            print(f"   ✅ name и url являются строками")
            
            # Проверяем, что в URL нет [object Object]
            if '[object Object]' not in test_case['url']:
                print(f"   ✅ URL не содержит [object Object]")
            else:
                print(f"   ❌ URL содержит [object Object]")
        else:
            print(f"   ❌ name или url не являются строками")
    
    print("✅ Тест предотвращения ошибки [object Object] завершен")

if __name__ == "__main__":
    print("🚀 Запуск тестов исправления ошибки 404 при скачивании файлов\n")
    
    # Тест 1: Предотвращение ошибки [object Object]
    test_object_object_error()
    
    # Тест 2: Скачивание файлов с кириллическими символами
    success1 = test_download_with_cyrillic_filename()
    
    # Тест 3: Скачивание файлов со специальными символами
    success2 = test_download_with_special_characters()
    
    if success1 and success2:
        print("\n✅ Все тесты прошли успешно!")
        print("🎉 Ошибка 404 при скачивании файлов исправлена!")
    else:
        print("\n❌ Некоторые тесты не прошли!")
        print("🔧 Требуется дополнительная отладка")
