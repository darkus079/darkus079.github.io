#!/usr/bin/env python3
"""
Тест реального скачивания файлов с запущенным сервером
"""

import os
import time
import subprocess
import requests
import threading
from pathlib import Path

def start_server():
    """Запускает сервер в отдельном процессе"""
    print("🚀 Запуск сервера...")
    process = subprocess.Popen(
        ["python", "app.py"],
        cwd=os.path.dirname(os.path.abspath(__file__)),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    return process

def wait_for_server(max_wait=30):
    """Ждет пока сервер запустится"""
    print("⏳ Ожидание запуска сервера...")
    for i in range(max_wait):
        try:
            response = requests.get("http://localhost:8000/", timeout=2)
            if response.status_code == 200:
                print("✅ Сервер запущен!")
                return True
        except:
            pass
        time.sleep(1)
        print(f"⏳ Попытка {i+1}/{max_wait}...")
    
    print("❌ Сервер не запустился за отведенное время")
    return False

def test_download_flow():
    """Тестирует полный процесс скачивания"""
    print("\n🧪 Тестирование процесса скачивания...")
    
    # 1. Проверяем список файлов
    print("📋 Проверка списка файлов...")
    try:
        response = requests.get("http://localhost:8000/api/files")
        print(f"📊 Статус /api/files: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"📁 Файлы: {data}")
            
            if 'files' in data and len(data['files']) > 0:
                filename = data['files'][0]
                print(f"📄 Тестируем скачивание файла: {filename}")
                
                # 2. Тестируем скачивание файла
                import urllib.parse
                encoded_filename = urllib.parse.quote(filename)
                download_url = f"http://localhost:8000/api/download/{encoded_filename}"
                
                print(f"🔗 URL для скачивания: {download_url}")
                
                response = requests.get(download_url)
                print(f"📊 Статус скачивания: {response.status_code}")
                
                if response.status_code == 200:
                    print("✅ Файл успешно скачан!")
                    print(f"📄 Размер файла: {len(response.content)} байт")
                    return True
                else:
                    print(f"❌ Ошибка скачивания: {response.status_code}")
                    print(f"📄 Ответ: {response.text}")
                    return False
            else:
                print("❌ Файлы не найдены")
                return False
        else:
            print(f"❌ Ошибка получения списка файлов: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        return False

def test_parsing_flow():
    """Тестирует процесс парсинга"""
    print("\n🧪 Тестирование процесса парсинга...")
    
    # Создаем тестовый файл для парсинга
    test_filename = "test_parsing_result.pdf"
    test_file_path = os.path.join("files", test_filename)
    
    # Создаем папку files если её нет
    os.makedirs("files", exist_ok=True)
    
    # Создаем тестовый файл
    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write("Test PDF content for parsing test")
    
    print(f"📄 Создан тестовый файл: {test_filename}")
    
    # Тестируем получение списка файлов
    try:
        response = requests.get("http://localhost:8000/api/files")
        if response.status_code == 200:
            data = response.json()
            print(f"📁 Файлы после создания тестового: {data}")
            
            if test_filename in data.get('files', []):
                print("✅ Тестовый файл найден в списке")
                
                # Тестируем скачивание
                import urllib.parse
                encoded_filename = urllib.parse.quote(test_filename)
                download_url = f"http://localhost:8000/api/download/{encoded_filename}"
                
                response = requests.get(download_url)
                print(f"📊 Статус скачивания тестового файла: {response.status_code}")
                
                if response.status_code == 200:
                    print("✅ Тестовый файл успешно скачан!")
                    return True
                else:
                    print(f"❌ Ошибка скачивания тестового файла: {response.status_code}")
                    print(f"📄 Ответ: {response.text}")
                    return False
            else:
                print("❌ Тестовый файл не найден в списке")
                return False
        else:
            print(f"❌ Ошибка получения списка файлов: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка тестирования парсинга: {e}")
        return False
    finally:
        # Очищаем тестовый файл
        if os.path.exists(test_file_path):
            os.remove(test_file_path)
            print("🗑️ Тестовый файл удален")

def main():
    """Основная функция тестирования"""
    print("🚀 Запуск тестов реального скачивания файлов\n")
    
    # Запускаем сервер
    server_process = start_server()
    
    try:
        # Ждем запуска сервера
        if not wait_for_server():
            return False
        
        # Тест 1: Проверка существующих файлов
        success1 = test_download_flow()
        
        # Тест 2: Тестирование парсинга
        success2 = test_parsing_flow()
        
        # Результаты
        print("\n📊 РЕЗУЛЬТАТЫ ТЕСТОВ:")
        print(f"✅ Скачивание существующих файлов: {'ПРОЙДЕН' if success1 else 'ПРОВАЛЕН'}")
        print(f"✅ Тестирование парсинга: {'ПРОЙДЕН' if success2 else 'ПРОВАЛЕН'}")
        
        if success1 and success2:
            print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Скачивание файлов работает!")
        else:
            print("\n❌ НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ! Требуется дополнительная отладка")
        
        return success1 and success2
        
    finally:
        # Останавливаем сервер
        print("\n🛑 Остановка сервера...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()
        print("✅ Сервер остановлен")

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
