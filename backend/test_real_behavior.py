#!/usr/bin/env python3
"""
Тест для симуляции реального поведения приложения
"""

import os
import tempfile
import shutil
from fastapi.testclient import TestClient
from app import app

def test_real_application_flow():
    """Симулирует реальный поток приложения"""
    print("🧪 Симуляция реального потока приложения...")
    
    # Создаем тестовые файлы (как после парсинга)
    test_files = [
        "А84-4753_2024_20251003_180941_1_A84-4753-2024_20240613_Opredelenie.pdf",
        "А84-4753_2024_20251003_180941_2_A84-4753-2024_20240805_Reshenija_i_postanovlenija.pdf"
    ]
    
    # Создаем папку files если её нет
    os.makedirs("files", exist_ok=True)
    
    # Создаем тестовые файлы
    for filename in test_files:
        file_path = os.path.join("files", filename)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"Test PDF content for {filename}")
        print(f"📄 Создан тестовый файл: {filename}")
    
    # Симулируем работу приложения
    client = TestClient(app)
    
    # 1. Симулируем parseCase() - получение списка файлов
    print("\n📡 Симуляция parseCase()...")
    response = client.get("/api/files")
    print(f"📊 Статус /api/files: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"📁 Данные от API: {data}")
        
        # 2. Симулируем getFilesList() - преобразование в объекты
        print("\n🔄 Симуляция getFilesList()...")
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
        
        # 3. Симулируем showSuccessPage() - создание HTML
        print("\n🎨 Симуляция showSuccessPage()...")
        if files and len(files) > 0:
            for i, file in enumerate(files):
                print(f"   Файл {i}: {file}")
                print(f"   Тип файла {i}: {type(file)}")
                
                if isinstance(file, dict) and 'name' in file and 'url' in file:
                    print(f"   ✅ Файл {i} имеет правильную структуру")
                    
                    # Симулируем создание HTML кнопки
                    filename = file['name']
                    url = file['url']
                    
                    print(f"   📝 Создаем HTML кнопку:")
                    print(f"   data-filename='{filename}'")
                    print(f"   data-url='{url}'")
                    
                    # Проверяем, что filename и url являются строками
                    if isinstance(filename, str) and isinstance(url, str):
                        print(f"   ✅ filename и url являются строками")
                        
                        # Симулируем клик по кнопке - извлечение атрибутов
                        print(f"   🖱️ Симуляция клика по кнопке...")
                        print(f"   Извлеченный filename: {filename} (тип: {type(filename)})")
                        print(f"   Извлеченный url: {url} (тип: {type(url)})")
                        
                        # Симулируем вызов downloadFile()
                        print(f"   📥 Симуляция вызова downloadFile('{filename}', '{url}')")
                        
                        # Проверяем, что параметры являются строками
                        if isinstance(filename, str) and isinstance(url, str):
                            print(f"   ✅ Параметры downloadFile являются строками")
                            
                            # Симулируем создание ссылки для скачивания
                            import urllib.parse
                            encoded_filename = urllib.parse.quote(filename)
                            download_url = f"/api/download/{encoded_filename}"
                            
                            print(f"   🔗 URL для скачивания: {download_url}")
                            
                            # Тестируем скачивание
                            response = client.get(download_url)
                            print(f"   📊 Статус скачивания: {response.status_code}")
                            
                            if response.status_code == 200:
                                print(f"   ✅ Файл {i} успешно скачан!")
                            else:
                                print(f"   ❌ Ошибка скачивания файла {i}: {response.status_code}")
                                print(f"   📄 Ответ: {response.text}")
                        else:
                            print(f"   ❌ Параметры downloadFile не являются строками")
                    else:
                        print(f"   ❌ filename или url не являются строками")
                else:
                    print(f"   ❌ Файл {i} не имеет правильную структуру")
        else:
            print("❌ Список файлов пуст")
    else:
        print(f"❌ Ошибка получения списка файлов: {response.status_code}")
    
    # Очищаем тестовые файлы
    for filename in test_files:
        file_path = os.path.join("files", filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"🗑️ Удален тестовый файл: {filename}")
    
    return response.status_code == 200

def test_object_object_scenario():
    """Тестирует сценарий, который может привести к [object Object]"""
    print("\n🧪 Тестирование сценария [object Object]...")
    
    # Создаем тестовый файл
    test_filename = "test_object_scenario.pdf"
    test_file_path = os.path.join("files", test_filename)
    
    # Создаем папку files если её нет
    os.makedirs("files", exist_ok=True)
    
    # Создаем тестовый файл
    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write("Test PDF content for object scenario")
    
    print(f"📄 Создан тестовый файл: {test_filename}")
    
    # Симулируем сценарий, который может привести к [object Object]
    client = TestClient(app)
    
    # 1. Получаем список файлов
    response = client.get("/api/files")
    if response.status_code == 200:
        data = response.json()
        files = data['files']
        
        print(f"📁 Файлы от API: {files}")
        
        # 2. Симулируем ошибку - передаем объект вместо строки
        print("\n⚠️ Симуляция ошибки - передаем объект вместо строки...")
        
        # Создаем объект файла
        file_obj = {
            'name': test_filename,
            'size': 0,
            'url': f"http://127.0.0.1:8000/api/download/{test_filename}",
            'created': "2025-10-03T18:00:00.000Z",
            'modified': "2025-10-03T18:00:00.000Z"
        }
        
        print(f"📁 Создан объект файла: {file_obj}")
        
        # Симулируем ошибку - передаем объект в downloadFile
        print(f"🖱️ Симуляция клика с объектом вместо строки...")
        
        # Это то, что может произойти при ошибке
        filename = file_obj  # ОШИБКА: передаем объект вместо строки
        url = file_obj['url']   # Это должно работать
        
        print(f"❌ filename (объект): {filename} (тип: {type(filename)})")
        print(f"✅ url (строка): {url} (тип: {type(url)})")
        
        # Симулируем то, что происходит в downloadFile
        print(f"📥 Симуляция downloadFile с объектом...")
        
        # При попытке использовать объект как строку
        try:
            # Это то, что происходит в HTML: data-filename="${file.name}"
            # Если file.name является объектом, то получается data-filename="[object Object]"
            html_filename = str(filename)  # Это даст "[object Object]"
            print(f"📝 HTML filename: {html_filename}")
            
            # При извлечении атрибута
            extracted_filename = html_filename  # Это будет "[object Object]"
            print(f"🔍 Извлеченный filename: {extracted_filename}")
            
            # При создании URL
            import urllib.parse
            encoded_filename = urllib.parse.quote(extracted_filename)
            download_url = f"/api/download/{encoded_filename}"
            
            print(f"🔗 URL для скачивания: {download_url}")
            
            # Тестируем скачивание
            response = client.get(download_url)
            print(f"📊 Статус скачивания: {response.status_code}")
            
            if response.status_code == 200:
                print(f"✅ Файл успешно скачан!")
            else:
                print(f"❌ Ошибка скачивания: {response.status_code}")
                print(f"📄 Ответ: {response.text}")
                
        except Exception as e:
            print(f"❌ Ошибка при симуляции: {e}")
    
    # Очищаем тестовый файл
    if os.path.exists(test_file_path):
        os.remove(test_file_path)
        print(f"🗑️ Удален тестовый файл: {test_filename}")
    
    return True

if __name__ == "__main__":
    print("🚀 Запуск тестов реального поведения приложения\n")
    
    # Тест 1: Реальный поток приложения
    success1 = test_real_application_flow()
    
    # Тест 2: Сценарий [object Object]
    success2 = test_object_object_scenario()
    
    if success1 and success2:
        print("\n✅ Все тесты завершены!")
        print("🎉 Проблема с [object Object] должна быть найдена!")
    else:
        print("\n❌ Некоторые тесты не прошли!")
        print("🔧 Требуется дополнительная отладка")
