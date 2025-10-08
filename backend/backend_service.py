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
# Хранилище ссылок по номеру дела
LINKS_STORE: Dict[str, List[Dict[str, Any]]] = {}
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
    start_time: str = ""
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
        "progress": "Готов к работе",
        "start_time": "",
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
        
        logger.info(f"🔄 Начало сбора ссылок по делу: {case_number}")
        logger.info(f"🔍 Поиск дела в базе kad.arbitr.ru...")
        
        # Выполняем парсинг в отдельном потоке
        loop = asyncio.get_event_loop()
        
        def progress_callback(progress_text):
            # Обновляем статус с детальной информацией
            current_time = datetime.now().strftime("%H:%M:%S")
            elapsed_time = time.time() - start_time
            parsing_status["progress"] = f"[{current_time}] {progress_text}"
            parsing_status["files_count"] = len([f for f in os.listdir("files") if f.endswith('.pdf')]) if os.path.exists("files") else 0
            
            # Логируем с дополнительной информацией
            logger.info(f"📊 [{current_time}] {progress_text}")
            logger.info(f"⏱️ Время выполнения: {elapsed_time:.1f}с")
            logger.info(f"📁 Обработано файлов: {parsing_status['files_count']}")
        
        # Добавляем дополнительное логирование перед парсингом
        logger.info(f"🌐 Открытие браузера для парсинга...")
        logger.info(f"📋 Переход на сайт kad.arbitr.ru...")
        
        # Сбор ссылок на PDF без скачивания
        collected_links: List[Dict[str, Any]] = await loop.run_in_executor(
            None,
            parser.collect_document_links,
            case_number.strip()
        )
        
        processing_time = time.time() - start_time
        
        # Фильтруем только PDF и сохраняем в память
        safe_links = []
        if collected_links:
            for link in collected_links:
                try:
                    url = (link or {}).get("url", "")
                    if not url or ".pdf" not in url.lower():
                        continue
                    safe_links.append({
                        "name": (link or {}).get("name") or "Document",
                        "url": url,
                        "date": (link or {}).get("date"),
                        "type": (link or {}).get("type") or "PDF",
                        "note": (link or {}).get("note") or "",
                        "source": (link or {}).get("source") or "kad.arbitr.ru"
                    })
                except Exception:
                    continue
            LINKS_STORE[case_number] = safe_links
            logger.info(f"🔗 Сохранено ссылок: {len(safe_links)} для дела {case_number}")
        else:
            logger.warning(f"⚠️ Ссылки не найдены для дела: {case_number}")
        
        # Обновляем статус
        parsing_status.update({
            "is_parsing": False,
            "current_case": "",
            "progress": f"Сбор ссылок завершен. Найдено ссылок: {len(LINKS_STORE.get(case_number, []))}",
            "start_time": "",
            "files_count": len(LINKS_STORE.get(case_number, []))
        })
        
        # Добавляем в историю
        history_entry = {
            "case_number": case_number,
            "success": True,
            "links_count": len(LINKS_STORE.get(case_number, [])),
            "processing_time": processing_time,
            "timestamp": datetime.now().isoformat()
        }
        parsing_history.append(history_entry)
        
        # Ограничиваем размер истории
        if len(parsing_history) > max_history:
            parsing_history.pop(0)
        
        logger.info(f"✅ Сбор ссылок завершен: {len(LINKS_STORE.get(case_number, []))} ссылок за {processing_time:.2f}с")
        
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
            "start_time": "",
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
        "message": "Запрос добавлен в очередь сбора ссылок",
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
    """Эндпоинт удален в режиме только ссылок"""
    raise HTTPException(status_code=404, detail="Эндпоинт удален: используйте /api/links?case=...")

@app.get("/api/download/{filename}")
async def download_file(filename: str):
    """Эндпоинт удален в режиме только ссылок"""
    raise HTTPException(status_code=404, detail="Эндпоинт удален: скачивание отключено")

@app.post("/api/clear")
async def clear_files():
    """Эндпоинт удален в режиме только ссылок"""
    raise HTTPException(status_code=404, detail="Эндпоинт удален: скачивание отключено")

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

# Новые эндпоинты для ссылок
@app.get("/api/links")
async def get_links(case: str):
    """Возвращает собранные ссылки на PDF по номеру дела"""
    case_key = (case or "").strip()
    if not case_key:
        raise HTTPException(status_code=400, detail="Не указан номер дела")
    return {"case": case_key, "links": LINKS_STORE.get(case_key, [])}

@app.get("/api/cases")
async def get_cases():
    """Список дел, по которым есть собранные ссылки"""
    return {"cases": list(LINKS_STORE.keys())}

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
    print("📱 API доступен по адресу: http://0.0.0.0:8000")
    print("📋 Документация API: http://0.0.0.0:8000/docs")
    print("⏹️  Для остановки нажмите Ctrl+C")
    
    try:
        uvicorn.run(
            app, 
            host="0.0.0.0", 
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
