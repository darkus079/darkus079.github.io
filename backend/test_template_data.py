#!/usr/bin/env python3
"""
Тест данных, передаваемых в шаблон result.html
"""

import os
from fastapi.testclient import TestClient
from app import app, FILES_DIR

def test_template_data():
    """Тестирует данные, передаваемые в шаблон"""
    print("🧪 Тестирование данных шаблона...")
    
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
    
    # Симулируем парсинг через POST запрос
    print("\n🔍 Симуляция парсинга...")
    
    # Сначала получаем список файлов
    response = client.get("/api/files")
    if response.status_code == 200:
        data = response.json()
        print(f"📁 Файлы в API: {data}")
        
        if 'files' in data and len(data['files']) > 0:
            # Тестируем скачивание каждого файла
            for filename in data['files']:
                print(f"\n📄 Тестируем файл: {filename}")
                print(f"📄 Тип: {type(filename)}")
                
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
        else:
            print("❌ Файлы не найдены")
            return False
    else:
        print(f"❌ Ошибка получения списка файлов: {response.status_code}")
        return False
    
    return True

def test_template_rendering():
    """Тестирует рендеринг шаблона с тестовыми данными"""
    print("\n🧪 Тестирование рендеринга шаблона...")
    
    from fastapi.templating import Jinja2Templates
    from fastapi import Request
    
    # Создаем тестовые данные
    test_data = {
        "success": True,
        "message": "Тестовое сообщение",
        "files": [
            "А84-4753_2024_20251006_104451_1_test1.pdf",
            "А84-4753_2024_20251006_104451_2_test2.pdf"
        ],
        "case_number": "А84-4753/2024"
    }
    
    status_data = {
        "is_parsing": False,
        "current_case": "",
        "progress": ""
    }
    
    # Создаем фиктивный request
    request = Request(scope={"type": "http", "method": "GET"})
    
    # Рендерим шаблон
    templates = Jinja2Templates(directory="templates")
    
    try:
        response = templates.TemplateResponse("result.html", {
            "request": request,
            "result": test_data,
            "status": status_data
        })
        
        print("✅ Шаблон успешно отрендерен")
        
        # Проверяем содержимое
        content = response.body.decode('utf-8')
        
        # Ищем ссылки на скачивание
        import re
        download_links = re.findall(r'href="/api/download/([^"]+)"', content)
        print(f"🔗 Найдены ссылки на скачивание: {download_links}")
        
        # Проверяем, что нет [object Object]
        if '[object Object]' in content:
            print("❌ Найден [object Object] в шаблоне!")
            return False
        else:
            print("✅ [object Object] не найден в шаблоне")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка рендеринга шаблона: {e}")
        return False

def cleanup_test_files():
    """Очистка тестовых файлов"""
    print("\n🧹 Очистка тестовых файлов...")
    
    test_files = [
        "А84-4753_2024_20251006_104451_1_test1.pdf",
        "А84-4753_2024_20251006_104451_2_test2.pdf"
    ]
    
    for filename in test_files:
        file_path = os.path.join(FILES_DIR, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"🗑️ Удален тестовый файл: {filename}")

if __name__ == "__main__":
    print("🚀 Запуск тестирования данных шаблона\n")
    
    # Тест 1: Данные API
    success1 = test_template_data()
    
    # Тест 2: Рендеринг шаблона
    success2 = test_template_rendering()
    
    # Очистка
    cleanup_test_files()
    
    # Результаты
    print("\n📊 РЕЗУЛЬТАТЫ ТЕСТОВ:")
    print(f"✅ Данные API: {'ПРОЙДЕН' if success1 else 'ПРОВАЛЕН'}")
    print(f"✅ Рендеринг шаблона: {'ПРОЙДЕН' if success2 else 'ПРОВАЛЕН'}")
    
    if success1 and success2:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Данные шаблона корректны!")
    else:
        print("\n❌ НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ! Требуется дополнительная отладка")
