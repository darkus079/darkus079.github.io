#!/usr/bin/env python3
"""
Тест для проверки исправлений скачивания файлов
"""

import os
import tempfile
import shutil
from fastapi.testclient import TestClient
from app import app, FILES_DIR

def test_files_directory_creation():
    """Тест создания папки files"""
    print("🧪 Тест создания папки files...")
    
    # Удаляем папку files если она существует
    if os.path.exists(FILES_DIR):
        shutil.rmtree(FILES_DIR)
        print(f"🗑️ Удалена существующая папка: {FILES_DIR}")
    
    # Создаем клиент
    client = TestClient(app)
    
    # Вызываем lifespan startup
    with client:
        # Проверяем, что папка создалась
        if os.path.exists(FILES_DIR):
            print(f"✅ Папка files создана: {FILES_DIR}")
            return True
        else:
            print(f"❌ Папка files не создана: {FILES_DIR}")
            return False

def test_file_operations():
    """Тест операций с файлами"""
    print("\n🧪 Тест операций с файлами...")
    
    # Создаем тестовый файл
    test_filename = "test_file.pdf"
    test_file_path = os.path.join(FILES_DIR, test_filename)
    
    # Создаем папку files если её нет
    os.makedirs(FILES_DIR, exist_ok=True)
    
    # Создаем тестовый файл
    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write("Test PDF content")
    
    print(f"📄 Создан тестовый файл: {test_filename}")
    
    # Тестируем с помощью TestClient
    client = TestClient(app)
    
    # Тест 1: Получение списка файлов
    print("📋 Тест получения списка файлов...")
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
        return False
    
    # Тест 2: Скачивание файла
    print("⬇️ Тест скачивания файла...")
    import urllib.parse
    encoded_filename = urllib.parse.quote(test_filename)
    download_url = f"/api/download/{encoded_filename}"
    
    print(f"🔗 URL для скачивания: {download_url}")
    
    response = client.get(download_url)
    print(f"📊 Статус скачивания: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ Файл успешно скачан!")
        return True
    else:
        print(f"❌ Ошибка скачивания файла: {response.status_code}")
        print(f"📄 Ответ: {response.text}")
        return False

def test_cyrillic_filenames():
    """Тест с кириллическими именами файлов"""
    print("\n🧪 Тест с кириллическими именами файлов...")
    
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

def test_object_object_fix():
    """Тест исправления проблемы [object Object]"""
    print("\n🧪 Тест исправления проблемы [object Object]...")
    
    # Тестируем URL с [object Object]
    client = TestClient(app)
    
    # Симулируем запрос с [object Object]
    object_object_url = "/api/download/%5Bobject%20Object%5D"
    print(f"🔗 Тестируем URL с [object Object]: {object_object_url}")
    
    response = client.get(object_object_url)
    print(f"📊 Статус ответа: {response.status_code}")
    
    if response.status_code == 404:
        print("✅ Правильно возвращается 404 для [object Object]")
        return True
    else:
        print(f"❌ Неожиданный статус для [object Object]: {response.status_code}")
        return False

def cleanup_test_files():
    """Очистка тестовых файлов"""
    print("\n🧹 Очистка тестовых файлов...")
    
    if os.path.exists(FILES_DIR):
        for filename in os.listdir(FILES_DIR):
            if filename.startswith("test_"):
                file_path = os.path.join(FILES_DIR, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
                    print(f"🗑️ Удален тестовый файл: {filename}")

if __name__ == "__main__":
    print("🚀 Запуск тестов исправлений скачивания файлов\n")
    
    # Тест 1: Создание папки files
    success1 = test_files_directory_creation()
    
    # Тест 2: Операции с файлами
    success2 = test_file_operations()
    
    # Тест 3: Кириллические имена файлов
    success3 = test_cyrillic_filenames()
    
    # Тест 4: Исправление [object Object]
    success4 = test_object_object_fix()
    
    # Очистка
    cleanup_test_files()
    
    # Результаты
    print("\n📊 РЕЗУЛЬТАТЫ ТЕСТОВ:")
    print(f"✅ Создание папки files: {'ПРОЙДЕН' if success1 else 'ПРОВАЛЕН'}")
    print(f"✅ Операции с файлами: {'ПРОЙДЕН' if success2 else 'ПРОВАЛЕН'}")
    print(f"✅ Кириллические имена: {'ПРОЙДЕН' if success3 else 'ПРОВАЛЕН'}")
    print(f"✅ Исправление [object Object]: {'ПРОЙДЕН' if success4 else 'ПРОВАЛЕН'}")
    
    if all([success1, success2, success3, success4]):
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Проблема с скачиванием файлов исправлена!")
    else:
        print("\n❌ НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ! Требуется дополнительная отладка")
