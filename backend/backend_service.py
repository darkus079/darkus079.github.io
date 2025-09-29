# -*- coding: utf-8 -*-
import asyncio
import os
import logging
import shutil
import time
import signal
import sys
from contextlib import asynccontextmanager
from typing import List, Dict, Any
from datetime import datetime, timedelta
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Form, Depends
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import threading
import queue
import json

from parser_simplified import KadArbitrParser

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backend.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Глобальные переменные
parser = None
parsing_queue = queue.Queue()
parsing_status = {
    "is_parsing": False, 
    "current_case": "", 
    "progress": "",
    "start_time": None,
    "files_count": 0
}
parsing_history = []
max_history = 50
file_cleanup_interval = 3600  # 1 час
max_file_age = 86400  # 24 часа
shutdown_event = threading.Event()

class ParseRequest(BaseModel):
    case_number: str

class ParseResponse(BaseModel):
    success: bool
    message: str
    files: List[str] = []
    case_number: str = ""
    processing_time: float = 0.0

class StatusResponse(BaseModel):
    is_parsing: bool
    current_case: str
    progress: str
    start_time: str = None
    files_count: int = 0
    queue_size: int = 0

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    global parser, parsing_status
    
    logger.info("🚀 Запуск backend сервиса парсера kad.arbitr.ru")
    
    # Сброс всех данных при запуске
    parsing_status = {
        "is_parsing": False, 
        "current_case": "", 
        "progress": "",
        "start_time": None,
        "files_count": 0
    }
    
    # Очистка папки files
    files_dir = "files"
    if os.path.exists(files_dir):
        try:
            for filename in os.listdir(files_dir):
                file_path = os.path.join(files_dir, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            logger.info("✅ Папка files очищена")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось очистить папку files: {e}")
    
    # Инициализация парсера
    logger.info("🔧 Инициализация парсера...")
    try:
        parser = KadArbitrParser()
        logger.info("📁 Папка для скачивания: C:\\Users\\gugu\\Downloads")
        logger.info("📁 Папка для сохранения: D:\\CODE\\sinichka_python\\github_pages\\darkus079.github.io\\backend\\files")
        logger.info("✅ Парсер инициализирован")
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации парсера: {e}")
        parser = None
    
    # Запуск фоновых задач
    cleanup_task = asyncio.create_task(periodic_cleanup())
    queue_processor_task = asyncio.create_task(queue_processor())
    
    logger.info("✅ Backend сервис полностью инициализирован")
    
    yield
    
    # Очистка при завершении
    logger.info("🛑 Завершение работы backend сервиса...")
    
    # Устанавливаем флаг завершения
    shutdown_event.set()
    
    # Отменяем фоновые задачи
    cleanup_task.cancel()
    queue_processor_task.cancel()
    
    # Ждем завершения обработки очереди (сокращенный таймаут)
    try:
        await asyncio.wait_for(queue_processor_task, timeout=2.0)
    except asyncio.TimeoutError:
        logger.warning("⚠️ Таймаут ожидания завершения обработки очереди")
    
    # Закрываем парсер
    if parser:
        try:
            parser.close()
        except Exception as e:
            logger.warning(f"⚠️ Ошибка закрытия парсера: {e}")
    
    logger.info("✅ Backend сервис остановлен")

# Создание приложения FastAPI
app = FastAPI(
    title="Парсер kad.arbitr.ru - Backend Service",
    description="Backend сервис для парсинга PDF файлов из арбитражных дел",
    version="2.0.0",
    lifespan=lifespan
)

# Настройка CORS для GitHub Pages
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://darkus079.github.io",
        "https://darkus079.github.io/",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Подключение статических файлов и шаблонов
templates = Jinja2Templates(directory="templates")

def cleanup_old_files():
    """Очистка старых файлов"""
    try:
        files_dir = "files"
        if not os.path.exists(files_dir):
            return
        
        current_time = time.time()
        removed_count = 0
        
        for filename in os.listdir(files_dir):
            file_path = os.path.join(files_dir, filename)
            if os.path.isfile(file_path):
                file_age = current_time - os.path.getmtime(file_path)
                if file_age > max_file_age:
                    os.remove(file_path)
                    removed_count += 1
                    logger.info(f"🗑️ Удален старый файл: {filename}")
        
        if removed_count > 0:
            logger.info(f"✅ Очищено {removed_count} старых файлов")
            
    except Exception as e:
        logger.error(f"❌ Ошибка очистки файлов: {e}")

async def periodic_cleanup():
    """Периодическая очистка файлов"""
    while True:
        try:
            await asyncio.sleep(file_cleanup_interval)
            cleanup_old_files()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"❌ Ошибка в periodic_cleanup: {e}")

async def queue_processor():
    """Обработчик очереди парсинга"""
    while not shutdown_event.is_set():
        try:
            # Используем asyncio.sleep вместо блокирующего queue.get
            await asyncio.sleep(0.1)  # Небольшая задержка для проверки очереди
            
            # Проверяем очередь без блокировки
            try:
                case_number = parsing_queue.get_nowait()
                
                if case_number is None:  # Сигнал остановки
                    break
                    
                await process_parsing_request(case_number)
                parsing_queue.task_done()
                
            except queue.Empty:
                # Очередь пуста, продолжаем цикл
                continue
                
        except Exception as e:
            logger.error(f"❌ Ошибка в queue_processor: {e}")
            await asyncio.sleep(1)  # Задержка при ошибке
    
    logger.info("🛑 Обработчик очереди остановлен")

async def process_parsing_request(case_number: str):
    """Обработка запроса на парсинг"""
    global parsing_status
    
    start_time = time.time()
    
    try:
        # Обновляем статус
        parsing_status.update({
            "is_parsing": True,
            "current_case": case_number,
            "progress": "Начинаем парсинг...",
            "start_time": datetime.now().isoformat(),
            "files_count": 0
        })
        
        logger.info(f"🔄 Начало парсинга дела: {case_number}")
        logger.info(f"🔍 Поиск дела в базе kad.arbitr.ru...")
        
        # Выполняем парсинг в отдельном потоке
        loop = asyncio.get_event_loop()
        
        def progress_callback(progress_text):
            parsing_status["progress"] = progress_text
            logger.info(f"📊 {progress_text}")
        
        # Добавляем дополнительное логирование перед парсингом
        logger.info(f"🌐 Открытие браузера для парсинга...")
        logger.info(f"📋 Переход на сайт kad.arbitr.ru...")
        
        downloaded_files = await loop.run_in_executor(
            None, 
            parser.parse_case, 
            case_number.strip()
        )
        
        processing_time = time.time() - start_time
        
        # Детальное логирование результата
        if downloaded_files:
            logger.info(f"📁 Найдено документов: {len(downloaded_files)}")
            for i, file_path in enumerate(downloaded_files, 1):
                file_name = os.path.basename(file_path)
                file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
                file_size_mb = file_size / (1024 * 1024)
                logger.info(f"📄 Документ {i}: {file_name} ({file_size_mb:.2f} MB)")
        else:
            logger.warning(f"⚠️ Документы не найдены для дела: {case_number}")
        
        # Обновляем статус
        parsing_status.update({
            "is_parsing": False,
            "current_case": "",
            "progress": f"Парсинг завершен. Скачано файлов: {len(downloaded_files)}",
            "start_time": None,
            "files_count": len(downloaded_files)
        })
        
        # Добавляем в историю
        history_entry = {
            "case_number": case_number,
            "success": True,
            "files_count": len(downloaded_files),
            "processing_time": processing_time,
            "timestamp": datetime.now().isoformat()
        }
        parsing_history.append(history_entry)
        
        # Ограничиваем размер истории
        if len(parsing_history) > max_history:
            parsing_history.pop(0)
        
        logger.info(f"✅ Парсинг завершен: {len(downloaded_files)} файлов за {processing_time:.2f}с")
        if len(downloaded_files) > 0:
            logger.info(f"⏱️ Средняя скорость: {len(downloaded_files)/processing_time:.2f} файлов/сек")
        logger.info(f"💾 Файлы сохранены в папку: files/")
        
    except Exception as e:
        processing_time = time.time() - start_time
        
        # Детальное логирование ошибки
        logger.error(f"❌ Ошибка парсинга дела {case_number}: {e}")
        logger.error(f"🔍 Тип ошибки: {type(e).__name__}")
        logger.error(f"⏱️ Время до ошибки: {processing_time:.2f}с")
        
        # Обновляем статус при ошибке
        parsing_status.update({
            "is_parsing": False,
            "current_case": "",
            "progress": f"Ошибка: {str(e)}",
            "start_time": None,
            "files_count": 0
        })
        
        # Добавляем ошибку в историю
        history_entry = {
            "case_number": case_number,
            "success": False,
            "files_count": 0,
            "processing_time": processing_time,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        parsing_history.append(history_entry)
        
        if len(parsing_history) > max_history:
            parsing_history.pop(0)
        
        logger.error(f"📝 Ошибка записана в историю парсинга")

# API эндпоинты

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Главная страница с формой"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "status": parsing_status
    })

@app.post("/api/parse")
async def parse_case(request: ParseRequest):
    """API эндпоинт для парсинга дела"""
    case_number = request.case_number.strip()
    
    if not case_number:
        raise HTTPException(status_code=400, detail="Номер дела не может быть пустым")
    
    # Проверяем, не выполняется ли уже парсинг
    if parsing_status["is_parsing"]:
        raise HTTPException(
            status_code=429, 
            detail="Парсинг уже выполняется. Пожалуйста, подождите."
        )
    
    # Добавляем в очередь
    parsing_queue.put(case_number)
    
    return JSONResponse({
        "success": True,
        "message": "Запрос добавлен в очередь парсинга",
        "case_number": case_number,
        "queue_position": parsing_queue.qsize()
    })

@app.get("/api/status", response_model=StatusResponse)
async def get_status():
    """Получение текущего статуса парсинга"""
    return StatusResponse(
        is_parsing=parsing_status["is_parsing"],
        current_case=parsing_status["current_case"],
        progress=parsing_status["progress"],
        start_time=parsing_status["start_time"],
        files_count=parsing_status["files_count"],
        queue_size=parsing_queue.qsize()
    )

@app.get("/api/files")
async def list_files():
    """Список доступных файлов"""
    try:
        files_dir = "files"
        if not os.path.exists(files_dir):
            return {"files": []}
        
        files = []
        for filename in os.listdir(files_dir):
            file_path = os.path.join(files_dir, filename)
            if os.path.isfile(file_path):
                stat = os.stat(file_path)
                files.append({
                    "name": filename,
                    "size": stat.st_size,
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
        
        # Сортируем по дате создания (новые сначала)
        files.sort(key=lambda x: x["created"], reverse=True)
        
        return {"files": files}
        
    except Exception as e:
        logger.error(f"❌ Ошибка получения списка файлов: {e}")
        return {"files": []}

@app.get("/api/download/{filename}")
async def download_file(filename: str):
    """Скачивание файла"""
    try:
        file_path = os.path.join("files", filename)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Файл не найден")
        
        if not os.path.isfile(file_path):
            raise HTTPException(status_code=404, detail="Указанный путь не является файлом")
        
        # Проверяем безопасность пути
        real_path = os.path.realpath(file_path)
        real_files_dir = os.path.realpath("files")
        
        if not real_path.startswith(real_files_dir):
            raise HTTPException(status_code=403, detail="Доступ к файлу запрещен")
        
        def iterfile():
            with open(file_path, mode="rb") as file_like:
                yield from file_like
        
        return StreamingResponse(
            iterfile(),
            media_type='application/pdf',
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка скачивания файла {filename}: {e}")
        raise HTTPException(status_code=500, detail="Ошибка скачивания файла")

@app.post("/api/clear")
async def clear_files():
    """Очистка папки files"""
    if parsing_status["is_parsing"]:
        raise HTTPException(
            status_code=429, 
            detail="Нельзя очистить файлы во время парсинга"
        )
    
    try:
        files_dir = "files"
        if os.path.exists(files_dir):
            shutil.rmtree(files_dir)
        os.makedirs(files_dir)
        
        logger.info("🗑️ Папка files очищена через API")
        return {"success": True, "message": "Файлы успешно удалены"}
        
    except Exception as e:
        logger.error(f"❌ Ошибка очистки файлов: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка очистки файлов: {str(e)}")

@app.get("/api/history")
async def get_parsing_history():
    """Получение истории парсинга"""
    return {"history": parsing_history}

@app.get("/api/health")
async def health_check():
    """Проверка состояния сервиса"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "parser_available": parser is not None,
        "queue_size": parsing_queue.qsize(),
        "is_parsing": parsing_status["is_parsing"]
    }

@app.get("/diagnostics", response_class=HTMLResponse)
async def diagnostics_page(request: Request):
    """Страница диагностики"""
    diagnostics_info = {
        "python_version": "",
        "selenium_version": "",
        "parser_status": "Не инициализирован",
        "files_count": 0,
        "queue_size": parsing_queue.qsize(),
        "history_count": len(parsing_history)
    }
    
    try:
        import sys
        diagnostics_info["python_version"] = sys.version
        
        try:
            import selenium
            diagnostics_info["selenium_version"] = selenium.__version__
        except:
            diagnostics_info["selenium_version"] = "Не найден"
        
        if parser:
            diagnostics_info["parser_status"] = "Инициализирован"
        
        files_dir = "files"
        if os.path.exists(files_dir):
            diagnostics_info["files_count"] = len([
                f for f in os.listdir(files_dir) 
                if os.path.isfile(os.path.join(files_dir, f))
            ])
        
    except Exception as e:
        logger.error(f"❌ Ошибка сбора диагностики: {e}")
    
    return templates.TemplateResponse("diagnostics.html", {
        "request": request,
        "diagnostics": diagnostics_info,
        "status": parsing_status
    })

def signal_handler(signum, frame):
    """Обработчик сигналов для корректного завершения"""
    print(f"\n🛑 Получен сигнал {signum} (Ctrl+C), завершение работы...")
    logger.info(f"🛑 Получен сигнал {signum}, завершение работы...")
    
    # Устанавливаем флаг завершения
    shutdown_event.set()
    
    # Закрываем парсер если он есть
    if parser:
        try:
            print("📝 Закрытие парсера...")
            logger.info("📝 Закрытие парсера...")
            parser.close()
            print("✅ Парсер закрыт")
            logger.info("✅ Парсер закрыт")
        except Exception as e:
            print(f"⚠️ Ошибка при закрытии парсера: {e}")
            logger.warning(f"⚠️ Ошибка при закрытии парсера: {e}")
    
    print("📝 Завершение работы backend сервиса...")
    logger.info("📝 Завершение работы backend сервиса...")
    print("✅ Backend сервис остановлен")
    logger.info("✅ Backend сервис остановлен")
    print("👋 До свидания!")
    
    sys.exit(0)

if __name__ == "__main__":
    # Настройка обработчиков сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Создаем необходимые папки
    os.makedirs("files", exist_ok=True)
    os.makedirs("templates", exist_ok=True)
    
    print("🚀 Запуск backend сервиса парсера kad.arbitr.ru")
    print("📱 API доступен по адресу: http://127.0.0.1:8000")
    print("📋 Документация API: http://127.0.0.1:8000/docs")
    print("⏹️  Для остановки нажмите Ctrl+C")
    
    try:
        uvicorn.run(
            app, 
            host="127.0.0.1", 
            port=8000, 
            reload=False,
            log_level="info",
            access_log=True
        )
    except KeyboardInterrupt:
        print("\n🛑 Получен сигнал прерывания (Ctrl+C), завершение работы...")
        logger.info("🛑 Получен сигнал прерывания, завершение работы...")
        shutdown_event.set()
        
        # Закрываем парсер если он есть
        if parser:
            try:
                print("📝 Закрытие парсера...")
                logger.info("📝 Закрытие парсера...")
                parser.close()
                print("✅ Парсер закрыт")
                logger.info("✅ Парсер закрыт")
            except Exception as e:
                print(f"⚠️ Ошибка при закрытии парсера: {e}")
                logger.warning(f"⚠️ Ошибка при закрытии парсера: {e}")
        
        print("✅ Backend сервис остановлен")
        logger.info("✅ Backend сервис остановлен")
        print("👋 До свидания!")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        logger.error(f"❌ Критическая ошибка: {e}")
        sys.exit(1)
