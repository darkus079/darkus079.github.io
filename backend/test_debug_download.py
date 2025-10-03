#!/usr/bin/env python3
"""
Тест для отладки проблемы с [object Object] при скачивании файлов
"""

import os
import tempfile
import shutil
from fastapi.testclient import TestClient
from app import app

def test_api_files_response():
    """Тестирует ответ API /api/files"""
    print("🧪 Тестирование ответа API /api/files...")
    
    # Создаем тестовый файл
    test_filename = "test_debug_file.pdf"
    test_file_path = os.path.join("files", test_filename)
    
    # Создаем папку files если её нет
    os.makedirs("files", exist_ok=True)
    
    # Создаем тестовый файл
    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write("Test PDF content for debug")
    
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
        print(f"📁 Ключи: {data.keys() if isinstance(data, dict) else 'Не словарь'}")
        
        if 'files' in data:
            files = data['files']
            print(f"📁 Файлы: {files}")
            print(f"📁 Тип файлов: {type(files)}")
            print(f"📁 Длина файлов: {len(files) if isinstance(files, list) else 'Не список'}")
            
            if isinstance(files, list) and len(files) > 0:
                print(f"📁 Первый файл: {files[0]}")
                print(f"📁 Тип первого файла: {type(files[0])}")
                
                # Тестируем скачивание первого файла
                if test_filename in files:
                    print(f"✅ Тестовый файл найден в списке")
                    
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
                    print(f"❌ Тестовый файл не найден в списке")
            else:
                print(f"❌ Список файлов пуст или не является списком")
        else:
            print(f"❌ Ключ 'files' не найден в ответе")
    else:
        print(f"❌ Ошибка получения списка файлов: {response.status_code}")
        print(f"📄 Ответ: {response.text}")
    
    # Очищаем тестовый файл
    if os.path.exists(test_file_path):
        os.remove(test_file_path)
        print("🗑️ Тестовый файл удален")
    
    return response.status_code == 200

def test_backend_client_simulation():
    """Симулирует работу backend-client.js"""
    print("\n🧪 Симуляция работы backend-client.js...")
    
    # Создаем тестовый файл
    test_filename = "test_backend_client.pdf"
    test_file_path = os.path.join("files", test_filename)
    
    # Создаем папку files если её нет
    os.makedirs("files", exist_ok=True)
    
    # Создаем тестовый файл
    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write("Test PDF content for backend client simulation")
    
    print(f"📄 Создан тестовый файл: {test_filename}")
    
    # Симулируем работу backend-client.js
    client = TestClient(app)
    
    # 1. Получаем список файлов (как в getFilesList())
    response = client.get("/api/files")
    print(f"📊 Статус /api/files: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"📁 Данные от API: {data}")
        
        # 2. Преобразуем в формат, ожидаемый frontend (как в getFilesList())
        files = [{
            'name': fileName,
            'size': 0,  # Размер не доступен через API
            'url': f"http://127.0.0.1:8000/api/download/{fileName}",
            'created': "2025-10-03T18:00:00.000Z",
            'modified': "2025-10-03T18:00:00.000Z"
        } for fileName in data['files']]
        
        print(f"📁 Преобразованные файлы: {files}")
        print(f"📁 Тип файлов: {type(files)}")
        print(f"📁 Длина файлов: {len(files)}")
        
        if len(files) > 0:
            first_file = files[0]
            print(f"📁 Первый файл: {first_file}")
            print(f"📁 Тип первого файла: {type(first_file)}")
            print(f"📁 Ключи первого файла: {first_file.keys() if isinstance(first_file, dict) else 'Не словарь'}")
            
            # 3. Проверяем, что файл имеет правильную структуру
            if isinstance(first_file, dict) and 'name' in first_file and 'url' in first_file:
                print("✅ Файл имеет правильную структуру")
                print(f"   name: {first_file['name']} (тип: {type(first_file['name'])})")
                print(f"   url: {first_file['url']} (тип: {type(first_file['url'])})")
                
                # 4. Тестируем скачивание
                import urllib.parse
                encoded_filename = urllib.parse.quote(first_file['name'])
                download_url = f"/api/download/{encoded_filename}"
                
                print(f"🔗 URL для скачивания: {download_url}")
                
                response = client.get(download_url)
                print(f"📊 Статус скачивания: {response.status_code}")
                
                if response.status_code == 200:
                    print("✅ Файл успешно скачан!")
                else:
                    print(f"❌ Ошибка скачивания: {response.status_code}")
            else:
                print("❌ Файл не имеет правильную структуру")
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
    print("🚀 Запуск тестов отладки проблемы с [object Object]\n")
    
    # Тест 1: Ответ API /api/files
    success1 = test_api_files_response()
    
    # Тест 2: Симуляция backend-client.js
    success2 = test_backend_client_simulation()
    
    if success1 and success2:
        print("\n✅ Все тесты прошли успешно!")
        print("🎉 Проблема с [object Object] должна быть решена!")
    else:
        print("\n❌ Некоторые тесты не прошли!")
        print("🔧 Требуется дополнительная отладка")
