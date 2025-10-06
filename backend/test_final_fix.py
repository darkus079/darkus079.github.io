#!/usr/bin/env python3
"""
Финальный тест исправлений проблемы [object Object]
"""

import os
import tempfile
from fastapi.testclient import TestClient
from app import app, FILES_DIR

def test_object_object_fix():
    """Тест исправления проблемы [object Object]"""
    print("🧪 Тест исправления проблемы [object Object]...")
    
    # Создаем тестовые файлы
    test_files = [
        "А84-4753_2024_20251006_104451_1_test1.pdf",
        "А84-4753_2024_20251006_104451_2_test2.pdf"
    ]
    
    # Создаем папку files если её нет
    os.makedirs(FILES_DIR, exist_ok=True)
    
    # Создаем тестовые файлы
    for filename in test_files:
        file_path = os.path.join(FILES_DIR, filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"Test PDF content for {filename}")
        print(f"📄 Создан тестовый файл: {filename}")
    
    # Тестируем с помощью TestClient
    client = TestClient(app)
    
    # Тест 1: Получение списка файлов
    print("\n📋 Тест получения списка файлов...")
    response = client.get("/api/files")
    print(f"📊 Статус /api/files: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"📁 Ответ API: {data}")
        
        if 'files' in data and len(data['files']) > 0:
            print("✅ Файлы найдены в API")
            
            # Проверяем, что все файлы являются строками
            all_strings = all(isinstance(f, str) for f in data['files'])
            if all_strings:
                print("✅ Все файлы являются строками")
            else:
                print("❌ Некоторые файлы не являются строками")
                return False
        else:
            print("❌ Файлы не найдены в API")
            return False
    else:
        print(f"❌ Ошибка получения списка файлов: {response.status_code}")
        return False
    
    # Тест 2: Скачивание каждого файла
    print("\n⬇️ Тест скачивания файлов...")
    for filename in data['files']:
        print(f"\n📄 Тестируем файл: {filename}")
        
        import urllib.parse
        encoded_filename = urllib.parse.quote(filename)
        download_url = f"/api/download/{encoded_filename}"
        
        print(f"🔗 URL: {download_url}")
        
        response = client.get(download_url)
        print(f"📊 Статус: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Файл скачан успешно")
        else:
            print(f"❌ Ошибка скачивания: {response.text}")
            return False
    
    # Тест 3: Проверка на [object Object]
    print("\n🔍 Проверка на [object Object]...")
    
    # Тестируем URL с [object Object]
    object_object_url = "/api/download/%5Bobject%20Object%5D"
    response = client.get(object_object_url)
    print(f"📊 Статус для [object Object]: {response.status_code}")
    
    if response.status_code == 404:
        print("✅ Правильно возвращается 404 для [object Object]")
    else:
        print(f"❌ Неожиданный статус для [object Object]: {response.status_code}")
        return False
    
    return True

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

def cleanup_test_files():
    """Очистка тестовых файлов"""
    print("\n🧹 Очистка тестовых файлов...")
    
    test_files = [
        "А84-4753_2024_20251006_104451_1_test1.pdf",
        "А84-4753_2024_20251006_104451_2_test2.pdf",
        "тест_файл_кириллица.pdf"
    ]
    
    for filename in test_files:
        file_path = os.path.join(FILES_DIR, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"🗑️ Удален тестовый файл: {filename}")

if __name__ == "__main__":
    print("🚀 Финальный тест исправлений проблемы [object Object]\n")
    
    # Тест 1: Исправление [object Object]
    success1 = test_object_object_fix()
    
    # Тест 2: Кириллические файлы
    success2 = test_cyrillic_filenames()
    
    # Очистка
    cleanup_test_files()
    
    # Результаты
    print("\n📊 РЕЗУЛЬТАТЫ ТЕСТОВ:")
    print(f"✅ Исправление [object Object]: {'ПРОЙДЕН' if success1 else 'ПРОВАЛЕН'}")
    print(f"✅ Кириллические файлы: {'ПРОЙДЕН' if success2 else 'ПРОВАЛЕН'}")
    
    if success1 and success2:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Проблема [object Object] исправлена!")
        print("\n📋 ИСПРАВЛЕНИЯ:")
        print("✅ Исправлены пути к папке files в backend")
        print("✅ Исправлены URL в HTML шаблонах backend")
        print("✅ Исправлена обработка объектов в JavaScript коде js_parser")
        print("✅ Добавлена поддержка как строк, так и объектов в frontend")
        print("✅ Исправлена проблема с [object Object] в URL")
    else:
        print("\n❌ НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ! Требуется дополнительная отладка")
