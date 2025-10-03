#!/usr/bin/env python3
"""
Тест для отладки проблемы с [object Object] - детальная диагностика
"""

import os
import tempfile
import shutil
from fastapi.testclient import TestClient
from app import app

def test_api_files_detailed():
    """Детальное тестирование API /api/files"""
    print("🧪 Детальное тестирование API /api/files...")
    
    # Создаем тестовый файл
    test_filename = "test_object_debug.pdf"
    test_file_path = os.path.join("files", test_filename)
    
    # Создаем папку files если её нет
    os.makedirs("files", exist_ok=True)
    
    # Создаем тестовый файл
    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write("Test PDF content for object debug")
    
    print(f"📄 Создан тестовый файл: {test_filename}")
    
    # Тестируем с помощью TestClient
    client = TestClient(app)
    
    # Тестируем API эндпоинт /api/files
    response = client.get("/api/files")
    print(f"📊 Статус /api/files: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"📁 Ответ API: {data}")
        print(f"📁 Тип ответа: {type(data)}")
        print(f"📁 Ключи: {list(data.keys()) if isinstance(data, dict) else 'Не словарь'}")
        
        if 'files' in data:
            files = data['files']
            print(f"📁 Файлы: {files}")
            print(f"📁 Тип файлов: {type(files)}")
            print(f"📁 Длина файлов: {len(files) if isinstance(files, list) else 'Не список'}")
            
            if isinstance(files, list) and len(files) > 0:
                for i, file in enumerate(files):
                    print(f"📁 Файл {i}: {file} (тип: {type(file)})")
                    
                    # Проверяем, что файл является строкой
                    if isinstance(file, str):
                        print(f"   ✅ Файл {i} является строкой")
                        
                        # Тестируем скачивание файла
                        import urllib.parse
                        encoded_filename = urllib.parse.quote(file)
                        download_url = f"/api/download/{encoded_filename}"
                        
                        print(f"   🔗 URL для скачивания: {download_url}")
                        
                        response = client.get(download_url)
                        print(f"   📊 Статус скачивания: {response.status_code}")
                        
                        if response.status_code == 200:
                            print(f"   ✅ Файл {i} успешно скачан!")
                        else:
                            print(f"   ❌ Ошибка скачивания файла {i}: {response.status_code}")
                            print(f"   📄 Ответ: {response.text}")
                    else:
                        print(f"   ❌ Файл {i} НЕ является строкой: {type(file)}")
            else:
                print("❌ Список файлов пуст или не является списком")
        else:
            print("❌ Ключ 'files' не найден в ответе")
    else:
        print(f"❌ Ошибка получения списка файлов: {response.status_code}")
        print(f"📄 Ответ: {response.text}")
    
    # Очищаем тестовый файл
    if os.path.exists(test_file_path):
        os.remove(test_file_path)
        print("🗑️ Тестовый файл удален")
    
    return response.status_code == 200

def test_simulate_frontend_behavior():
    """Симулирует поведение frontend"""
    print("\n🧪 Симуляция поведения frontend...")
    
    # Создаем тестовый файл
    test_filename = "test_frontend_simulation.pdf"
    test_file_path = os.path.join("files", test_filename)
    
    # Создаем папку files если её нет
    os.makedirs("files", exist_ok=True)
    
    # Создаем тестовый файл
    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write("Test PDF content for frontend simulation")
    
    print(f"📄 Создан тестовый файл: {test_filename}")
    
    # Симулируем работу frontend
    client = TestClient(app)
    
    # 1. Получаем список файлов (как в getFilesList())
    response = client.get("/api/files")
    print(f"📊 Статус /api/files: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"📁 Данные от API: {data}")
        
        # 2. Преобразуем в формат, ожидаемый frontend (как в getFilesList())
        files = []
        for fileName in data['files']:
            print(f"   Обрабатываем файл: {fileName} (тип: {type(fileName)})")
            
            if isinstance(fileName, str):
                file_obj = {
                    'name': fileName,
                    'size': 0,
                    'url': f"http://127.0.0.1:8000/api/download/{fileName}",
                    'created': "2025-10-03T18:00:00.000Z",
                    'modified': "2025-10-03T18:00:00.000Z"
                }
                files.append(file_obj)
                print(f"   ✅ Создан объект файла: {file_obj}")
            else:
                print(f"   ❌ Файл не является строкой: {type(fileName)}")
        
        print(f"📁 Преобразованные файлы: {files}")
        print(f"📁 Количество файлов: {len(files)}")
        
        # 3. Симулируем showSuccessPage
        if files and len(files) > 0:
            print("📁 Симуляция showSuccessPage...")
            for i, file in enumerate(files):
                print(f"   Файл {i}: {file}")
                print(f"   Тип файла {i}: {type(file)}")
                print(f"   name: {file.get('name')} (тип: {type(file.get('name'))})")
                print(f"   url: {file.get('url')} (тип: {type(file.get('url'))})")
                
                # Проверяем, что файл имеет правильную структуру
                if isinstance(file, dict) and 'name' in file and 'url' in file:
                    print(f"   ✅ Файл {i} имеет правильную структуру")
                    
                    # Симулируем создание кнопки скачивания
                    filename = file['name']
                    url = file['url']
                    
                    print(f"   📝 Создаем кнопку с data-filename='{filename}' data-url='{url}'")
                    
                    # Проверяем, что filename и url являются строками
                    if isinstance(filename, str) and isinstance(url, str):
                        print(f"   ✅ filename и url являются строками")
                        
                        # Тестируем скачивание
                        import urllib.parse
                        encoded_filename = urllib.parse.quote(filename)
                        download_url = f"/api/download/{encoded_filename}"
                        
                        print(f"   🔗 URL для скачивания: {download_url}")
                        
                        response = client.get(download_url)
                        print(f"   📊 Статус скачивания: {response.status_code}")
                        
                        if response.status_code == 200:
                            print(f"   ✅ Файл {i} успешно скачан!")
                        else:
                            print(f"   ❌ Ошибка скачивания файла {i}: {response.status_code}")
                    else:
                        print(f"   ❌ filename или url не являются строками")
                else:
                    print(f"   ❌ Файл {i} не имеет правильную структуру")
        else:
            print("❌ Список файлов пуст")
    else:
        print(f"❌ Ошибка получения списка файлов: {response.status_code}")
    
    # Очищаем тестовый файл
    if os.path.exists(test_file_path):
        os.remove(test_file_path)
        print("🗑️ Тестовый файл удален")
    
    return response.status_code == 200

if __name__ == "__main__":
    print("🚀 Запуск детальной диагностики проблемы с [object Object]\n")
    
    # Тест 1: Детальное тестирование API
    success1 = test_api_files_detailed()
    
    # Тест 2: Симуляция frontend
    success2 = test_simulate_frontend_behavior()
    
    if success1 and success2:
        print("\n✅ Все тесты прошли успешно!")
        print("🎉 Проблема с [object Object] должна быть найдена!")
    else:
        print("\n❌ Некоторые тесты не прошли!")
        print("🔧 Требуется дополнительная отладка")
