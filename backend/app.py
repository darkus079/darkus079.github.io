import asyncio
import os
import logging
from contextlib import asynccontextmanager
from typing import List
import uvicorn    
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Form
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from parser_simplified import KadArbitrParser

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Глобальный экземпляр парсера
parser = None
# Семафор для ограничения одновременных запросов
parsing_semaphore = asyncio.Semaphore(1)
# Статус парсинга
parsing_status = {"is_parsing": False, "current_case": "", "progress": ""}
# Память для ссылок на документы по номеру дела
DOC_LINKS_STORE = {}

class ParseRequest(BaseModel):
    case_number: str

class ParseResponse(BaseModel):
    success: bool
    message: str
    files: List[str] = []

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    global parser, parsing_status
    
    # Сброс всех данных при запуске
    logger.info("🔄 Сброс всех данных при запуске...")
    parsing_status = {"is_parsing": False, "current_case": "", "progress": ""}
    
    # Очистка папки files
    if os.path.exists(FILES_DIR):
        try:
            for filename in os.listdir(FILES_DIR):
                file_path = os.path.join(FILES_DIR, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            logger.info("✅ Папка files очищена")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось очистить папку files: {e}")
    else:
        # Создаем папку files если её нет
        try:
            os.makedirs(FILES_DIR, exist_ok=True)
            logger.info("✅ Папка files создана")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось создать папку files: {e}")
    
    # Инициализация при запуске
    logger.info("Инициализация парсера...")
    parser = KadArbitrParser()
    
    # WebDriver НЕ инициализируем при запуске - он создается в каждом запросе
    logger.info("Парсер создан, WebDriver будет создан и закрыт в каждом запросе")
    
    yield
    
    # Очистка при завершении
    logger.info("Завершение работы парсера...")
    # WebDriver больше не хранится глобально - каждый запрос создает и закрывает свой
    logger.info("Парсер закрыт")

# Создание приложения FastAPI
app = FastAPI(
    title="Парсер kad.arbitr.ru",
    description="Парсер для скачивания PDF файлов из арбитражных дел",
    version="1.0.0",
    lifespan=lifespan
)

# Определяем абсолютный путь к папке files
FILES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "files")

# Подключение статических файлов и шаблонов
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Главная страница с формой"""
    return templates.TemplateResponse("index.html", {
        "request": request,
        "status": parsing_status
    })

@app.post("/parse")
async def parse_case(request: Request, case_number: str = Form(...)):
    """Парсинг дела по номеру"""
    # ЖЕСТКАЯ ПРОВЕРКА: не выполняется ли уже парсинг
    if parsing_status["is_parsing"]:
        logger.error("🛑 ПАРСИНГ УЖЕ ВЫПОЛНЯЕТСЯ! Запрос заблокирован!")
        raise HTTPException(status_code=429, detail="Парсинг уже выполняется. Пожалуйста, подождите.")
    
    # ДОПОЛНИТЕЛЬНАЯ ПРОВЕРКА: флаг в парсере
    if parser.is_processing:
        logger.error("🛑 ПАРСЕР ЗАНЯТ! Запрос заблокирован!")
        raise HTTPException(status_code=429, detail="Парсер занят. Пожалуйста, подождите.")
    
    if not case_number.strip():
        raise HTTPException(status_code=400, detail="Номер дела не может быть пустым")
    
    try:
        async with parsing_semaphore:
            # Обновляем статус
            parsing_status["is_parsing"] = True
            parsing_status["current_case"] = case_number.strip()
            parsing_status["progress"] = "Начинаем парсинг..."
            
            logger.info(f"Начало парсинга дела: {case_number}")
            
            # Выполняем парсинг в отдельном потоке
            loop = asyncio.get_event_loop()
            
            try:
                # Обновляем прогресс
                parsing_status["progress"] = "Поиск дела на сайте..."
                
                # Новая логика: собираем ссылки вместо скачивания
                collected_links = await loop.run_in_executor(
                    None,
                    parser.collect_document_links,
                    case_number.strip()
                )
                
                parsing_status["progress"] = f"Парсинг завершен. Найдено документов: {len(collected_links)}"
                
                # Формируем ответ
                if collected_links:
                    # Отладочная информация
                    # Сохраняем в память по номеру дела
                    DOC_LINKS_STORE[case_number.strip()] = collected_links
                    logger.info(f"🔗 Сохранено ссылок для {case_number}: {len(collected_links)}")
                    
                    response_data = {
                        "success": True,
                        "message": f"Найдено документов: {len(collected_links)}",
                        "files": [],
                        "links": collected_links,
                        "case_number": case_number.strip()
                    }
                    logger.info(f"Парсинг завершен успешно: найдено документов {len(collected_links)}")
                else:
                    response_data = {
                        "success": False,
                        "message": "Дела не найдены или документы недоступны",
                        "files": [],
                        "links": [],
                        "case_number": case_number.strip()
                    }
                    logger.warning("Парсинг завершен без результатов")
                
                # Возвращаем HTML ответ с результатами
                return templates.TemplateResponse("result.html", {
                    "request": request,
                    "result": response_data,
                    "status": parsing_status
                })
                
            except Exception as e:
                logger.error(f"Ошибка парсинга: {e}")
                parsing_status["progress"] = f"Ошибка: {str(e)}"
                
                error_response = {
                    "success": False,
                    "message": f"Ошибка парсинга: {str(e)}",
                    "files": [],
                    "case_number": case_number.strip()
                }
                
                return templates.TemplateResponse("result.html", {
                    "request": request,
                    "result": error_response,
                    "status": parsing_status
                })
                
    finally:
        # Сбрасываем статус
        parsing_status["is_parsing"] = False
        parsing_status["current_case"] = ""
        # Сбрасываем флаг парсера
        parser.is_processing = False
        logger.info("🔄 Флаги сброшены - парсер готов к новому запросу")

@app.get("/api/parse/{case_number}")
async def api_parse_case(case_number: str):
    """API эндпоинт для парсинга (JSON ответ)"""
    if parsing_status["is_parsing"]:
        raise HTTPException(status_code=429, detail="Парсер уже выполняет задачу. Дождитесь завершения.")
    
    if not case_number.strip():
        raise HTTPException(status_code=400, detail="Номер дела не может быть пустым")
    
    try:
        async with parsing_semaphore:
            parsing_status["is_parsing"] = True
            parsing_status["current_case"] = case_number.strip()
            parsing_status["progress"] = "Начинаем парсинг..."
            
            logger.info(f"API парсинг дела: {case_number}")
            
            loop = asyncio.get_event_loop()
            
            parsing_status["progress"] = "Поиск дела на сайте..."
            
            collected_links = await loop.run_in_executor(
                None,
                parser.collect_document_links,
                case_number.strip()
            )
            
            parsing_status["progress"] = f"Парсинг завершен. Найдено документов: {len(collected_links)}"
            
            if collected_links:
                DOC_LINKS_STORE[case_number.strip()] = collected_links
                logger.info(f"API парсинг завершен успешно: найдено документов {len(collected_links)}")
                return JSONResponse(
                    content={
                        "success": True,
                        "message": f"Найдено документов: {len(collected_links)}",
                        "links": collected_links
                    }
                )
            else:
                logger.warning("API парсинг завершен без результатов")
                return JSONResponse(
                    content={
                        "success": False,
                        "message": "Дела не найдены или документы недоступны",
                        "links": []
                    }
                )
                
    except Exception as e:
        logger.error(f"Ошибка API парсинга: {e}")
        parsing_status["progress"] = f"Ошибка: {str(e)}"
        raise HTTPException(status_code=500, detail=f"Ошибка парсинга: {str(e)}")
        
    finally:
        parsing_status["is_parsing"] = False
        parsing_status["current_case"] = ""

@app.get("/status")
async def get_status():
    """Получение текущего статуса парсинга"""
    return parsing_status

@app.get("/files", response_class=HTMLResponse)
async def files_page(request: Request):
    """Страница со списком файлов"""
    return templates.TemplateResponse("files.html", {"request": request})

@app.get("/api/files")
async def list_files():
    """API эндпоинт - список доступных файлов (устаревший, сохранен для совместимости)."""
    file_names = []
    if os.path.exists(FILES_DIR):
        try:
            for filename in os.listdir(FILES_DIR):
                file_path = os.path.join(FILES_DIR, filename)
                if os.path.isfile(file_path):
                    file_names.append(filename)
            logger.info(f"📁 Найдено файлов в {FILES_DIR}: {len(file_names)}")
        except Exception as e:
            logger.error(f"Ошибка чтения папки files: {e}")
    else:
        logger.warning(f"Папка files не существует: {FILES_DIR}")
    return {"files": file_names}

@app.get("/api/doc-links")
async def get_doc_links(case: str):
    """Возвращает собранные ссылки на документы для указанного номера дела."""
    links = DOC_LINKS_STORE.get(case.strip(), [])
    return {"case": case.strip(), "links": links}

@app.get("/api/download/{filename}")
async def api_download_file(filename: str):
    """API эндпоинт для скачивания файла"""
    import urllib.parse
    
    # Декодируем URL-encoded имя файла
    decoded_filename = urllib.parse.unquote(filename)
    file_path = os.path.join(FILES_DIR, decoded_filename)
    
    logger.info(f"🔍 Поиск файла: {decoded_filename}")
    logger.info(f"📁 Путь к файлу: {file_path}")
    logger.info(f"📁 Папка files: {FILES_DIR}")
    
    if not os.path.exists(file_path):
        logger.error(f"❌ Файл не найден: {file_path}")
        raise HTTPException(status_code=404, detail="Файл не найден")
    
    if not os.path.isfile(file_path):
        logger.error(f"❌ Путь не является файлом: {file_path}")
        raise HTTPException(status_code=404, detail="Указанный путь не является файлом")
    
    # Проверяем, что файл находится в папке files (безопасность)
    real_path = os.path.realpath(file_path)
    real_files_dir = os.path.realpath(FILES_DIR)
    
    if not real_path.startswith(real_files_dir):
        logger.error(f"❌ Доступ к файлу запрещен: {real_path} не в {real_files_dir}")
        raise HTTPException(status_code=403, detail="Доступ к файлу запрещен")
    
    logger.info(f"✅ Файл найден и готов к скачиванию: {decoded_filename}")
    
    # Создаем безопасное имя файла для заголовка Content-Disposition
    # Заменяем кириллические символы на латинские аналоги
    safe_filename = decoded_filename
    cyrillic_to_latin = {
        'А': 'A', 'В': 'B', 'Е': 'E', 'К': 'K', 'М': 'M', 'Н': 'H', 'О': 'O', 
        'Р': 'P', 'С': 'C', 'Т': 'T', 'У': 'Y', 'Х': 'X', 'а': 'a', 'в': 'b', 
        'е': 'e', 'к': 'k', 'м': 'm', 'н': 'h', 'о': 'o', 'р': 'p', 'с': 'c', 
        'т': 't', 'у': 'y', 'х': 'x'
    }
    
    for cyr, lat in cyrillic_to_latin.items():
        safe_filename = safe_filename.replace(cyr, lat)
    
    return FileResponse(
        path=file_path,
        filename=safe_filename,
        media_type='application/pdf',
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{urllib.parse.quote(decoded_filename)}"
        }
    )

@app.get("/download/{filename}")
async def download_file(filename: str):
    """Скачивание файла (устаревший эндпоинт, используйте /api/download/{filename})"""
    import urllib.parse
    
    # Декодируем URL-encoded имя файла
    decoded_filename = urllib.parse.unquote(filename)
    file_path = os.path.join(FILES_DIR, decoded_filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Файл не найден")
    
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Указанный путь не является файлом")
    
    # Проверяем, что файл находится в папке files (безопасность)
    real_path = os.path.realpath(file_path)
    real_files_dir = os.path.realpath(FILES_DIR)
    
    if not real_path.startswith(real_files_dir):
        raise HTTPException(status_code=403, detail="Доступ к файлу запрещен")
    
    # Создаем безопасное имя файла для заголовка Content-Disposition
    safe_filename = decoded_filename
    cyrillic_to_latin = {
        'А': 'A', 'В': 'B', 'Е': 'E', 'К': 'K', 'М': 'M', 'Н': 'H', 'О': 'O', 
        'Р': 'P', 'С': 'C', 'Т': 'T', 'У': 'Y', 'Х': 'X', 'а': 'a', 'в': 'b', 
        'е': 'e', 'к': 'k', 'м': 'm', 'н': 'h', 'о': 'o', 'р': 'p', 'с': 'c', 
        'т': 't', 'у': 'y', 'х': 'x'
    }
    
    for cyr, lat in cyrillic_to_latin.items():
        safe_filename = safe_filename.replace(cyr, lat)
    
    return FileResponse(
        path=file_path,
        filename=safe_filename,
        media_type='application/pdf',
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{urllib.parse.quote(decoded_filename)}"
        }
    )

@app.get("/clear")
async def clear_files():
    """Очистка папки files"""
    if parsing_status["is_parsing"]:
        raise HTTPException(status_code=429, detail="Нельзя очистить файлы во время парсинга")
    
    try:
        if os.path.exists(FILES_DIR):
            for filename in os.listdir(FILES_DIR):
                file_path = os.path.join(FILES_DIR, filename)
                if os.path.isfile(file_path):
                    os.remove(file_path)
            logger.info(f"Папка files очищена через веб-интерфейс: {FILES_DIR}")
            return {"message": "Файлы успешно удалены"}
        else:
            logger.warning(f"Папка files не существует: {FILES_DIR}")
            return {"message": "Папка files не существует"}
    except Exception as e:
        logger.error(f"Ошибка очистки файлов: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка очистки файлов: {str(e)}")

@app.get("/reinit-driver")
async def reinit_driver():
    """Переинициализация WebDriver"""
    global parser
    
    if parsing_status["is_parsing"]:
        raise HTTPException(status_code=429, detail="Нельзя переинициализировать драйвер во время парсинга")
    
    try:
        logger.info("Переинициализация WebDriver по запросу пользователя")
        
        # Закрываем старый драйвер если есть
        if parser and parser.driver:
            parser.close()
        
        # Создаем новый парсер
        parser = KadArbitrParser()
        
        # Пытаемся инициализировать WebDriver
        if parser.init_driver():
            logger.info("WebDriver успешно переинициализирован")
            return {"success": True, "message": "WebDriver успешно переинициализирован"}
        else:
            logger.error("Не удалось переинициализировать WebDriver")
            return {"success": False, "message": "Не удалось переинициализировать WebDriver"}
            
    except Exception as e:
        logger.error(f"Ошибка переинициализации WebDriver: {e}")
        return {"success": False, "message": f"Ошибка переинициализации: {str(e)}"}

@app.get("/diagnostics", response_class=HTMLResponse)
async def diagnostics_page(request: Request):
    """Страница диагностики проблем"""
    
    # Собираем диагностическую информацию
    diagnostics_info = {
        "chrome_paths": [],
        "chromedriver_paths": [],
        "python_version": "",
        "selenium_version": "",
        "undetected_available": False,
        "webdriver_manager_cache": [],
        "driver_status": "Не инициализирован"
    }
    
    try:
        # Python версия
        import sys
        diagnostics_info["python_version"] = sys.version
        
        # Selenium версия
        try:
            import selenium
            diagnostics_info["selenium_version"] = selenium.__version__
        except:
            diagnostics_info["selenium_version"] = "Не найден"
        
        # Проверка undetected-chromedriver
        try:
            import undetected_chromedriver
            diagnostics_info["undetected_available"] = True
        except ImportError:
            diagnostics_info["undetected_available"] = False
        
        # Статус драйвера
        if parser and parser.driver:
            diagnostics_info["driver_status"] = "Инициализирован"
        else:
            diagnostics_info["driver_status"] = "Не инициализирован"
        
        # Поиск Chrome
        import subprocess
        import platform
        
        if platform.system() == "Windows":
            try:
                result = subprocess.run(['where', 'chrome'], capture_output=True, text=True)
                if result.returncode == 0:
                    diagnostics_info["chrome_paths"] = result.stdout.strip().split('\n')
            except:
                pass
        else:
            try:
                result = subprocess.run(['which', 'google-chrome'], capture_output=True, text=True)
                if result.returncode == 0:
                    diagnostics_info["chrome_paths"].append(result.stdout.strip())
            except:
                pass
        
        # Кэш WebDriverManager
        import os
        cache_dirs = [
            os.path.expanduser("~/.wdm"),
            os.path.join(os.path.expanduser("~"), "AppData", "Local", ".wdm")
        ]
        
        for cache_dir in cache_dirs:
            if os.path.exists(cache_dir):
                try:
                    for root, dirs, files in os.walk(cache_dir):
                        for file in files:
                            if 'chromedriver' in file.lower():
                                diagnostics_info["webdriver_manager_cache"].append(os.path.join(root, file))
                except:
                    pass
        
    except Exception as e:
        logger.error(f"Ошибка сбора диагностики: {e}")
    
    return templates.TemplateResponse("diagnostics.html", {
        "request": request,
        "diagnostics": diagnostics_info,
        "status": parsing_status
    })

if __name__ == "__main__":
    # Создаем папку templates если её нет
    templates_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
    if not os.path.exists(templates_dir):
        os.makedirs(templates_dir)
    
    # Создаем папку files если её нет  
    if not os.path.exists(FILES_DIR):
        os.makedirs(FILES_DIR)
    
    print("🚀 Запуск парсера kad.arbitr.ru с веб-интерфейсом")
    print("📱 Откройте браузер: http://localhost:8000")
    print("⏹️  Для остановки нажмите Ctrl+C")
    
    uvicorn.run(
        "app:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="info"
    )
