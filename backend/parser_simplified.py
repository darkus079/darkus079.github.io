import os
import time
import logging
import requests
import shutil
import random
import re
import json
import signal
import sys
import threading
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
import urllib3
import undetected_chromedriver as uc
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import shutil
import platform
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import tempfile
import glob
# from pdf_extraction_algorithms import PDFExtractionAlgorithms  # УДАЛЕНО - больше не используем сложные алгоритмы
from selenium_config import (
    create_undetected_chrome_options, 
    create_standard_chrome_options, 
    get_downloads_directory,
    move_downloaded_files
)

UC_AVAILABLE = True

# Отключаем предупреждения urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s', 
    encoding='utf-8'
)
logger = logging.getLogger(__name__)

class KadArbitrParser:
    def __init__(self):
        self.driver = None
        # Используем абсолютный путь к папке files в backend
        self.files_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "files")
        self.downloads_dir = self._get_downloads_directory()
        self.is_processing = False  # Флаг для предотвращения повторных запусков
        self._force_stop = False  # Флаг принудительной остановки
        self.headless = False  # Режим без окна (для VM)
        self._profile_dir = None  # Уникальная папка профиля Chrome
        self._ensure_files_directory()
        self._signal_handlers_setup = False
        logger.info(f"📁 Папка для скачивания: {self.downloads_dir}")
        logger.info(f"📁 Папка для сохранения: {os.path.abspath(self.files_dir)}")
    
    def _get_downloads_directory(self):
        """Получает путь к папке Загрузки"""
        try:
            # Для Windows
            if platform.system() == "Windows":
                downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
                if os.path.exists(downloads_path):
                    return downloads_path
                # Альтернативный путь
                downloads_path = os.path.join(os.path.expanduser("~"), "Загрузки")
                if os.path.exists(downloads_path):
                    return downloads_path
            # Для Linux/Mac
            else:
                downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
                if os.path.exists(downloads_path):
                    return downloads_path
            
            # Если не найдена, используем текущую папку
            logger.warning("⚠️ Папка Загрузки не найдена, используем текущую папку")
            return os.getcwd()
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка получения пути к Загрузкам: {e}")
            return os.getcwd()
    
    def _ensure_files_directory(self):
        """Создает папку files если её нет"""
        if not os.path.exists(self.files_dir):
            os.makedirs(self.files_dir)
            logger.info(f"Создана папка {self.files_dir}")
    
    def _setup_signal_handlers(self):
        """Настраивает обработчики сигналов для корректного завершения"""
        # Проверяем, что мы в главном потоке
        if threading.current_thread() is not threading.main_thread():
            logger.debug("⚠️ Обработчики сигналов не установлены - не главный поток")
            return
        
        if self._signal_handlers_setup:
            return
            
        def signal_handler(signum, frame):
            logger.info("🛑 ПРИНУДИТЕЛЬНОЕ ЗАВЕРШЕНИЕ (Ctrl+C)")
            logger.info("🔄 НЕМЕДЛЕННОЕ ОСТАНОВКА ВСЕХ ПРОЦЕССОВ...")
            
            # СРАЗУ сбрасываем флаг обработки для прерывания всех задержек
            self.is_processing = False
            
            # Устанавливаем флаг принудительной остановки
            self._force_stop = True
            
            # Принудительно закрываем WebDriver
            if self.driver:
                try:
                    self.driver.quit()
                    logger.info("✅ WebDriver принудительно закрыт")
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка при закрытии WebDriver: {e}")
            
            # Принудительно завершаем процесс
            logger.info("🏁 ПРИНУДИТЕЛЬНОЕ ЗАВЕРШЕНИЕ ПАРСЕРА")
            os._exit(0)  # Принудительное завершение без очистки
        
        try:
            # Регистрируем обработчики сигналов
            signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
            signal.signal(signal.SIGTERM, signal_handler)  # Сигнал завершения
            self._signal_handlers_setup = True
            logger.debug("✅ Обработчики сигналов установлены")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось установить обработчики сигналов: {e}")
    
    def cleanup_files_directory(self):
        """Очищает папку files"""
        if os.path.exists(self.files_dir):
            shutil.rmtree(self.files_dir)
        os.makedirs(self.files_dir)
        logger.info("Папка files очищена")
    
    def init_driver(self):
        """Инициализирует WebDriver с несколькими fallback вариантами"""
        
        # Список методов инициализации в порядке приоритета
        init_methods = [
            ("undetected-chromedriver", self._init_undetected_driver),
            ("Chrome с WebDriverManager", self._init_chrome_webdriver_manager),
            ("Chrome с очисткой кэша", self._init_chrome_clean_cache), 
            ("Chrome системный", self._init_chrome_system),
            ("Chrome минимальный", self._init_chrome_minimal)
        ]
        
        for method_name, method_func in init_methods:
            try:
                logger.info(f"Попытка инициализации: {method_name}")
                if method_func():
                    logger.info(f"✅ WebDriver успешно инициализирован методом: {method_name}")
                    return True
                else:
                    logger.warning(f"❌ Метод {method_name} не сработал")
            except Exception as e:
                logger.warning(f"❌ Ошибка метода {method_name}: {e}")
                continue
        
        logger.error("❌ Все методы инициализации WebDriver не сработали")
        return False
    
    def _init_undetected_driver(self):
        """Инициализация с undetected-chromedriver и максимальным обходом защиты"""
        if not UC_AVAILABLE:
            logger.warning("⚠️ undetected-chromedriver недоступен, пропускаем этот метод")
            return False
            
        try:
            logger.info("🤖 Настройка максимально человекоподобного браузера с автоматическим скачиванием PDF...")
            
            # Используем новые настройки для автоматического скачивания PDF
            options = create_undetected_chrome_options()
            # Безопасные настройки для Linux headless и уникального профиля
            self._apply_linux_headless_and_profile(options)
            
            # Создаем драйвер
            self.driver = uc.Chrome(options=options, version_main=None)
            
            # Дополнительные настройки после создания
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.6843.82 Safari/537.36'
            })
            
            # Устанавливаем реалистичные параметры экрана
            self.driver.execute_cdp_cmd('Emulation.setDeviceMetricsOverride', {
                'mobile': False,
                'width': 1920,
                'height': 1080,
                'deviceScaleFactor': 1,
            })
            
            # Маскируем автоматизацию
            self.driver.execute_script("""
                // Удаляем следы автоматизации
                delete navigator.__proto__.webdriver;
                
                // Маскируем Chrome runtime
                window.chrome = {
                    runtime: {},
                    loadTimes: function() {},
                    csi: function() {},
                    app: {}
                };
                
                // Добавляем реалистичные свойства
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['ru-RU', 'ru', 'en-US', 'en']
                });
                
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5] // Имитируем плагины
                });
            """)
            
            logger.info("✅ Максимально человекоподобный браузер с автоматическим скачиванием PDF настроен")
            return True
            
        except ImportError:
            logger.info("undetected-chromedriver не установлен")
            return False
        except Exception as e:
            logger.warning(f"Ошибка настройки человекоподобного браузера: {e}")
            return False
    
    def _init_chrome_webdriver_manager(self):
        """Стандартная инициализация с WebDriverManager и антидетект настройками"""
        try:            
            logger.info("🌐 Настройка обычного Chrome с антидетект функциями и автоматическим скачиванием PDF...")
            
            # Используем новые настройки для автоматического скачивания PDF
            options = create_standard_chrome_options()
            # Безопасные настройки для Linux headless и уникального профиля
            self._apply_linux_headless_and_profile(options)
            
            # Получаем путь к драйверу
            driver_path = ChromeDriverManager().install()
            logger.info(f"Путь к драйверу: {driver_path}")
            
            # Подробная проверка файла драйвера
            validated_path = self._validate_chromedriver(driver_path)
            if not validated_path:
                return False
            
            service = Service(validated_path)
            self.driver = webdriver.Chrome(service=service, options=options)
            
            # Дополнительные настройки после создания
            try:
                self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                    "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.6843.82 Safari/537.36'
                })
            except Exception as script_error:
                logger.debug(f"Не удалось выполнить дополнительные скрипты: {script_error}")
            
            logger.info("✅ Обычный Chrome с антидетект настройками и автоматическим скачиванием PDF готов")
            return True
            
        except Exception as e:
            logger.warning(f"Ошибка WebDriverManager: {e}")
            return False
    
    def _init_chrome_clean_cache(self):
        """Инициализация с очисткой кэша WebDriverManager"""
        try:
            try:
                system = platform.system().lower()
                
                cache_dirs = []
                if system == "windows":
                    # Windows - основные пути кэша WebDriverManager
                    cache_dirs = [
                        os.path.expanduser("~/.wdm"),
                        os.path.join(os.path.expanduser("~"), ".wdm"),
                        os.path.join(os.path.expanduser("~"), "AppData", "Local", ".wdm"),
                        os.path.join(os.getenv("USERPROFILE", ""), ".wdm")
                    ]
                else:
                    # Linux/Mac
                    cache_dirs = [
                        os.path.expanduser("~/.wdm"),
                        os.path.join(os.path.expanduser("~"), ".cache", "wdm")
                    ]
                
                for cache_dir in cache_dirs:
                    if cache_dir and os.path.exists(cache_dir):
                        shutil.rmtree(cache_dir)
                        logger.info(f"Кэш WebDriverManager очищен: {cache_dir}")
                        
            except Exception as cache_error:
                logger.warning(f"Не удалось очистить кэш: {cache_error}")
            
            logger.info("🌐 Настройка Chrome с очисткой кэша и антидетект функциями...")
            
            options = Options()
            
            # Основные антидетект настройки
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            # Экспериментальные опции оставляем только на Windows
            if platform.system().lower() == 'windows':
                options.add_experimental_option("excludeSwitches", ["enable-automation"])
                options.add_experimental_option('useAutomationExtension', False)
            
            # Настройки окна и производительности
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--disable-gpu')

            # Безопасные настройки для Linux headless и уникального профиля
            self._apply_linux_headless_and_profile(options)
            
            # Человекоподобные предпочтения
            prefs = {
                "profile.default_content_setting_values.notifications": 2,
                "profile.default_content_settings.popups": 0,
                "credentials_enable_service": False,
                "profile.password_manager_enabled": False,
                "intl.accept_languages": "ru-RU,ru,en-US,en",
            }
            options.add_experimental_option("prefs", prefs)
            
            # Принудительно скачиваем новый драйвер
            driver_path = ChromeDriverManager().install()
            
            # Подробная проверка файла драйвера
            validated_path = self._validate_chromedriver(driver_path)
            if not validated_path:
                return False
                
            service = Service(validated_path)
            self.driver = webdriver.Chrome(service=service, options=options)
            
            # Дополнительные настройки после создания
            try:
                self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                    "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.6843.82 Safari/537.36'
                })
            except Exception as script_error:
                logger.debug(f"Не удалось выполнить дополнительные скрипты: {script_error}")
            
            logger.info("✅ Chrome с очисткой кэша готов")
            return True
                
        except Exception as e:
            logger.warning(f"Ошибка с очисткой кэша: {e}")
            return False
    
    def _init_chrome_system(self):
        """Инициализация с системным Chrome без WebDriverManager"""
        try:
            logger.info("🔧 Настройка системного Chrome с антидетект функциями...")
            
            options = Options()
            
            # Основные антидетект настройки
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            # Экспериментальные опции оставляем только на Windows
            if platform.system().lower() == 'windows':
                options.add_experimental_option("excludeSwitches", ["enable-automation"])
                options.add_experimental_option('useAutomationExtension', False)
            
            # Настройки окна
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--disable-gpu')

            # Безопасные настройки для Linux headless и уникального профиля
            self._apply_linux_headless_and_profile(options)
            
            # Человекоподобные предпочтения
            prefs = {
                "profile.default_content_setting_values.notifications": 2,
                "profile.default_content_settings.popups": 0,
                "credentials_enable_service": False,
                "profile.password_manager_enabled": False,
                "intl.accept_languages": "ru-RU,ru,en-US,en",
            }
            options.add_experimental_option("prefs", prefs)
            
            # Попытка использовать системный chromedriver
            self.driver = webdriver.Chrome(options=options)
            
            # Дополнительные настройки после создания
            try:
                self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            except Exception as script_error:
                logger.debug(f"Не удалось выполнить дополнительные скрипты: {script_error}")
            
            logger.info("✅ Системный Chrome готов")
            return True
            
        except Exception as e:
            logger.warning(f"Системный Chrome не найден: {e}")
            return False
    
    def _init_chrome_minimal(self):
        """Минимальная инициализация Chrome (последний шанс)"""
        try:
            logger.info("🚨 Попытка минимальной инициализации Chrome...")
            
            options = webdriver.ChromeOptions()
            
            # Минимальные настройки для работы
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-gpu')
            
            # Пробуем без headless режима сначала
            try:
                options.add_argument('--window-size=1280,720')
                self.driver = webdriver.Chrome(options=options)
                logger.info("✅ Минимальная инициализация успешна (с окном)")
                return True
            except:
                # Если не получилось, пробуем headless режим
                logger.warning("⚠️ Переходим на headless режим...")
                options.add_argument('--headless=new')
                options.add_argument('--window-size=1920,1080')
                self.driver = webdriver.Chrome(options=options)
                logger.warning("✅ Минимальная инициализация в headless режиме")
                self.headless = True
                return True
            
        except Exception as e:
            logger.error(f"❌ Минимальная инициализация не удалась: {e}")
            return False
    
    def _validate_chromedriver(self, driver_path):
        """Проверяет валидность файла chromedriver и возвращает путь к валидному файлу"""
        try:
            logger.info(f"Проверка файла chromedriver: {driver_path}")
            
            # Проверка существования файла
            if not os.path.exists(driver_path):
                logger.error(f"Файл драйвера не найден: {driver_path}")
                return None
            
            # Проверка размера файла (chromedriver должен быть больше 1MB)
            file_size = os.path.getsize(driver_path)
            logger.info(f"Размер файла драйвера: {file_size} байт")
            
            if file_size < 1000000:  # Менее 1MB
                logger.error(f"Файл драйвера слишком мал: {file_size} байт")
                return None
            
            # Проверка расширения файла для Windows
            if platform.system().lower() == "windows":
                if not driver_path.lower().endswith('.exe'):
                    logger.warning(f"Файл драйвера не имеет расширения .exe: {driver_path}")
                    # Попробуем найти правильный файл в той же папке
                    driver_dir = os.path.dirname(driver_path)
                    for file in os.listdir(driver_dir):
                        if file.lower().startswith('chromedriver') and file.lower().endswith('.exe'):
                            correct_path = os.path.join(driver_dir, file)
                            logger.info(f"Найден правильный chromedriver: {correct_path}")
                            return self._validate_chromedriver(correct_path)
                    
                    logger.error("Исполняемый chromedriver.exe не найден")
                    return None
            
            # Проверка что это не текстовый файл (например, THIRD_PARTY_NOTICES)
            try:
                with open(driver_path, 'rb') as f:
                    header = f.read(10)
                    # Проверяем что файл начинается с бинарных данных, а не с текста
                    if header.startswith(b'MZ'):  # PE заголовок для Windows exe
                        logger.info("Найден валидный PE исполняемый файл (Windows)")
                        return driver_path
                    elif header.startswith(b'\x7fELF'):  # ELF заголовок для Linux
                        logger.info("Найден валидный ELF исполняемый файл (Linux)")
                        return driver_path
                    elif not header.decode('utf-8', errors='ignore').isprintable():
                        logger.info("Найден бинарный исполняемый файл")
                        return driver_path
                    else:
                        logger.error(f"Файл выглядит как текстовый, а не исполняемый: {header}")
                        return None
                        
            except Exception as read_error:
                logger.warning(f"Не удалось прочитать заголовок файла: {read_error}")
                # Если не можем прочитать, считаем файл валидным по размеру
                return driver_path
            
        except Exception as e:
            logger.warning(f"Ошибка валидации chromedriver: {e}")
            return None
    
    def _human_delay(self, min_seconds=1, max_seconds=3, description=""):
        """Человекоподобная задержка с логированием и проверкой на прерывание"""
        delay_time = random.uniform(min_seconds, max_seconds)
        if description:
            logger.info(f"⏱️ {description}: {delay_time:.1f}с")
        else:
            logger.debug(f"⏱️ Пауза: {delay_time:.1f}с")
        
        # Разбиваем задержку на маленькие части для быстрого реагирования на Ctrl+C
        start_time = time.time()
        while time.time() - start_time < delay_time:
            if self.is_processing == False:  # Проверяем флаг обработки
                logger.info("🛑 Прерывание по запросу пользователя")
                raise KeyboardInterrupt("Прерывание по запросу пользователя")
            time.sleep(0.1)  # Проверяем каждые 100мс
    
    def _human_type(self, element, text, delay_range=(0.05, 0.15)):
        """Человекоподобный ввод текста с реалистичными задержками"""
        logger.info(f"⌨️ Человекоподобный ввод: {text}")
        
        # Иногда делаем ошибки и исправляем их (как люди)
        if random.random() < 0.1:  # 10% вероятность ошибки
            wrong_char = random.choice('qwertyuiop')
            element.send_keys(wrong_char)
            self._human_delay(0.2, 0.5, "обнаружили ошибку")
            element.send_keys(Keys.BACKSPACE)
            self._human_delay(0.1, 0.3, "исправляем ошибку")
        
        # Вводим текст по символам
        for i, char in enumerate(text):
            element.send_keys(char)
            
            # Различные паузы для разных типов символов
            if char.isdigit():
                delay = random.uniform(0.03, 0.08)  # Цифры быстрее
            elif char.isalpha():
                delay = random.uniform(delay_range[0], delay_range[1])  # Буквы стандартно
            elif char in '-/\\':
                delay = random.uniform(0.1, 0.2)  # Специальные символы медленнее
            else:
                delay = random.uniform(0.05, 0.12)
            
            time.sleep(delay)
            
            # Случайные небольшие паузы (как будто думаем)
            if i > 0 and random.random() < 0.15:  # 15% вероятность паузы
                self._human_delay(0.1, 0.4, "пауза во время ввода")
        
        # Пауза после завершения ввода (проверяем что написали)
        self._human_delay(0.3, 0.8, "проверяем введенный текст")
    
    def _human_scroll(self, direction="down", amount="small"):
        """Человекоподобная прокрутка страницы"""
        try:
            if direction == "up":
                scroll_value = -300 if amount == "small" else -600
            else:
                scroll_value = 300 if amount == "small" else 600
            
            # Добавляем случайность к прокрутке
            scroll_value += random.randint(-50, 50)
            
            logger.debug(f"🖱️ Прокрутка {direction} на {scroll_value}px")
            self.driver.execute_script(f"window.scrollBy(0, {scroll_value});")
            self._human_delay(0.5, 1.5, "после прокрутки")
        except Exception as e:
            logger.warning(f"Ошибка прокрутки: {e}")
    
    def _human_mouse_move(self, element=None, random_movement=True):
        """Человекоподобное движение мыши"""
        try:
            # В headless режиме движение мыши часто приводит к out of bounds.
            if getattr(self, 'headless', False):
                logger.debug("🖱️ Пропуск движения мыши в headless режиме")
                return
            actions = ActionChains(self.driver)
            
            if random_movement:
                # Случайные движения мыши (имитация изучения страницы)
                for _ in range(random.randint(1, 3)):
                    x_offset = random.randint(-100, 100)
                    y_offset = random.randint(-50, 50)
                    actions.move_by_offset(x_offset, y_offset)
                    actions.pause(random.uniform(0.1, 0.3))
                
                # Сброс позиции мыши
                actions.move_by_offset(0, 0)
            
            if element:
                # Плавное движение к элементу
                actions.move_to_element(element)
                actions.pause(random.uniform(0.2, 0.5))
            
            actions.perform()
            logger.debug("🖱️ Движение мыши выполнено")
            
        except Exception as e:
            logger.warning(f"Ошибка движения мыши: {e}")

    def _make_unique_profile_dirs(self):
        """Создает уникальные директории профиля и кэша для Chrome, возвращает (profile_dir, cache_dir)."""
        try:
            base_tmp = tempfile.gettempdir()
            profiles_root = os.path.join(base_tmp, "kad_parser_profiles")
            os.makedirs(profiles_root, exist_ok=True)
            profile_dir = tempfile.mkdtemp(prefix="profile_", dir=profiles_root)
            cache_dir = tempfile.mkdtemp(prefix="cache_", dir=profiles_root)
            self._profile_dir = profile_dir
            return profile_dir, cache_dir
        except Exception as e:
            logger.warning(f"⚠️ Не удалось создать уникальный профиль: {e}")
            return None, None

    def _apply_linux_headless_and_profile(self, options):
        """Применяет headless и уникальный user-data-dir для Linux окружения."""
        try:
            if platform.system().lower() == 'linux':
                # Всегда headless на VM без GUI
                options.add_argument('--headless=new')
                options.add_argument('--window-size=1920,1080')
                options.add_argument('--disable-gpu')
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                profile_dir, cache_dir = self._make_unique_profile_dirs()
                if profile_dir:
                    options.add_argument(f'--user-data-dir={profile_dir}')
                if cache_dir:
                    options.add_argument(f'--disk-cache-dir={cache_dir}')
                self.headless = True
        except Exception as e:
            logger.warning(f"⚠️ Ошибка применения headless/profile: {e}")
    
    def _simulate_human_reading(self, seconds_range=(2, 5)):
        """Имитация чтения страницы пользователем"""
        read_time = random.uniform(seconds_range[0], seconds_range[1])
        logger.info(f"👁️ Имитируем чтение страницы: {read_time:.1f}с")
        
        # Во время "чтения" делаем небольшие прокрутки
        start_time = time.time()
        while time.time() - start_time < read_time:
            if random.random() < 0.3:  # 30% вероятность прокрутки
                self._human_scroll("down", "small")
            time.sleep(random.uniform(0.5, 1.0))
    
    def _setup_realistic_session(self):
        """Настройка реалистичной сессии браузера"""
        try:
            logger.info("🎭 Настройка реалистичной сессии браузера")
            
            # Устанавливаем реалистичные cookies
            realistic_cookies = [
                {"name": "session_start", "value": str(int(time.time()))},
                {"name": "timezone_offset", "value": str(-180)},  # MSK
                {"name": "screen_resolution", "value": "1920x1080"},
                {"name": "browser_language", "value": "ru-RU,ru;q=0.9,en;q=0.8"},
                {"name": "visit_count", "value": str(random.randint(1, 10))},
                {"name": "last_activity", "value": str(int(time.time() - random.randint(3600, 86400)))},
            ]
            
            for cookie in realistic_cookies:
                try:
                    self.driver.add_cookie(cookie)
                except Exception as e:
                    logger.debug(f"Не удалось установить cookie {cookie['name']}: {e}")
            
            # Устанавливаем localStorage данные
            localStorage_data = {
                "userPreferences": json.dumps({
                    "theme": "default",
                    "language": "ru",
                    "visited_pages": random.randint(1, 5)
                }),
                "sessionData": json.dumps({
                    "startTime": int(time.time()),
                    "actions": random.randint(1, 10)
                })
            }
            
            for key, value in localStorage_data.items():
                try:
                    self.driver.execute_script(f"localStorage.setItem('{key}', '{value}');")
                except Exception as e:
                    logger.debug(f"Не удалось установить localStorage {key}: {e}")
            
            logger.info("✅ Реалистичная сессия настроена")
            
        except Exception as e:
            logger.warning(f"Ошибка настройки сессии: {e}")
    
    def _handle_anti_bot_measures(self):
        """Обработка антибот мер"""
        try:
            logger.info("🛡️ Проверка антибот мер...")
            
            # Ищем капчу
            captcha_selectors = [
                "iframe[src*='captcha']",
                ".captcha",
                "#captcha", 
                "[class*='captcha']",
                "iframe[src*='recaptcha']",
                ".g-recaptcha"
            ]
            
            for selector in captcha_selectors:
                try:
                    captcha_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if captcha_element.is_displayed():
                        logger.warning("⚠️ Обнаружена CAPTCHA! Требуется ручное вмешательство")
                        logger.warning("🤖 Пожалуйста, решите CAPTCHA в браузере и нажмите Enter в консоли")
                        input(">>> Нажмите Enter после решения CAPTCHA...")
                        return True
                except:
                    continue
            
            # Ищем блокировки по IP
            blocking_indicators = [
                "заблокирован",
                "blocked",
                "access denied", 
                "слишком много запросов",
                "too many requests",
                "попробуйте позже"
            ]
            
            page_text = self.driver.page_source.lower()
            for indicator in blocking_indicators:
                if indicator in page_text:
                    logger.error(f"🚫 Обнаружена блокировка: {indicator}")
                    return False
            
            # Проверяем модальные окна
            modal_selectors = [
                ".modal",
                "[class*='modal']",
                ".popup",
                "[class*='popup']",
                ".overlay",
                ".notification"
            ]
            
            for selector in modal_selectors:
                try:
                    modals = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for modal in modals:
                        if modal.is_displayed():
                            logger.info(f"💬 Найдено модальное окно: {selector}")
                            # Ищем кнопку закрытия
                            close_buttons = modal.find_elements(By.CSS_SELECTOR, 
                                "button, .close, [class*='close'], [onclick*='close']")
                            for btn in close_buttons:
                                if btn.is_displayed():
                                    self._human_mouse_move(btn)
                                    btn.click()
                                    self._human_delay(1, 2, "после закрытия модального окна")
                                    logger.info("✅ Модальное окно закрыто")
                                    break
                except:
                    continue
            
            return True
            
        except Exception as e:
            logger.warning(f"Ошибка обработки антибот мер: {e}")
            return True
    
    def search_case(self, case_number):
        """Ищет дело по номеру с максимально человекоподобным поведением"""
        # ПРОВЕРКА: Если парсер остановлен, не выполняем поиск
        if not self.is_processing:
            logger.warning("🛑 ПАРСЕР ОСТАНОВЛЕН - поиск отменен")
            return []
            
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                logger.info(f"🎯 Начинаем человекоподобный поиск дела: {case_number} (попытка {retry_count + 1})")
                
                # ЭТАП 1: Переход на сайт с человекоподобным поведением
                target_url = "https://kad.arbitr.ru/"
                logger.info(f"🌐 [NAVIGATION] Переход на главную страницу: {target_url}")
                self.driver.get(target_url)
                logger.info(f"✅ [NAVIGATION] Загружена страница: {self.driver.current_url}")
                
                # Ждем загрузки страницы и делаем человекоподобную паузу
                self._human_delay(2, 4, "ожидание загрузки главной страницы")
                
                # Настраиваем реалистичную сессию
                self._setup_realistic_session()
                
                # ЭТАП 2: Проверка антибот мер
                if not self._handle_anti_bot_measures():
                    logger.error("🚫 Сайт заблокировал доступ")
                    return []
                
                # ЭТАП 3: Имитация изучения страницы
                logger.info("👁️ Изучаем главную страницу...")
                self._simulate_human_reading((3, 6))
                
                # Делаем несколько случайных движений мыши
                self._human_mouse_move(random_movement=True)
                
                # ЭТАП 4: Поиск поля ввода с повышенной надежностью
                logger.info("🔍 Ищем поле поиска дел...")
                
                search_input = None
                input_selectors = [
                    "#sug-cases > div > input",
                    "#sug-cases input",
                    "#sug-cases div input",
                    "input[placeholder*='номер']",
                    "input[placeholder*='дел']",
                    "input[name*='case']",
                    "input[id*='search']",
                    "input[type='text']:not([style*='display: none'])"
                ]
                
                for selector in input_selectors:
                    try:
                        search_input = WebDriverWait(self.driver, 8).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                        logger.info(f"✅ Найдено поле ввода: {selector}")
                        break
                    except TimeoutException:
                        logger.debug(f"Поле не найдено: {selector}")
                        continue
                
                if not search_input:
                    logger.error("❌ Поле поиска не найдено!")
                    # Попытка найти любое видимое поле ввода
                    try:
                        all_inputs = self.driver.find_elements(By.TAG_NAME, "input")
                        for inp in all_inputs:
                            if inp.is_displayed() and inp.is_enabled():
                                input_type = inp.get_attribute("type")
                                if input_type in ["text", "search", None]:
                                    search_input = inp
                                    logger.info("✅ Найдено альтернативное поле ввода")
                                    break
                    except Exception as e:
                        logger.error(f"Ошибка поиска альтернативного поля: {e}")
                    
                    if not search_input:
                        return []
                
                # ЭТАП 5: Человекоподобный клик и ввод текста
                logger.info("🖱️ Кликаем по полю поиска...")
                
                # Прокручиваем к полю
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", search_input)
                self._human_delay(1, 2, "после прокрутки к полю")
                
                # Движение мыши к полю
                self._human_mouse_move(search_input)
                
                # Человекоподобный клик
                try:
                    search_input.click()
                    logger.info("✅ Клик по полю выполнен")
                except Exception as e:
                    logger.warning(f"Обычный клик не сработал: {e}, пробуем JavaScript")
                    self.driver.execute_script("arguments[0].click();", search_input)
                
                self._human_delay(0.5, 1.2, "после клика по полю")
                
                # Очищаем поле (если есть текст)
                try:
                    current_value = search_input.get_attribute("value")
                    if current_value:
                        logger.info("🧹 Очищаем существующий текст...")
                        search_input.clear()
                        self._human_delay(0.3, 0.8, "после очистки поля")
                except Exception as e:
                    logger.debug(f"Ошибка очистки поля: {e}")
                
                # Человекоподобный ввод номера дела
                logger.info("⌨️ Вводим номер дела человекоподобно...")
                self._human_type(search_input, case_number, delay_range=(0.08, 0.18))
                # Логируем фактическое значение из поля
                try:
                    typed_value = search_input.get_attribute("value")
                    logger.info(f"✍️ В поле введено: '{typed_value}'")
                except Exception as e:
                    logger.debug(f"Не удалось прочитать value: {e}")
                
                # ЭТАП 6: Поиск и нажатие кнопки поиска
                logger.info("🔍 Ищем кнопку поиска...")
                
                search_button = None
                button_selectors = [
                "#b-form-submit > div > button",
                "#b-form-submit button",
                "#b-form-submit",
                "button[type='submit']",
                "input[type='submit']",
                "button:contains('Найти')",
                "input[value*='Найти']",
                "[onclick*='search']",
                ".search-button",
                "[class*='search'] button"
            ]
            
                for selector in button_selectors:
                    try:
                        if ":contains(" in selector:
                            # XPath селектор для текста
                            xpath = f"//button[contains(text(), 'Найти')] | //input[@value='Найти'] | //button[contains(@value, 'Найти')]"
                            search_button = WebDriverWait(self.driver, 5).until(
                                EC.element_to_be_clickable((By.XPATH, xpath))
                            )
                        else:
                            search_button = WebDriverWait(self.driver, 5).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                            )
                        
                        logger.info(f"✅ Найдена кнопка поиска: {selector}")
                        break
                        
                    except TimeoutException:
                        logger.debug(f"Кнопка не найдена: {selector}")
                        continue
                
                if not search_button:
                    logger.error("❌ Кнопка поиска не найдена!")
                    # Пробуем нажать Enter в поле ввода
                    logger.info("⌨️ Пробуем нажать Enter в поле ввода...")
                    try:
                        search_input.send_keys(Keys.RETURN)
                        logger.info("✅ Enter нажат")
                    except Exception as e:
                        logger.error(f"Не удалось нажать Enter: {e}")
                        return []
                else:
                    # Человекоподобный клик по кнопке
                    logger.info("🖱️ Кликаем по кнопке поиска...")
                    
                    # Прокручиваем к кнопке
                    self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", search_button)
                    self._human_delay(1, 2, "после прокрутки к кнопке")
                    
                    # Движение мыши к кнопке (пропустим в headless)
                    if not self.headless:
                        self._human_mouse_move(search_button)
                    
                    # Несколько попыток клика
                    click_success = False
                    for attempt in range(3):
                        try:
                            logger.info(f"🎯 Попытка клика #{attempt + 1}")
                            
                            if attempt == 0:
                                # Первая попытка - обычный клик
                                search_button.click()
                            elif attempt == 1:
                                # Вторая попытка - ActionChains
                                if not self.headless:
                                    ActionChains(self.driver).move_to_element(search_button).click().perform()
                                else:
                                    # В headless частый out of bounds — используем JS
                                    self.driver.execute_script("arguments[0].click();", search_button)
                            else:
                                # Третья попытка - JavaScript
                                self.driver.execute_script("arguments[0].click();", search_button)
                            
                            logger.info("✅ Клик по кнопке выполнен")
                            click_success = True
                            break
                        
                        except Exception as e:
                            logger.warning(f"Попытка клика #{attempt + 1} не удалась: {e}")
                            self._human_delay(1, 2, f"перед повторной попыткой #{attempt + 2}")
                            continue
                
                if not click_success:
                    logger.error("❌ Все попытки клика не удались")
                    return []
                
                # ЭТАП 7: Ожидание результатов поиска
                logger.info("⏳ Ожидаем результаты поиска...")
                self._human_delay(3, 6, "ожидание обработки запроса")
                
                # Проверяем что поиск выполнился
                search_executed = False
                for check_attempt in range(5):  # 5 попыток проверки
                    try:
                        # Ищем индикаторы что поиск выполнился
                        result_indicators = [
                            "#b-cases",
                            ".search-results", 
                            "[class*='result']",
                            "#main-column1",
                            ".b-found-total"
                        ]
                        
                        for indicator in result_indicators:
                            try:
                                result_element = self.driver.find_element(By.CSS_SELECTOR, indicator)
                                if result_element.is_displayed():
                                    logger.info(f"✅ Найден индикатор результатов: {indicator}")
                                    search_executed = True
                                    break
                            except NoSuchElementException:
                                continue
                        
                        if search_executed:
                            break
                        
                        logger.info(f"🔄 Проверка результатов #{check_attempt + 1}/5...")
                        self._human_delay(2, 4, "между проверками результатов")
                        
                    except Exception as e:
                        logger.warning(f"Ошибка проверки результатов: {e}")
                        continue
                
                if not search_executed:
                    logger.warning("⚠️ Не удалось подтвердить выполнение поиска")
                    # Но продолжаем попытку найти результаты
                
                # ЭТАП 8: Извлечение результатов
                logger.info("📊 Извлекаем результаты поиска...")
                # Сохраняем дампы для дебага
                try:
                    logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
                    os.makedirs(logs_dir, exist_ok=True)
                    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                    html_path = os.path.join(logs_dir, f'search_results_{ts}.html')
                    with open(html_path, 'w', encoding='utf-8') as f:
                        f.write(self.driver.page_source)
                    # Скриншоты в headless могут быть полезны
                    try:
                        screenshot_path = os.path.join(logs_dir, f'search_results_{ts}.png')
                        self.driver.save_screenshot(screenshot_path)
                    except Exception as _:
                        pass
                    logger.info(f"🧾 Дампы сохранены: {html_path}")
                except Exception as dump_err:
                    logger.debug(f"Не удалось сохранить дампы: {dump_err}")
                
                # Имитируем изучение результатов
                if not self.headless:
                    self._simulate_human_reading((2, 4))
                else:
                    self._human_delay(1, 2, "пауза перед извлечением результатов")
                
                case_links = []
                result_selectors = [
                    "#b-cases > tbody > tr > td.num > div > a",
                    "#b-cases tbody tr td.num a",
                    "#b-cases a[href*='card']",
                    ".search-results a[href*='card']",
                    "table a[href*='card']",
                    "a[href*='Kad/Card']"
                ]
                
                for selector in result_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        if elements:
                            logger.info(f"✅ Найдены результаты с селектором: {selector}")
                            for element in elements:
                                try:
                                    url = element.get_attribute('href')
                                    text = element.text.strip()
                                    if url and text:
                                        case_links.append((url, text))
                                        logger.info(f"📋 Найдено дело: {text}")
                                except Exception as e:
                                    logger.warning(f"Ошибка извлечения данных элемента: {e}")
                                    continue
                            break
                    except Exception as e:
                        logger.debug(f"Ошибка с селектором {selector}: {e}")
                        continue
                
                # ЭТАП 9: Финальная проверка и возврат результатов
                if case_links:
                    logger.info(f"🎉 Успешно найдено {len(case_links)} дел")
                    
                    # Небольшая пауза для "просмотра" результатов
                    self._human_delay(2, 4, "просмотр найденных дел")
                    
                    return case_links
                else:
                    logger.warning("❌ Дела не найдены в результатах поиска")
                    
                    # Проверяем есть ли сообщение "не найдено"
                    not_found_indicators = [
                        "не найдено",
                        "ничего не найдено", 
                        "результатов нет",
                        "no results",
                        "not found"
                    ]
                    
                    page_text = self.driver.page_source.lower()
                    for indicator in not_found_indicators:
                        if indicator in page_text:
                            logger.info(f"ℹ️ Подтверждение что дела не найдены: '{indicator}'")
                            break
                    
                    return []
                    
            except KeyboardInterrupt:
                logger.info("🛑 Получен сигнал завершения (Ctrl+C) во время поиска дела")
                return []
            except Exception as e:
                logger.error(f"❌ Критическая ошибка поиска дела (попытка {retry_count + 1}): {e}")
                
                # Проверяем, является ли ошибка связанной с WebDriver
                if "HTTPConnectionPool" in str(e) or "Failed to establish" in str(e):
                    logger.warning("🔄 Обнаружена ошибка подключения к WebDriver, пробуем переподключиться...")
                    
                    # Закрываем текущий драйвер
                    try:
                        if self.driver:
                            self.driver.quit()
                    except:
                        pass
                    self.driver = None
                    
                    # Пытаемся переподключиться
                    if self.init_driver():
                        logger.info("✅ WebDriver переподключен, повторяем попытку...")
                        retry_count += 1
                        continue
                    else:
                        logger.error("❌ Не удалось переподключить WebDriver")
                        return []
                else:
                    # Для других ошибок просто увеличиваем счетчик
                    retry_count += 1
                    if retry_count < max_retries:
                        logger.info(f"🔄 Повторяем попытку {retry_count + 1}/{max_retries}...")
                        self._human_delay(3, 5, "перед повторной попыткой")
                        continue
                    else:
                        logger.error("❌ Исчерпаны все попытки поиска дела")
                        return []
        
        logger.error("❌ Все попытки поиска дела исчерпаны")
        return []
    
    def download_pdf_files(self, case_url, case_number):
        """УСТАРЕЛО: Скачивание файлов больше не используется. Оставлено для обратной совместимости."""
        # ПРОВЕРКА: Если парсер остановлен, не выполняем скачивание
        if not self.is_processing:
            logger.warning("🛑 ПАРСЕР ОСТАНОВЛЕН - скачивание отменено")
            return []
            
        downloaded_files = []
        
        try:
            logger.info(f"🌐 [NAVIGATION] Переход к делу: {case_url}")
            self.driver.get(case_url)
            logger.info(f"✅ [NAVIGATION] Загружена страница дела: {self.driver.current_url}")
            time.sleep(3)
            
            # Ищем вкладку "Электронное дело"
            try:
                electronic_tab = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 
                        "#main-column > div.b-case-card-content.js-case-card-content > div > div.b-case-chrono > div.b-case-chrono-header > div > div:nth-child(2) > div.b-case-chrono-button.js-case-chrono-button.js-case-chrono-button--ed > div.b-case-chrono-button-text"))
                )
                electronic_tab.click()
                logger.info("✅ Переход на вкладку 'Электронное дело'")
                time.sleep(2)
            except TimeoutException:
                logger.warning("❌ Вкладка 'Электронное дело' не найдена")
                return downloaded_files
            
            # Ждем загрузки списка документов
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#chrono_ed_content > ul"))
                )
                logger.info("✅ Список документов загружен")
            except TimeoutException:
                logger.warning("❌ Список документов не загрузился")
                return downloaded_files
            
            # Ищем все документы в списке
            document_elements = self.driver.find_elements(By.CSS_SELECTOR, "#chrono_ed_content > ul > li")
            total_documents = len(document_elements)
            
            if not document_elements:
                logger.warning("❌ Документы не найдены в списке")
                return downloaded_files
            
            logger.info(f"📄 Найдено {total_documents} документов для обработки")
            
            # Ограничиваем количество документов
            max_documents = min(total_documents, 5)
            if total_documents > max_documents:
                logger.warning(f"🛑 Ограничение: обрабатываем только первые {max_documents} из {total_documents} документов")
            
            # Обрабатываем каждый документ
            for i, doc_element in enumerate(document_elements[:max_documents], 1):
                # ПРОВЕРКА: Если парсер остановлен, прерываем обработку
                if not self.is_processing:
                    logger.warning("🛑 ПАРСЕР ОСТАНОВЛЕН - обработка документов прервана")
                    break
                    
                try:
                    logger.info(f"📋 Обработка документа {i}/{max_documents}")
                    
                    # Извлекаем ссылку на PDF
                    pdf_link_element = doc_element.find_element(By.CSS_SELECTOR, "a")
                    pdf_url = pdf_link_element.get_attribute('href')
                    doc_title = pdf_link_element.text.strip() or f"document_{i}"
                    
                    # Очищаем название
                    doc_title = re.sub(r'\s+', ' ', doc_title).strip()
                    
                    if not pdf_url:
                        logger.warning(f"⚠️ Пустая ссылка для документа {i}")
                        continue
                    
                        logger.info(f"🔗 Ссылка на PDF: {pdf_url}")
                        logger.info(f"📄 Название документа: {doc_title}")
                    
                        # Новая логика больше не скачивает файлы здесь
                        # Этот метод оставлен для совместимости и больше не должен вызываться
                        pass
                    
                except Exception as e:
                    logger.error(f"❌ Ошибка обработки документа {i}: {e}")
                    continue
            
            # Новая логика: никаких перемещений, метод устарел
            
        except KeyboardInterrupt:
            logger.info("🛑 Получен сигнал завершения (Ctrl+C) во время скачивания файлов")
            return downloaded_files
        except Exception as e:
            logger.error(f"❌ Критическая ошибка скачивания файлов: {e}")
        
        return downloaded_files
            
    
    def ensure_driver_ready(self):
        """УСТАРЕЛО: WebDriver теперь инициализируется в каждом запросе"""
        logger.warning("⚠️ ensure_driver_ready() устарел - WebDriver инициализируется в parse_case()")
        return True
    
    def parse_case(self, case_number):
        """Основная функция парсинга дела - НОВЫЙ АЛГОРИТМ (устарело для скачивания)."""
        # Настраиваем обработчики сигналов если еще не настроены
        self._setup_signal_handlers()
        
        # ЖЕСТКОЕ ОГРАНИЧЕНИЕ: только один запуск за раз
        if self.is_processing:
            logger.error("🛑 ПАРСЕР УЖЕ РАБОТАЕТ! Повторный запуск заблокирован!")
            return []
        
        # ПРОВЕРКА: Если парсер был остановлен, не запускаем новый парсинг
        if hasattr(self, '_force_stop') and self._force_stop:
            logger.warning("🛑 ПАРСЕР ПРИНУДИТЕЛЬНО ОСТАНОВЛЕН - новый парсинг заблокирован")
            return []
        
        # Устанавливаем флаг обработки
        self.is_processing = True
        logger.info(f"🚀 НАЧАЛО ПАРСИНГА: {case_number}")
        
        # Очищаем папку files
        self.cleanup_files_directory()
        
        # ШАГ 1: Инициализируем WebDriver
        logger.info("🔧 ШАГ 1: Инициализация WebDriver")
        if not self.init_driver():
            logger.error("❌ Не удалось инициализировать WebDriver")
            return []
        
        try:
            # ШАГ 2: Ищем дело
            logger.info("🔍 ШАГ 2: Поиск по номеру дела")
            case_links = self.search_case(case_number)
            
            if not case_links:
                logger.error("❌ Дела не найдены")
                return []
            
            # ШАГ 3: Переходим на страницу дела и обрабатываем документы
            logger.info("📁 ШАГ 3: Переход на страницу дела и обработка документов")
            case_url, case_text = case_links[0]
            logger.info(f"🔄 Обработка дела: {case_text}")
            logger.info(f"🔗 URL дела: {case_url}")
            
            downloaded_files = []
            
            # ШАГ 3.1: Открываем ссылку на дело в новой вкладке
            logger.info("🪟 ШАГ 3.1: Открытие ссылки на дело в новой вкладке")
            try:
                # Сохраняем текущее окно
                original_window = self.driver.current_window_handle
                logger.info(f"📍 [TAB] Оригинальное окно: {original_window}")
                
                # Открываем новую вкладку
                self.driver.execute_script("window.open('');")
                time.sleep(1)
                
                # Переключаемся на новую вкладку
                new_window = self.driver.window_handles[-1]
                self.driver.switch_to.window(new_window)
                logger.info(f"✅ [TAB] Переключились на новую вкладку: {new_window}")
                
                # Загружаем страницу дела
                logger.info(f"🌐 [TAB] Загружаем страницу дела: {case_url}")
                self.driver.get(case_url)
                time.sleep(5)
                
                current_url = self.driver.current_url
                logger.info(f"✅ [TAB] Страница дела загружена: {current_url}")
                
            except Exception as e:
                logger.error(f"❌ Ошибка открытия новой вкладки: {e}")
                return []
            
            # ШАГ 3.2: Нажимаем на кнопку "Электронное дело"
            logger.info("🔘 ШАГ 3.2: Поиск и нажатие кнопки 'Электронное дело'")
            try:
                # Ищем кнопку "Электронное дело" по точному селектору
                electronic_tab_selectors = [
                    "#main-column > div.b-case-card-content.js-case-card-content > div > div.b-case-chrono > div.b-case-chrono-header > div > div:nth-child(2) > div.b-case-chrono-button.js-case-chrono-button.js-case-chrono-button--ed > div.b-case-chrono-button-text",
                    "#main-column > div.b-case-card-content.js-case-card-content > div > div.b-case-chrono > div.b-case-chrono-header > div > div:nth-child(2) > div.b-case-chrono-button.js-case-chrono-button.js-case-chrono-button--ed.active > div.b-case-chrono-button-text",
                    ".b-case-chrono-button--ed .b-case-chrono-button-text",
                    "div[class*='b-case-chrono-button--ed'] div[class*='b-case-chrono-button-text']",
                    "//div[contains(@class, 'b-case-chrono-button--ed')]//div[contains(@class, 'b-case-chrono-button-text')]"
                ]
                
                electronic_tab = None
                used_selector = None
                
                for selector in electronic_tab_selectors:
                    try:
                        if selector.startswith('//'):
                            # XPath селектор
                            electronic_tab = WebDriverWait(self.driver, 5).until(
                                EC.element_to_be_clickable((By.XPATH, selector))
                            )
                        else:
                            # CSS селектор
                            electronic_tab = WebDriverWait(self.driver, 5).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                            )
                        
                        used_selector = selector
                        logger.info(f"✅ [TAB] Найдена кнопка 'Электронное дело': {selector}")
                        break
                        
                    except TimeoutException:
                        logger.debug(f"[TAB] Кнопка не найдена: {selector}")
                        continue
                
                if not electronic_tab:
                    logger.error("❌ [TAB] Кнопка 'Электронное дело' не найдена!")
                    return []
                
                # Кликаем по кнопке
                logger.info("🖱️ [TAB] Кликаем по кнопке 'Электронное дело'...")
                try:
                    electronic_tab.click()
                    logger.info("✅ [TAB] Клик по кнопке выполнен")
                except Exception as e:
                    logger.warning(f"⚠️ [TAB] Обычный клик не сработал: {e}, пробуем JavaScript")
                    self.driver.execute_script("arguments[0].click();", electronic_tab)
                    logger.info("✅ [TAB] JavaScript клик выполнен")
                
                # Ждем загрузки списка документов
                logger.info("⏳ [TAB] Ожидание загрузки списка документов...")
                time.sleep(3)
                
                # Проверяем, что список документов загрузился
                try:
                    WebDriverWait(self.driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "#chrono_ed_content > ul"))
                    )
                    logger.info("✅ [TAB] Список документов загружен")
                except TimeoutException:
                    logger.warning("⚠️ [TAB] Список документов не загрузился, продолжаем...")
                
            except Exception as e:
                logger.error(f"❌ Ошибка нажатия кнопки 'Электронное дело': {e}")
                return []
            
            # ШАГ 3.3: Обрабатываем документы - УПРОЩЕННАЯ ВЕРСИЯ
            logger.info("📄 ШАГ 3.3: Обработка документов дела")
            try:
                # Ищем все документы в списке
                document_elements = self.driver.find_elements(By.CSS_SELECTOR, "#chrono_ed_content > ul > li")
                total_documents = len(document_elements)
                
                if not document_elements:
                    logger.warning("❌ [TAB] Документы не найдены в списке")
                    return []
                
                logger.info(f"📄 [TAB] Найдено {total_documents} документов для обработки")
                
                # Ограничиваем количество документов
                max_documents = min(total_documents, 5)
                if total_documents > max_documents:
                    logger.warning(f"🛑 [TAB] Ограничение: обрабатываем только первые {max_documents} из {total_documents} документов")
                
                # Обрабатываем каждый документ
                for i, doc_element in enumerate(document_elements[:max_documents], 1):
                    # ПРОВЕРКА: Если парсер остановлен, прерываем обработку
                    if not self.is_processing:
                        logger.warning("🛑 ПАРСЕР ОСТАНОВЛЕН - обработка документов прервана")
                        break
                    
                    try:
                        logger.info(f"📋 [TAB] Обработка документа {i}/{max_documents}")
                        
                        # Извлекаем ссылку на PDF
                        pdf_link_element = doc_element.find_element(By.CSS_SELECTOR, "a")
                        pdf_url = pdf_link_element.get_attribute('href')
                        doc_title = pdf_link_element.text.strip() or f"document_{i}"
                        
                        # Очищаем название
                        doc_title = re.sub(r'\s+', ' ', doc_title).strip()
                        
                        if not pdf_url:
                            logger.warning(f"⚠️ [TAB] Пустая ссылка для документа {i}")
                            continue
                        
                        logger.info(f"🔗 [TAB] Ссылка на документ {i}: {pdf_url}")
                        logger.info(f"📄 [TAB] Название документа {i}: {doc_title}")
                        
                        # Новая логика: в этом методе ранее шло скачивание, теперь ничего не делаем
                        pass
                        
                    except Exception as e:
                        logger.error(f"❌ [TAB] Ошибка обработки документа {i}: {e}")
                        continue
                
                # Закрываем вкладку дела и возвращаемся к оригинальному окну
                logger.info("🔙 [TAB] Закрываем вкладку дела...")
                self.driver.close()
                self.driver.switch_to.window(original_window)
                logger.info("✅ [TAB] Вернулись в оригинальное окно")
                
            except Exception as e:
                logger.error(f"❌ Ошибка обработки документов: {e}")
                # Пытаемся вернуться в оригинальное окно
                try:
                    if len(self.driver.window_handles) > 1:
                        self.driver.switch_to.window(original_window)
                except:
                    pass
            
            
            
            logger.info(f"✅ Обработка завершена. Скачивание файлов отключено")
            return []
            
        except KeyboardInterrupt:
            logger.info("🛑 Получен сигнал завершения (Ctrl+C)")
            logger.info("🔄 Завершение работы парсера...")
            return []
        except Exception as e:
            logger.error(f"❌ Критическая ошибка парсинга: {e}")
            return []
            
        finally:
            # ШАГ 4: ЗАКРЫВАЕМ WebDriver ПОСЛЕ КАЖДОЙ ОБРАБОТКИ
            logger.info("🛑 ШАГ 4: ЗАКРЫТИЕ WebDriver")
            try:
                if self.driver:
                    self.driver.quit()
                    logger.info("✅ WebDriver закрыт")
                self.driver = None
            except Exception as e:
                logger.warning(f"⚠️ Ошибка при закрытии WebDriver: {e}")
            
            # СБРОС ФЛАГА ОБРАБОТКИ
            self.is_processing = False
            logger.info("🏁 ПАРСИНГ ЗАВЕРШЕН - WebDriver ОТКЛЮЧЕН - ФЛАГ СБРОШЕН")

    def collect_document_links(self, case_number):
        """Собирает ссылки на PDF документы без скачивания.

        Возвращает список словарей: {
            "name": "Document #N",
            "url": "https://kad.arbitr.ru/Kad/PdfDocument/...",
            "date": None | "YYYY-MM-DD",
            "source": "kad.arbitr.ru"
        }
        """
        self._setup_signal_handlers()
        if self.is_processing:
            logger.error("🛑 ПАРСЕР УЖЕ РАБОТАЕТ! Повторный запуск заблокирован!")
            return []
        if hasattr(self, '_force_stop') and self._force_stop:
            logger.warning("🛑 ПАРСЕР ПРИНУДИТЕЛЬНО ОСТАНОВЛЕН - новый парсинг заблокирован")
            return []

        self.is_processing = True
        links = []
        try:
            logger.info(f"🚀 НАЧАЛО СБОРА ССЫЛОК: {case_number}")
            # Инициализация драйвера
            if not self.init_driver():
                logger.error("❌ Не удалось инициализировать WebDriver")
                return []

            # Ищем дело
            case_links = self.search_case(case_number)
            if not case_links:
                logger.error("❌ Дела не найдены")
                return []

            case_url, case_text = case_links[0]
            logger.info(f"🔄 Обработка дела: {case_text}")
            logger.info(f"🔗 URL дела: {case_url}")

            # Переходим по ссылке дела в ТЕКУЩЕМ окне (без открытий вкладок)
            self.driver.get(case_url)
            time.sleep(3)

            # Дамп страницы дела для дебага
            try:
                logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
                os.makedirs(logs_dir, exist_ok=True)
                ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                html_path = os.path.join(logs_dir, f'case_page_{ts}.html')
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(self.driver.page_source)
            except Exception:
                pass

            # Открываем вкладку Электронное дело (надежный поиск и клик)
            try:
                # Дожидаемся готовности документа
                for _ in range(10):
                    try:
                        ready = self.driver.execute_script("return document.readyState")
                        if ready == "complete":
                            break
                    except Exception:
                        pass
                    time.sleep(0.3)

                selectors = [
                    # Полный селектор, предоставленный пользователем
                    "#main-column > div.b-case-card-content.js-case-card-content > div > div.b-case-chrono > div.b-case-chrono-header > div > div:nth-child(2) > div.b-case-chrono-button.js-case-chrono-button.js-case-chrono-button--ed > div.b-case-chrono-button-text",
                    # Ранее используемый селектор (на случай другой вёрстки)
                    "#main-column > div.b-case-card-content.js-case-card-content > div > div.b-case-chrono > div > div > div.b-case-chrono-button.js-case-chrono-button.js-case-chrono-button--ed > div.b-case-chrono-button-text",
                    # Упрощённый селектор по классу
                    "div.b-case-chrono-button.js-case-chrono-button.js-case-chrono-button--ed > div.b-case-chrono-button-text",
                ]

                clicked = False

                # Пробуем CSS селекторы
                for css in selectors:
                    try:
                        el = WebDriverWait(self.driver, 6).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, css))
                        )
                        # Скроллим и ждём кликабельность
                        try:
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", el)
                        except Exception:
                            pass
                        el = WebDriverWait(self.driver, 4).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, css))
                        )
                        try:
                            el.click()
                        except Exception:
                            # JS click как резерв, если обычный клик не удался (например, out of bounds)
                            self.driver.execute_script("arguments[0].click();", el)
                        clicked = True
                        break
                    except Exception:
                        continue

                # Пробуем XPath по тексту, если CSS не сработали
                if not clicked:
                    try:
                        xpath = "//div[contains(@class,'b-case-chrono-button-text')][contains(., 'Электронное дело')]"
                        el = WebDriverWait(self.driver, 6).until(
                            EC.presence_of_element_located((By.XPATH, xpath))
                        )
                        try:
                            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", el)
                        except Exception:
                            pass
                        el = WebDriverWait(self.driver, 4).until(
                            EC.element_to_be_clickable((By.XPATH, xpath))
                        )
                        try:
                            el.click()
                        except Exception:
                            self.driver.execute_script("arguments[0].click();", el)
                        clicked = True
                    except Exception:
                        clicked = False

                if not clicked:
                    raise TimeoutException("Кнопка 'Электронное дело' не найдена или недоступна")

                time.sleep(2)
            except Exception as e:
                logger.error(f"❌ Не удалось открыть вкладку 'Электронное дело': {e}")
                return []

            # Ждем список документов
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "#chrono_ed_content > ul"))
                )
            except TimeoutException:
                logger.warning("❌ Список документов не загрузился")
                return []

            # Собираем элементы документов
            document_elements = self.driver.find_elements(By.CSS_SELECTOR, "#chrono_ed_content > ul > li")
            # Ограничение по количеству
            if len(document_elements) > 100:
                document_elements = document_elements[:100]
            total_documents = len(document_elements)
            logger.info(f"📄 Найдено документов: {total_documents}")

            for i, doc_element in enumerate(document_elements, 1):
                try:
                    a_el = doc_element.find_element(By.CSS_SELECTOR, "a")
                    pdf_url = a_el.get_attribute('href')
                    full_title = a_el.text.strip()
                    short_title = re.sub(r"\s+", " ", full_title)[:80] if full_title else None
                    display_name = f"Document #{i}" if not short_title else f"Document #{i} — {short_title}"
                    # Пытаемся извлечь дату из URL/названия
                    date_match = re.search(r"(20\d{2}-\d{2}-\d{2})", pdf_url or "") or re.search(r"(20\d{2}-\d{2}-\d{2})", full_title or "")
                    date_val = date_match.group(1) if date_match else None
                    # Фильтруем только PDF ссылки
                    if pdf_url and (pdf_url.lower().endswith('.pdf') or '.pdf' in (pdf_url.lower())):
                        # Выводим тип документа по ключевым словам
                        doc_type = None
                        try:
                            lowered = (full_title or '').lower()
                            if any(k in lowered for k in ["решение", "postanovlen", "reshen"]):
                                doc_type = "Решение"
                            elif any(k in lowered for k in ["определение", "opredel"]):
                                doc_type = "Определение"
                            elif any(k in lowered for k in ["постановление", "постановл", "пост"]):
                                doc_type = "Постановление"
                            elif any(k in lowered for k in ["исков", "иск", "заявлен"]):
                                doc_type = "Заявление/Иск"
                            else:
                                doc_type = "PDF"
                        except Exception:
                            doc_type = "PDF"

                        # Примечание – исходное полное название, если есть
                        note_val = full_title if full_title else "Ссылка извлечена из раздела 'Электронное дело'"

                        links.append({
                            "name": display_name,
                            "url": pdf_url,
                            "date": date_val,
                            "type": doc_type,
                            "note": note_val,
                            "source": "kad.arbitr.ru"
                        })
                    # Rate limit 400ms
                    time.sleep(0.4)
                except Exception as e:
                    logger.debug(f"Пропуск элемента документа: {e}")
                    continue

            # Сохраняем все ссылки в refs.txt (одна ссылка на строку)
            try:
                refs_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "refs.txt")
                with open(refs_path, "w", encoding="utf-8") as f:
                    for item in links:
                        f.write((item.get("url") or "") + "\n")
                logger.info(f"💾 Ссылки сохранены в {refs_path}")
            except Exception as save_err:
                logger.warning(f"⚠️ Не удалось сохранить refs.txt: {save_err}")

            logger.info(f"✅ Ссылок собрано: {len(links)}")
            return links
        except Exception as e:
            logger.error(f"❌ Ошибка сбора ссылок: {e}")
            return []
        finally:
            try:
                if self.driver:
                    self.driver.quit()
                self.driver = None
            except Exception:
                pass
            self.is_processing = False
    
    def get_downloaded_files(self):
        """Возвращает список скачанных файлов с полными путями"""
        if not os.path.exists(self.files_dir):
            return []
        
        files = []
        for filename in os.listdir(self.files_dir):
            file_path = os.path.join(self.files_dir, filename)
            if os.path.isfile(file_path):
                files.append(file_path)
        
        return sorted(files)
    

    def close(self):
        """Закрывает WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("WebDriver закрыт")
            except Exception as e:
                logger.error(f"Ошибка закрытия WebDriver: {e}")
