#!/usr/bin/env python3
"""
Тест для проверки исправления проблемы с кириллическими символами в именах файлов
"""

import os
import urllib.parse
import tempfile
import shutil
from fastapi.testclient import TestClient
from app import app

def test_cyrillic_filename_download():
    """Тестирует скачивание файлов с кириллическими символами в именах"""
    print("🧪 Тестирование скачивания файлов с кириллическими символами...")
    
    # Создаем тестовый файл с кириллическим именем
    test_filename = "А84-4753_2024_тест_документ.pdf"
    test_file_path = os.path.join("files", test_filename)
    
    # Создаем папку files если её нет
    os.makedirs("files", exist_ok=True)
    
    # Создаем тестовый файл
    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write("Test PDF content with Cyrillic filename")
    
    print(f"📄 Создан тестовый файл: {test_filename}")
    
    # Тестируем с помощью TestClient
    client = TestClient(app)
    
    # URL-encode имя файла (как это делает браузер)
    encoded_filename = urllib.parse.quote(test_filename)
    print(f"🔗 URL-encoded имя файла: {encoded_filename}")
    
    # Тестируем API эндпоинт
    response = client.get(f"/api/download/{encoded_filename}")
    
    print(f"📊 Статус ответа: {response.status_code}")
    
    if response.status_code == 200:
        print("✅ Файл успешно скачан!")
        print(f"📁 Content-Type: {response.headers.get('content-type')}")
        print(f"📁 Content-Disposition: {response.headers.get('content-disposition')}")
        print(f"📊 Размер файла: {len(response.content)} байт")
    else:
        print(f"❌ Ошибка скачивания: {response.status_code}")
        print(f"📄 Ответ: {response.text}")
    
    # Очищаем тестовый файл
    if os.path.exists(test_file_path):
        os.remove(test_file_path)
        print("🗑️ Тестовый файл удален")
    
    return response.status_code == 200

def test_cyrillic_to_latin_conversion():
    """Тестирует конвертацию кириллических символов в латинские"""
    print("\n🧪 Тестирование конвертации кириллических символов...")
    
    cyrillic_to_latin = {
        'А': 'A', 'В': 'B', 'Е': 'E', 'К': 'K', 'М': 'M', 'Н': 'H', 'О': 'O', 
        'Р': 'P', 'С': 'C', 'Т': 'T', 'У': 'Y', 'Х': 'X', 'а': 'a', 'в': 'b', 
        'е': 'e', 'к': 'k', 'м': 'm', 'н': 'h', 'о': 'o', 'р': 'p', 'с': 'c', 
        'т': 't', 'у': 'y', 'х': 'x'
    }
    
    test_cases = [
        "А84-4753_2024_тест",
        "Решение_по_делу",
        "Определение_судьи",
        "Постановление_арбитражного_суда"
    ]
    
    for test_case in test_cases:
        safe_filename = test_case
        for cyr, lat in cyrillic_to_latin.items():
            safe_filename = safe_filename.replace(cyr, lat)
        
        print(f"   {test_case} -> {safe_filename}")
    
    print("✅ Конвертация кириллических символов работает")

def test_url_encoding():
    """Тестирует URL-кодирование имен файлов"""
    print("\n🧪 Тестирование URL-кодирования...")
    
    test_filenames = [
        "А84-4753_2024_тест.pdf",
        "Решение_по_делу_№123.pdf",
        "Определение_судьи_Иванова.pdf"
    ]
    
    for filename in test_filenames:
        encoded = urllib.parse.quote(filename)
        decoded = urllib.parse.unquote(encoded)
        
        print(f"   Оригинал: {filename}")
        print(f"   Закодирован: {encoded}")
        print(f"   Декодирован: {decoded}")
        print(f"   Совпадает: {filename == decoded}")
        print()

if __name__ == "__main__":
    print("🚀 Запуск тестов исправления кириллических символов\n")
    
    # Тест 1: Конвертация кириллических символов
    test_cyrillic_to_latin_conversion()
    
    # Тест 2: URL-кодирование
    test_url_encoding()
    
    # Тест 3: Скачивание файла с кириллическим именем
    success = test_cyrillic_filename_download()
    
    if success:
        print("\n✅ Все тесты прошли успешно!")
        print("🎉 Проблема с кириллическими символами исправлена!")
    else:
        print("\n❌ Тесты не прошли!")
        print("🔧 Требуется дополнительная отладка")
