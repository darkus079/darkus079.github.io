#!/usr/bin/env python3
"""
Прямое тестирование API без запуска сервера
"""

import os
import tempfile
from fastapi.testclient import TestClient
from app import app, FILES_DIR

def test_api_direct():
    """Прямое тестирование API"""
    print("🧪 Прямое тестирование API...")
    
    # Создаем тестовый файл
    test_filename = "test_direct_api.pdf"
    test_file_path = os.path.join(FILES_DIR, test_filename)
    
    # Создаем папку files если её нет
    os.makedirs(FILES_DIR, exist_ok=True)
    
    # Создаем тестовый файл
    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write("Test PDF content for direct API test")
    
    print(f"📄 Создан тестовый файл: {test_filename}")
    print(f"📁 Путь к файлу: {test_file_path}")
    print(f"📁 Папка files: {FILES_DIR}")
    
    # Тестируем с помощью TestClient
    client = TestClient(app)
    
    # Тест 1: Получение списка файлов
    print("\n📋 Тест получения списка файлов...")
    response = client.get("/api/files")
    print(f"📊 Статус /api/files: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"📁 Ответ API: {data}")
        
        if 'files' in data and test_filename in data['files']:
            print("✅ Файл найден в списке")
        else:
            print("❌ Файл не найден в списке")
            return False
    else:
        print(f"❌ Ошибка получения списка файлов: {response.status_code}")
        print(f"📄 Ответ: {response.text}")
        return False
    
    # Тест 2: Скачивание файла
    print("\n⬇️ Тест скачивания файла...")
    import urllib.parse
    encoded_filename = urllib.parse.quote(test_filename)
    download_url = f"/api/download/{encoded_filename}"
    
    print(f"🔗 URL для скачивания: {download_url}")
    
    response = client.get(download_url)
    print(f"📊 Статус скачивания: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ Файл успешно скачан!")
        print(f"📄 Размер файла: {len(response.content)} байт")
        return True
    else:
        print(f"❌ Ошибка скачивания файла: {response.status_code}")
        print(f"📄 Ответ: {response.text}")
        return False

def test_cyrillic_filename():
    """Тест с кириллическим именем файла"""
    print("\n🧪 Тест с кириллическим именем файла...")
    
    # Создаем тестовый файл с кириллическим именем
    test_filename = "тест_файл_кириллица.pdf"
    test_file_path = os.path.join(FILES_DIR, test_filename)
    
    # Создаем тестовый файл
    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write("Test PDF content with Cyrillic filename")
    
    print(f"📄 Создан тестовый файл: {test_filename}")
    
    # Тестируем с помощью TestClient
    client = TestClient(app)
    
    # Тест получения списка файлов
    response = client.get("/api/files")
    if response.status_code == 200:
        data = response.json()
        if 'files' in data and test_filename in data['files']:
            print("✅ Кириллический файл найден в списке")
        else:
            print("❌ Кириллический файл не найден в списке")
            return False
    else:
        print(f"❌ Ошибка получения списка файлов: {response.status_code}")
        return False
    
    # Тест скачивания кириллического файла
    import urllib.parse
    encoded_filename = urllib.parse.quote(test_filename)
    download_url = f"/api/download/{encoded_filename}"
    
    print(f"🔗 URL для скачивания кириллического файла: {download_url}")
    
    response = client.get(download_url)
    print(f"📊 Статус скачивания кириллического файла: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ Кириллический файл успешно скачан!")
        return True
    else:
        print(f"❌ Ошибка скачивания кириллического файла: {response.status_code}")
        print(f"📄 Ответ: {response.text}")
        return False

def cleanup_test_files():
    """Очистка тестовых файлов"""
    print("\n🧹 Очистка тестовых файлов...")
    
    test_files = ["test_direct_api.pdf", "тест_файл_кириллица.pdf"]
    
    for filename in test_files:
        file_path = os.path.join(FILES_DIR, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"🗑️ Удален тестовый файл: {filename}")

if __name__ == "__main__":
    print("🚀 Запуск прямого тестирования API\n")
    
    # Тест 1: Обычные файлы
    success1 = test_api_direct()
    
    # Тест 2: Кириллические файлы
    success2 = test_cyrillic_filename()
    
    # Очистка
    cleanup_test_files()
    
    # Результаты
    print("\n📊 РЕЗУЛЬТАТЫ ТЕСТОВ:")
    print(f"✅ Обычные файлы: {'ПРОЙДЕН' if success1 else 'ПРОВАЛЕН'}")
    print(f"✅ Кириллические файлы: {'ПРОЙДЕН' if success2 else 'ПРОВАЛЕН'}")
    
    if success1 and success2:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! API работает корректно!")
    else:
        print("\n❌ НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ! Требуется дополнительная отладка")
