import os
import time
import logging
import requests
import shutil
import random
import re
import json
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
from pdf_extraction_algorithms import PDFExtractionAlgorithms

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
        self.files_dir = "files"
        self.downloads_dir = self._get_downloads_directory()
        self.is_processing = False  # Флаг для предотвращения повторных запусков
        self._ensure_files_directory()
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
            logger.info("🤖 Настройка максимально человекоподобного браузера...")
            
            options = uc.ChromeOptions()
            
            # Основные антидетект настройки
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Настройки окна
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--start-maximized')
            
            # Улучшенные настройки стабильности
            options.add_argument('--disable-web-security')
            options.add_argument('--disable-features=VizDisplayCompositor')
            options.add_argument('--disable-ipc-flooding-protection')
            options.add_argument('--disable-renderer-backgrounding')
            options.add_argument('--disable-backgrounding-occluded-windows')
            options.add_argument('--disable-client-side-phishing-detection')
            options.add_argument('--disable-sync')
            options.add_argument('--disable-translate')
            options.add_argument('--disable-background-timer-throttling')
            options.add_argument('--disable-backgrounding-occluded-windows')
            options.add_argument('--disable-renderer-backgrounding')
            
            # Настройки таймаутов
            options.add_argument('--timeout=30000')
            options.add_argument('--page-load-strategy=normal')
            
            # Отключение подозрительных функций
            options.add_argument('--disable-extensions-file-access-check')
            options.add_argument('--disable-extensions-http-throttling')
            options.add_argument('--disable-extensions-except=*')
            options.add_argument('--aggressive-cache-discard')
            options.add_argument('--disable-background-timer-throttling')
            options.add_argument('--disable-renderer-backgrounding')
            options.add_argument('--disable-backgrounding-occluded-windows')
            options.add_argument('--disable-client-side-phishing-detection')
            
            # Человекоподобные предпочтения
            prefs = {
                "profile.default_content_setting_values.notifications": 2,
                "profile.default_content_settings.popups": 0,
                "profile.managed_default_content_settings.images": 1,
                "profile.default_content_setting_values.geolocation": 2,
                "credentials_enable_service": False,
                "profile.password_manager_enabled": False,
                "profile.default_content_setting_values.media_stream_mic": 2,
                "profile.default_content_setting_values.media_stream_camera": 2,
                "intl.accept_languages": "ru-RU,ru,en-US,en",
                "profile.default_content_settings.site_engagement": {
                    "https://kad.arbitr.ru": {"last_engagement_time": time.time()}
                },
                # Настройки папки для скачивания
                "download.default_directory": self.downloads_dir,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True
            }
            options.add_experimental_option("prefs", prefs)
            
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
            
            logger.info("✅ Максимально человекоподобный браузер настроен")
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
            logger.info("🌐 Настройка обычного Chrome с антидетект функциями...")
            
            options = Options()
            
            # Основные антидетект настройки
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Настройки окна и производительности
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--disable-gpu')
            options.add_argument('--remote-debugging-port=9222')
            options.add_argument('--disable-web-security')
            options.add_argument('--disable-features=VizDisplayCompositor')
            
            # Отключаем подозрительные функции
            options.add_argument('--disable-background-timer-throttling')
            options.add_argument('--disable-renderer-backgrounding')
            options.add_argument('--disable-backgrounding-occluded-windows')
            options.add_argument('--disable-client-side-phishing-detection')
            
            # Человекоподобные предпочтения
            prefs = {
                "profile.default_content_setting_values.notifications": 2,
                "profile.default_content_settings.popups": 0,
                "profile.managed_default_content_settings.images": 1,
                "credentials_enable_service": False,
                "profile.password_manager_enabled": False,
                "intl.accept_languages": "ru-RU,ru,en-US,en",
                # Настройки папки для скачивания
                "download.default_directory": self.downloads_dir,
                "download.prompt_for_download": False,
                "download.directory_upgrade": True,
                "safebrowsing.enabled": True
            }
            options.add_experimental_option("prefs", prefs)
            
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
            
            logger.info("✅ Обычный Chrome с антидетект настройками готов")
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
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Настройки окна и производительности
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--disable-gpu')
            
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
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Настройки окна
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--disable-gpu')
            
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
                options.add_argument('--headless')
                self.driver = webdriver.Chrome(options=options)
                logger.warning("✅ Минимальная инициализация в headless режиме")
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
        """Человекоподобная задержка с логированием"""
        delay_time = random.uniform(min_seconds, max_seconds)
        if description:
            logger.info(f"⏱️ {description}: {delay_time:.1f}с")
        else:
            logger.debug(f"⏱️ Пауза: {delay_time:.1f}с")
        time.sleep(delay_time)
    
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
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                logger.info(f"🎯 Начинаем человекоподобный поиск дела: {case_number} (попытка {retry_count + 1})")
                
                # ЭТАП 1: Переход на сайт с человекоподобным поведением
                logger.info("🌐 Переходим на kad.arbitr.ru...")
                self.driver.get("https://kad.arbitr.ru/")
                
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
                
                # Движение мыши к кнопке
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
                            ActionChains(self.driver).move_to_element(search_button).click().perform()
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
            
            # Имитируем изучение результатов
            self._simulate_human_reading((2, 4))
            
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
        """Скачивает PDF файлы из электронного дела"""
        downloaded_files = []
        total_documents = 0
        successful_downloads = 0
        
        try:
            logger.info(f"Переход к делу: {case_url}")
            self.driver.get(case_url)
            time.sleep(3)
            
            # Ищем вкладку "Электронное дело" по точному селектору
            try:
                electronic_tab = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 
                        "#main-column > div.b-case-card-content.js-case-card-content > div > div.b-case-chrono > div.b-case-chrono-header > div > div:nth-child(2) > div.b-case-chrono-button.js-case-chrono-button.js-case-chrono-button--ed > div.b-case-chrono-button-text"))
                )
                electronic_tab.click()
                logger.info("✅ Переход на вкладку 'Электронное дело'")
                time.sleep(2)  # Ждем загрузки списка документов
            except TimeoutException:
                logger.warning("❌ Вкладка 'Электронное дело' не найдена")
                return downloaded_files
            
            # Ждем загрузки содержимого списка документов
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
            
            # Ограничиваем количество документов для предотвращения бесконечного цикла
            max_documents = min(total_documents, 5)  # Максимум 5 документов
            if total_documents > max_documents:
                logger.warning(f"🛑 Ограничение: обрабатываем только первые {max_documents} из {total_documents} документов")
            
            # Логируем все найденные ссылки для отладки
            for i, doc_element in enumerate(document_elements[:max_documents], 1):
                try:
                    link_element = doc_element.find_element(By.CSS_SELECTOR, "a")
                    link_url = link_element.get_attribute('href')
                    link_text = link_element.text.strip()
                    logger.info(f"🔍 Документ {i}: {link_text} -> {link_url}")
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось получить информацию о документе {i}: {e}")
            
            # Обрабатываем каждый документ
            for i, doc_element in enumerate(document_elements, 1):
                try:
                    logger.info(f"📋 Обработка документа {i}/{total_documents}")
                    
                    # Извлекаем дату документа
                    date_element = doc_element.find_element(By.CSS_SELECTOR, "p.b-case-chrono-ed-item-date")
                    date_text = date_element.text.strip()
                    logger.info(f"📅 Дата документа: {date_text}")
                    
                    # Преобразуем дату из dd.mm.yyyy в yyyy-mm-dd
                    try:
                        parsed_date = datetime.strptime(date_text, "%d.%m.%Y")
                        formatted_date = parsed_date.strftime("%Y-%m-%d")
                        logger.info(f"📅 Форматированная дата: {formatted_date}")
                    except ValueError as e:
                        logger.warning(f"⚠️ Не удалось распарсить дату '{date_text}': {e}")
                        formatted_date = f"unknown_date_{i}"
                    
                    # Извлекаем ссылку на PDF
                    pdf_link_element = doc_element.find_element(By.CSS_SELECTOR, "a")
                    pdf_url = pdf_link_element.get_attribute('href')
                    doc_title = pdf_link_element.text.strip() or f"document_{i}"
                    
                    # Очищаем название от символов новой строки и лишних пробелов
                    doc_title = re.sub(r'\s+', ' ', doc_title).strip()
                    
                    # Проверяем, что ссылка существует
                    if not pdf_url:
                        logger.warning(f"⚠️ Пустая ссылка для документа {i}")
                        continue
                    
                    logger.info(f"🔗 Ссылка на PDF: {pdf_url}")
                    logger.info(f"📄 Название документа: {doc_title}")
                    
                    # Используем оригинальный URL без преобразования
                    direct_pdf_url = pdf_url
                    logger.info(f"🔗 Используем оригинальную ссылку: {direct_pdf_url}")
                    
                    # Формируем имя файла с датой
                    safe_case_number = case_number.replace('/', '_').replace('\\', '_')
                    base_filename = f"{formatted_date}_{safe_case_number}_{doc_title}"
                    # Очищаем имя файла от недопустимых символов
                    safe_filename = re.sub(r'[<>:"/\\|?*\n\r\t]', '_', base_filename)
                    filename = f"{safe_filename}.pdf"  # По умолчанию PDF, но может быть изменено при скачивании
                    filepath = os.path.join(self.files_dir, filename)
                    
                    # Проверяем на дубликаты и добавляем суффикс
                    counter = 1
                    original_filepath = filepath
                    while os.path.exists(filepath):
                        name, ext = os.path.splitext(original_filepath)
                        filepath = f"{name}_{counter}{ext}"
                        counter += 1
                    
                    if counter > 1:
                        filename = os.path.basename(filepath)
                        logger.info(f"📝 Файл с суффиксом: {filename}")
                    
                    logger.info(f"💾 Скачивание документа {i}: {filename}")
                    
                    # Скачиваем файл напрямую через GET запрос
                    result = self._download_file(direct_pdf_url, filepath)
                    if result:
                        downloaded_files.append(result)  # result содержит правильное имя файла
                        successful_downloads += 1
                        logger.info(f"✅ Успешно скачан файл: {result}")
                    else:
                        logger.warning(f"❌ Не удалось скачать файл: {filename}")
                    
                    # Небольшая пауза между скачиваниями
                    time.sleep(1)
                    
                except NoSuchElementException as e:
                    logger.error(f"❌ Элемент не найден для документа {i}: {e}")
                    continue
                except Exception as e:
                    logger.error(f"❌ Ошибка обработки документа {i}: {e}")
                    continue
            
            # Итоговая статистика
            logger.info(f"📊 ИТОГИ СКАЧИВАНИЯ:")
            logger.info(f"📄 Всего документов найдено: {total_documents}")
            logger.info(f"✅ Успешно скачано: {successful_downloads}")
            logger.info(f"❌ Не удалось скачать: {total_documents - successful_downloads}")
            
        except Exception as e:
            logger.error(f"❌ Критическая ошибка скачивания файлов: {e}")
            # При критической ошибке переинициализируем WebDriver
            try:
                if hasattr(self, 'driver') and self.driver:
                    self.driver.quit()
            except:
                pass
            self.driver = None
            logger.warning("🔄 WebDriver переинициализирован из-за критической ошибки")
        
        return downloaded_files
    
    def _download_file(self, url, filepath):
        """Скачивание PDF файла с множественными алгоритмами"""
        try:
            if not hasattr(self, 'driver') or not self.driver:
                logger.error("❌ WebDriver не инициализирован")
                return False
            
            logger.info(f"🌐 Скачивание PDF: {url}")
            
            # Алгоритм 1: Поиск ссылки на PDF и прямое скачивание
            result = self._download_with_direct_pdf_link(url, filepath)
            if result:
                logger.info("✅ Файл скачан через прямую ссылку на PDF")
                return result
            
            # Алгоритм 2: Поиск ссылки на PDF, переход по ней и копирование содержимого
            result = self._download_with_pdf_link_and_copy(url, filepath)
            if result:
                logger.info("✅ Файл скачан через переход по ссылке и копирование")
                return result
            
            # Алгоритм 3: Прямое скачивание через requests с cookies
            result = self._download_with_requests_cookies(url, filepath)
            if result:
                logger.info("✅ Файл скачан через requests с cookies")
                return result
            
            # Алгоритм 4: Извлечение прямых ссылок
            result = self._download_with_direct_links(url, filepath)
            if result:
                logger.info("✅ Файл скачан через прямые ссылки")
                return result
            
            # Алгоритм 5: Исправленная автоматизация диалога сохранения (Ctrl+S)
            result = self._download_with_dialog_automation_fixed(url, filepath)
            if result:
                logger.info("✅ Файл скачан через исправленную автоматизацию диалога")
                return result
            
            # Алгоритм 6: Скачивание через правый клик и "Сохранить как"
            result = self._download_with_right_click_save(url, filepath)
            if result:
                logger.info("✅ Файл скачан через правый клик и 'Сохранить как'")
                return result
            
            # Алгоритм 7: Скачивание через печать в PDF
            result = self._download_with_print_to_pdf(url, filepath)
            if result:
                logger.info("✅ Файл скачан через печать в PDF")
                return result
            
            # Алгоритм 8: Скачивание через извлечение из iframe
            result = self._download_with_iframe_extraction(url, filepath)
            if result:
                logger.info("✅ Файл скачан через извлечение из iframe")
                return result
            
            logger.warning(f"❌ Все методы скачивания не сработали для: {url}")
            return False
                
        except Exception as e:
            logger.error(f"❌ Критическая ошибка скачивания {url}: {e}")
            return False
    
    def _download_with_direct_pdf_link(self, url, filepath):
        """Алгоритм 1: Поиск ссылки на PDF и прямое скачивание"""
        try:
            logger.info("🔄 Алгоритм 1: Поиск ссылки на PDF и прямое скачивание")
            
            # Открываем URL в новой вкладке
            self.driver.execute_script("window.open('');")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            self.driver.get(url)
            time.sleep(5)  # Ждем загрузки страницы
            
            # Ищем ссылки на PDF файлы
            pdf_links = []
            
            try:
                # 1. Ищем ссылки в HTML
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                
                # Ищем ссылки с PDF
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if '.pdf' in href.lower() or 'Document/Pdf' in href or 'Kad/PdfDocument' in href:
                        pdf_links.append(href)
                
                # 2. Ищем ссылки в JavaScript
                for script in soup.find_all('script'):
                    if script.string:
                        import re
                        # Ищем URL с PDF
                        pdf_matches = re.findall(r'["\']([^"\']*\.pdf[^"\']*)["\']', script.string, re.IGNORECASE)
                        pdf_links.extend(pdf_matches)
                        
                        # Ищем URL с Document/Pdf
                        doc_matches = re.findall(r'["\']([^"\']*Document/Pdf[^"\']*)["\']', script.string, re.IGNORECASE)
                        pdf_links.extend(doc_matches)
                        
                        # Ищем URL с Kad/PdfDocument
                        kad_matches = re.findall(r'["\']([^"\']*Kad/PdfDocument[^"\']*)["\']', script.string, re.IGNORECASE)
                        pdf_links.extend(kad_matches)
                
                # 3. Ищем ссылки в data-атрибутах
                for element in soup.find_all(attrs={'data-pdf': True}):
                    pdf_links.append(element['data-pdf'])
                
                # 4. Ищем ссылки в onclick
                for element in soup.find_all(onclick=True):
                    onclick = element['onclick']
                    pdf_matches = re.findall(r'["\']([^"\']*\.pdf[^"\']*)["\']', onclick, re.IGNORECASE)
                    pdf_links.extend(pdf_matches)
                
                # 5. Ищем embed элементы с original-url
                for embed in soup.find_all('embed', {'type': 'application/x-google-chrome-pdf'}):
                    if embed.get('original-url'):
                        pdf_links.append(embed.get('original-url'))
                
                logger.info(f"🔍 Найдено {len(pdf_links)} потенциальных ссылок на PDF")
                
                # Убираем дубликаты и пробуем скачать
                unique_links = list(set(pdf_links))
                
                for pdf_url in unique_links:
                    if not pdf_url.startswith('http'):
                        from urllib.parse import urljoin
                        pdf_url = urljoin(url, pdf_url)
                    
                    logger.info(f"🔗 Пробуем скачать PDF по ссылке: {pdf_url}")
                    
                    # Пробуем скачать через requests
                    result = self._download_with_requests_cookies(pdf_url, filepath)
                    if result:
                        logger.info("✅ PDF успешно скачан по найденной ссылке")
                        self.driver.close()
                        self.driver.switch_to.window(self.driver.window_handles[0])
                        return os.path.basename(filepath)
                    else:
                        logger.warning(f"⚠️ Не удалось скачать PDF по ссылке: {pdf_url}")
                
            except Exception as e:
                logger.warning(f"⚠️ Ошибка при поиске ссылок на PDF: {e}")
            
            # Если не нашли подходящие ссылки, возвращаем False
            logger.warning("❌ Не удалось найти рабочую ссылку на PDF")
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])
            return False
            
        except Exception as e:
            logger.warning(f"⚠️ Алгоритм поиска ссылки на PDF не сработал: {e}")
            # Закрываем вкладку при ошибке
            try:
                if len(self.driver.window_handles) > 1:
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
            except:
                pass
            return False
    
    def _download_with_pdf_link_and_copy(self, url, filepath):
        """Алгоритм 2: Поиск ссылки на PDF, переход по ней и копирование содержимого"""
        try:
            logger.info("🔄 Алгоритм 2: Поиск ссылки на PDF, переход по ней и копирование содержимого")
            
            # Открываем URL в новой вкладке
            self.driver.execute_script("window.open('');")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            self.driver.get(url)
            time.sleep(5)  # Ждем загрузки страницы
            
            # Ищем ссылки на PDF файлы
            pdf_links = []
            
            try:
                # 1. Ищем ссылки в HTML
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                
                # Ищем ссылки с PDF
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if '.pdf' in href.lower() or 'Document/Pdf' in href or 'Kad/PdfDocument' in href:
                        pdf_links.append(href)
                
                # 2. Ищем ссылки в JavaScript
                for script in soup.find_all('script'):
                    if script.string:
                        import re
                        # Ищем URL с PDF
                        pdf_matches = re.findall(r'["\']([^"\']*\.pdf[^"\']*)["\']', script.string, re.IGNORECASE)
                        pdf_links.extend(pdf_matches)
                        
                        # Ищем URL с Document/Pdf
                        doc_matches = re.findall(r'["\']([^"\']*Document/Pdf[^"\']*)["\']', script.string, re.IGNORECASE)
                        pdf_links.extend(doc_matches)
                        
                        # Ищем URL с Kad/PdfDocument
                        kad_matches = re.findall(r'["\']([^"\']*Kad/PdfDocument[^"\']*)["\']', script.string, re.IGNORECASE)
                        pdf_links.extend(kad_matches)
                
                # 3. Ищем ссылки в data-атрибутах
                for element in soup.find_all(attrs={'data-pdf': True}):
                    pdf_links.append(element['data-pdf'])
                
                # 4. Ищем ссылки в onclick
                for element in soup.find_all(onclick=True):
                    onclick = element['onclick']
                    pdf_matches = re.findall(r'["\']([^"\']*\.pdf[^"\']*)["\']', onclick, re.IGNORECASE)
                    pdf_links.extend(pdf_matches)
                
                # 5. Ищем embed элементы с original-url
                for embed in soup.find_all('embed', {'type': 'application/x-google-chrome-pdf'}):
                    if embed.get('original-url'):
                        pdf_links.append(embed.get('original-url'))
                
                logger.info(f"🔍 Найдено {len(pdf_links)} потенциальных ссылок на PDF")
                
                # Убираем дубликаты и пробуем перейти по ссылке
                unique_links = list(set(pdf_links))
                
                for pdf_url in unique_links:
                    if not pdf_url.startswith('http'):
                        from urllib.parse import urljoin
                        pdf_url = urljoin(url, pdf_url)
                    
                    logger.info(f"🔗 Переходим по ссылке на PDF: {pdf_url}")
                    
                    try:
                        # Переходим по ссылке на PDF
                        self.driver.get(pdf_url)
                        time.sleep(5)  # Ждем загрузки PDF
                        
                        # Пробуем выделить все содержимое и скопировать
                        try:
                            # Выделяем все содержимое страницы
                            self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.CONTROL + "a")
                            time.sleep(1)
                            
                            # Копируем в буфер обмена
                            self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.CONTROL + "c")
                            time.sleep(1)
                            
                            # Получаем содержимое из буфера обмена
                            clipboard_content = self.driver.execute_script("return navigator.clipboard.readText();")
                            
                            if clipboard_content and len(clipboard_content.strip()) > 10:
                                # Создаем PDF с содержимым
                                enhanced_pdf = self._create_enhanced_pdf_with_content(
                                    clipboard_content, self.driver.page_source, pdf_url
                                )
                                
                                if enhanced_pdf:
                                    with open(filepath, 'wb') as f:
                                        f.write(enhanced_pdf)
                                    logger.info("✅ PDF создан с содержимым из буфера обмена")
                                    self.driver.close()
                                    self.driver.switch_to.window(self.driver.window_handles[0])
                                    return os.path.basename(filepath)
                                else:
                                    logger.warning("⚠️ Не удалось создать PDF с содержимым")
                            else:
                                logger.warning("⚠️ Содержимое буфера обмена пустое или слишком короткое")
                                
                        except Exception as copy_error:
                            logger.warning(f"⚠️ Ошибка при копировании содержимого: {copy_error}")
                            
                            # Fallback: пробуем скачать напрямую
                            result = self._download_with_requests_cookies(pdf_url, filepath)
                            if result:
                                logger.info("✅ PDF скачан напрямую как fallback")
                                self.driver.close()
                                self.driver.switch_to.window(self.driver.window_handles[0])
                                return os.path.basename(filepath)
                    
                    except Exception as navigation_error:
                        logger.warning(f"⚠️ Ошибка при переходе по ссылке {pdf_url}: {navigation_error}")
                        continue
                
            except Exception as e:
                logger.warning(f"⚠️ Ошибка при поиске ссылок на PDF: {e}")
            
            # Если не нашли подходящие ссылки, возвращаем False
            logger.warning("❌ Не удалось найти рабочую ссылку на PDF")
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])
            return False
            
        except Exception as e:
            logger.warning(f"⚠️ Алгоритм перехода по ссылке и копирования не сработал: {e}")
            # Закрываем вкладку при ошибке
            try:
                if len(self.driver.window_handles) > 1:
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
            except:
                pass
            return False
    
    def _download_with_right_click_save(self, url, filepath):
        """Алгоритм 6: Скачивание через правый клик и 'Сохранить как'"""
        try:
            logger.info("🔄 Алгоритм 6: Скачивание через правый клик и 'Сохранить как'")
            
            # Открываем URL в новой вкладке
            self.driver.execute_script("window.open('');")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            self.driver.get(url)
            time.sleep(5)  # Ждем загрузки страницы
            
            try:
                # Ищем элемент для правого клика (body или embed)
                target_element = None
                
                # Пробуем найти embed элемент
                try:
                    target_element = self.driver.find_element(By.CSS_SELECTOR, "embed[type='application/x-google-chrome-pdf']")
                except:
                    # Если embed не найден, используем body
                    target_element = self.driver.find_element(By.TAG_NAME, "body")
                
                if target_element:
                    # Выполняем правый клик
                    from selenium.webdriver.common.action_chains import ActionChains
                    actions = ActionChains(self.driver)
                    actions.context_click(target_element).perform()
                    time.sleep(2)
                    
                    # Пробуем найти и нажать "Сохранить как"
                    try:
                        # Ищем пункт меню "Сохранить как" или "Save as"
                        save_as_element = self.driver.find_element(By.XPATH, "//*[contains(text(), 'Сохранить как') or contains(text(), 'Save as')]")
                        save_as_element.click()
                        time.sleep(3)
                        
                        # Ждем появления диалога сохранения и ищем файл в папке Загрузки
                        filename = os.path.basename(filepath)
                        downloaded_file = self._find_downloaded_file(filename)
                        if downloaded_file:
                            # Перемещаем файл в нужную папку
                            final_filepath = self._move_file_from_downloads(downloaded_file, filepath)
                            if final_filepath:
                                logger.info("✅ PDF скачан через правый клик")
                                self.driver.close()
                                self.driver.switch_to.window(self.driver.window_handles[0])
                                return os.path.basename(final_filepath)
                        
                    except Exception as menu_error:
                        logger.warning(f"⚠️ Не удалось найти пункт меню 'Сохранить как': {menu_error}")
                
            except Exception as click_error:
                logger.warning(f"⚠️ Ошибка при правом клике: {click_error}")
            
            # Если не удалось скачать через правый клик, возвращаем False
            logger.warning("❌ Не удалось скачать через правый клик")
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])
            return False
            
        except Exception as e:
            logger.warning(f"⚠️ Алгоритм правого клика не сработал: {e}")
            # Закрываем вкладку при ошибке
            try:
                if len(self.driver.window_handles) > 1:
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
            except:
                pass
            return False
    
    def _download_with_print_to_pdf(self, url, filepath):
        """Алгоритм 7: Скачивание через печать в PDF"""
        try:
            logger.info("🔄 Алгоритм 7: Скачивание через печать в PDF")
            
            # Открываем URL в новой вкладке
            self.driver.execute_script("window.open('');")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            self.driver.get(url)
            time.sleep(5)  # Ждем загрузки страницы
            
            try:
                # Открываем диалог печати
                self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.CONTROL + "p")
                time.sleep(3)
                
                # Пробуем найти и нажать "Сохранить как PDF"
                try:
                    # Ищем кнопку "Сохранить как PDF" или "Save as PDF"
                    save_pdf_element = self.driver.find_element(By.XPATH, "//*[contains(text(), 'Сохранить как PDF') or contains(text(), 'Save as PDF')]")
                    save_pdf_element.click()
                    time.sleep(3)
                    
                    # Ждем появления диалога сохранения и ищем файл в папке Загрузки
                    filename = os.path.basename(filepath)
                    downloaded_file = self._find_downloaded_file(filename)
                    if downloaded_file:
                        # Перемещаем файл в нужную папку
                        final_filepath = self._move_file_from_downloads(downloaded_file, filepath)
                        if final_filepath:
                            logger.info("✅ PDF скачан через печать")
                            self.driver.close()
                            self.driver.switch_to.window(self.driver.window_handles[0])
                            return os.path.basename(final_filepath)
                    
                except Exception as print_error:
                    logger.warning(f"⚠️ Не удалось найти кнопку 'Сохранить как PDF': {print_error}")
                
            except Exception as print_dialog_error:
                logger.warning(f"⚠️ Ошибка при открытии диалога печати: {print_dialog_error}")
            
            # Если не удалось скачать через печать, возвращаем False
            logger.warning("❌ Не удалось скачать через печать")
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])
            return False
            
        except Exception as e:
            logger.warning(f"⚠️ Алгоритм печати не сработал: {e}")
            # Закрываем вкладку при ошибке
            try:
                if len(self.driver.window_handles) > 1:
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
            except:
                pass
            return False
    
    def _download_with_iframe_extraction(self, url, filepath):
        """Алгоритм 8: Скачивание через извлечение из iframe"""
        try:
            logger.info("🔄 Алгоритм 8: Скачивание через извлечение из iframe")
            
            # Открываем URL в новой вкладке
            self.driver.execute_script("window.open('');")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            self.driver.get(url)
            time.sleep(5)  # Ждем загрузки страницы
            
            try:
                # Ищем iframe элементы
                iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                logger.info(f"🔍 Найдено {len(iframes)} iframe элементов")
                
                for i, iframe in enumerate(iframes):
                    try:
                        # Переключаемся на iframe
                        self.driver.switch_to.frame(iframe)
                        time.sleep(2)
                        
                        # Ищем ссылки на PDF в iframe
                        pdf_links = []
                        
                        # Ищем ссылки с PDF
                        for link in self.driver.find_elements(By.TAG_NAME, "a"):
                            href = link.get_attribute("href")
                            if href and ('.pdf' in href.lower() or 'Document/Pdf' in href or 'Kad/PdfDocument' in href):
                                pdf_links.append(href)
                        
                        # Ищем embed элементы с original-url
                        for embed in self.driver.find_elements(By.CSS_SELECTOR, "embed[type='application/x-google-chrome-pdf']"):
                            original_url = embed.get_attribute("original-url")
                            if original_url:
                                pdf_links.append(original_url)
                        
                        if pdf_links:
                            logger.info(f"🔗 Найдено {len(pdf_links)} ссылок на PDF в iframe {i}")
                            
                            # Пробуем скачать по найденным ссылкам
                            for pdf_url in pdf_links:
                                if not pdf_url.startswith('http'):
                                    from urllib.parse import urljoin
                                    pdf_url = urljoin(url, pdf_url)
                                
                                result = self._download_with_requests_cookies(pdf_url, filepath)
                                if result:
                                    logger.info("✅ PDF скачан из iframe")
                                    self.driver.switch_to.default_content()
                                    self.driver.close()
                                    self.driver.switch_to.window(self.driver.window_handles[0])
                                    return os.path.basename(filepath)
                        
                        # Возвращаемся к основному контенту
                        self.driver.switch_to.default_content()
                        
                    except Exception as iframe_error:
                        logger.warning(f"⚠️ Ошибка при работе с iframe {i}: {iframe_error}")
                        # Возвращаемся к основному контенту
                        try:
                            self.driver.switch_to.default_content()
                        except:
                            pass
                        continue
                
            except Exception as iframe_search_error:
                logger.warning(f"⚠️ Ошибка при поиске iframe: {iframe_search_error}")
            
            # Если не удалось скачать из iframe, возвращаем False
            logger.warning("❌ Не удалось скачать из iframe")
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])
            return False
            
        except Exception as e:
            logger.warning(f"⚠️ Алгоритм извлечения из iframe не сработал: {e}")
            # Закрываем вкладку при ошибке
            try:
                if len(self.driver.window_handles) > 1:
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
            except:
                pass
            return False
    
    def _create_enhanced_pdf_with_content(self, text_content, html_content, url, title="", description=""):
        """Создает улучшенный PDF с содержимым страницы"""
        try:
            # Очищаем текст от лишних символов
            clean_text = text_content.strip() if text_content else "Содержимое недоступно"
            clean_title = title.strip() if title else "Документ kad.arbitr.ru"
            clean_description = description.strip() if description else ""
            
            # Если текст пустой, пытаемся извлечь информацию из HTML
            if not clean_text or clean_text == "Содержимое недоступно":
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    # Извлекаем текст из всех элементов
                    all_text = soup.get_text()
                    if all_text and len(all_text.strip()) > 10:
                        clean_text = all_text.strip()[:1000]  # Ограничиваем длину
                    else:
                        clean_text = "Документ загружен, но содержимое недоступно для извлечения"
                        
                except Exception as parse_error:
                    logger.warning(f"⚠️ Ошибка извлечения текста из HTML: {parse_error}")
                    clean_text = "Ошибка извлечения содержимого"
            
            # Создаем содержимое PDF
            pdf_text = f"""Документ: {clean_title}
URL: {url}
Описание: {clean_description}

Содержимое:
{clean_text[:800]}

---
Документ получен с сайта kad.arbitr.ru
Время создания: {time.strftime('%Y-%m-%d %H:%M:%S')}"""
            
            # Простой PDF с текстовым содержимым
            pdf_content = f"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
/Resources <<
/Font <<
/F1 <<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
>>
>>
endobj

4 0 obj
<<
/Length {len(pdf_text) + 200}
>>
stream
BT
/F1 10 Tf
72 750 Td
({pdf_text[:500]}) Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000204 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
{len(pdf_text) + 400}
%%EOF"""
            
            return pdf_content.encode('utf-8')
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка создания улучшенного PDF: {e}")
            return None

    def _download_with_dialog_automation_fixed(self, url, filepath):
        """Алгоритм 2: ИСПРАВЛЕННАЯ автоматизация диалога сохранения (Ctrl+S)"""
        try:
            logger.info("🔄 Алгоритм 2: Исправленная автоматизация диалога сохранения")
            
            # Открываем URL в новой вкладке
            self.driver.execute_script("window.open('');")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            self.driver.get(url)
            time.sleep(5)  # Ждем полной загрузки страницы
            
            # Сэмулируем нажатие Ctrl+S
            logger.info("⌨️ Нажимаем Ctrl+S для открытия диалога сохранения")
            
            # Нажимаем Ctrl+S
            body = self.driver.find_element(By.TAG_NAME, "body")
            ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('s').key_up(Keys.CONTROL).perform()
            time.sleep(3)  # Увеличиваем время ожидания диалога
            
            # НОВАЯ ЛОГИКА: Используем pyautogui для автоматизации диалога Windows
            try:
                import pyautogui
                logger.info("🤖 Используем pyautogui для автоматизации диалога Windows")
                
                # Ждем появления диалога сохранения
                time.sleep(2)
                
                # Вводим путь к файлу в диалоге
                pyautogui.write(filepath)
                time.sleep(1)
                
                # Нажимаем Enter для сохранения
                pyautogui.press('enter')
                time.sleep(3)
                
                # Проверяем, что файл создался
                if os.path.exists(filepath):
                    logger.info(f"✅ Файл сохранен через pyautogui: {filepath}")
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
                    return os.path.basename(filepath)
                else:
                    logger.warning("⚠️ Файл не найден после pyautogui")
                    
            except ImportError:
                logger.warning("⚠️ pyautogui не установлен, используем альтернативный метод")
                
                # Альтернативный метод: используем JavaScript для скачивания
                try:
                    # Создаем ссылку для скачивания
                    download_script = f"""
                    var link = document.createElement('a');
                    link.href = '{url}';
                    link.download = '{os.path.basename(filepath)}';
                    link.target = '_blank';
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                    """
                    
                    self.driver.execute_script(download_script)
                    time.sleep(5)  # Ждем скачивания
                    
                    # Ищем скачанный файл в папке Загрузки
                    filename = os.path.basename(filepath)
                    downloaded_file = self._find_downloaded_file(filename)
                    
                    if downloaded_file:
                        # Перемещаем файл в нужную папку
                        final_filepath = self._move_file_from_downloads(downloaded_file, filepath)
                        if final_filepath:
                            logger.info(f"✅ PDF скачан через JavaScript: {final_filepath}")
                            self.driver.close()
                            self.driver.switch_to.window(self.driver.window_handles[0])
                            return os.path.basename(final_filepath)
                    
                except Exception as js_error:
                    logger.warning(f"⚠️ JavaScript метод не сработал: {js_error}")
            
            # Закрываем вкладку
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])
            return False
            
        except Exception as e:
            logger.warning(f"⚠️ Исправленная автоматизация диалога не сработала: {e}")
            # Закрываем вкладку при ошибке
            try:
                if len(self.driver.window_handles) > 1:
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
            except:
                pass
            return False

    def _download_with_dialog_automation(self, url, filepath):
        """Алгоритм 1: Автоматизация диалога сохранения (Ctrl+S)"""
        try:
            logger.info("🔄 Алгоритм 1: Автоматизация диалога сохранения")
            
            # Открываем URL в новой вкладке
            self.driver.execute_script("window.open('');")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            self.driver.get(url)
            time.sleep(5)  # Ждем полной загрузки страницы
            
            # Сэмулируем нажатие Ctrl+S
            logger.info("⌨️ Нажимаем Ctrl+S для открытия диалога сохранения")
            
            # Нажимаем Ctrl+S
            body = self.driver.find_element(By.TAG_NAME, "body")
            ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('s').key_up(Keys.CONTROL).perform()
            time.sleep(2)  # Ждем появления диалога
            
            # Автоматизируем диалог сохранения
            try:
                # Устанавливаем путь к папке Загрузки в диалоге
                logger.info("📁 Устанавливаем путь к папке Загрузки в диалоге")
                
                # Нажимаем Tab для перехода к полю пути
                ActionChains(self.driver).send_keys(Keys.TAB).perform()
                time.sleep(0.5)
                
                # Очищаем поле и вводим путь к папке Загрузки
                ActionChains(self.driver).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).perform()
                time.sleep(0.5)
                ActionChains(self.driver).send_keys(self.downloads_dir).perform()
                time.sleep(1)
                
                # Нажимаем Enter для сохранения
                ActionChains(self.driver).send_keys(Keys.ENTER).perform()
                logger.info("✅ Диалог сохранения автоматизирован")
                
                # Ждем скачивания файла
                time.sleep(8)
                
                # Ищем скачанный файл в папке Загрузки
                filename = os.path.basename(filepath)
                downloaded_file = self._find_downloaded_file(filename)
                
                if downloaded_file:
                    # Перемещаем файл в нужную папку
                    final_filepath = self._move_file_from_downloads(downloaded_file, filepath)
                    if final_filepath:
                        logger.info(f"✅ PDF скачан через автоматизацию диалога: {final_filepath}")
                        self.driver.close()
                        self.driver.switch_to.window(self.driver.window_handles[0])
                        return os.path.basename(final_filepath)
                else:
                    logger.warning("⚠️ Файл не найден в папке Загрузки после автоматизации диалога")
                
            except Exception as e:
                logger.warning(f"⚠️ Автоматизация диалога не сработала: {e}")
            
            # Закрываем вкладку
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])
            return False
            
        except Exception as e:
            logger.warning(f"⚠️ Алгоритм автоматизации диалога не сработал: {e}")
            # Закрываем вкладку при ошибке
            try:
                if len(self.driver.window_handles) > 1:
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
            except:
                pass
            return False
    
    def _download_with_requests_cookies(self, url, filepath):
        """Алгоритм 2: Прямое скачивание через requests с cookies браузера"""
        try:
            logger.info("🔄 Алгоритм 2: Прямое скачивание через requests с cookies")
            
            # Получаем cookies из браузера
            cookies = {}
            for cookie in self.driver.get_cookies():
                cookies[cookie['name']] = cookie['value']
            
            # Получаем User-Agent из браузера
            user_agent = self.driver.execute_script("return navigator.userAgent;")
            
            # Правильные заголовки для обхода защиты
            headers = {
                'User-Agent': user_agent,
                'Accept': 'application/pdf,application/octet-stream,*/*',
                'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Referer': 'https://kad.arbitr.ru/',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
                'DNT': '1'
            }
            
            # Скачиваем с правильными заголовками и cookies
            response = requests.get(url, headers=headers, cookies=cookies, timeout=30, verify=False)
            
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '').lower()
                
                if 'pdf' in content_type or response.content.startswith(b'%PDF'):
                    # Это PDF файл, сохраняем его
                    with open(filepath, 'wb') as f:
                        f.write(response.content)
                    logger.info(f"✅ PDF скачан через requests: {filepath} ({len(response.content)} байт)")
                    return os.path.basename(filepath)
                else:
                    logger.info(f"ℹ️ Получен HTML вместо PDF (Content-Type: {content_type})")
                    return False
            else:
                logger.warning(f"❌ HTTP ошибка: {response.status_code}")
                return False
                
        except Exception as e:
            logger.warning(f"⚠️ Алгоритм requests с cookies не сработал: {e}")
            return False
    
    def _download_with_direct_links(self, url, filepath):
        """Алгоритм 4: Извлечение прямых ссылок и скачивание"""
        try:
            logger.info("🔄 Алгоритм 4: Извлечение прямых ссылок")
            
            # Открываем URL в новой вкладке
            self.driver.execute_script("window.open('');")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            self.driver.get(url)
            time.sleep(5)  # Ждем полной загрузки страницы
            
            # СНАЧАЛА: Ищем embed элемент с real PDF URL (включая Shadow DOM)
            original_url = None
            
            # Сначала пробуем найти через JavaScript в Shadow DOM
            try:
                logger.info("🔄 Поиск embed элемента через JavaScript в Shadow DOM")
                
                # Выполняем JavaScript для поиска embed элемента в Shadow DOM
                js_script = """
                // Ищем embed элемент в Shadow DOM
                function findEmbedInShadowDOM() {
                    console.log('Поиск pdf-viewer элемента...');
                    
                    // Ищем pdf-viewer элемент
                    const pdfViewer = document.querySelector('pdf-viewer');
                    console.log('pdf-viewer найден:', !!pdfViewer);
                    
                    if (pdfViewer) {
                        console.log('pdf-viewer shadowRoot:', !!pdfViewer.shadowRoot);
                        
                        if (pdfViewer.shadowRoot) {
                            // Ищем embed в Shadow DOM pdf-viewer
                            const embed = pdfViewer.shadowRoot.querySelector('embed[type="application/x-google-chrome-pdf"]');
                            console.log('embed в Shadow DOM найден:', !!embed);
                            
                            if (embed) {
                                const originalUrl = embed.getAttribute('original-url');
                                console.log('original-url в Shadow DOM:', originalUrl);
                                return originalUrl;
                            }
                        }
                    }
                    
                    // Ищем embed в основном DOM
                    const embed = document.querySelector('embed[type="application/x-google-chrome-pdf"]');
                    console.log('embed в основном DOM найден:', !!embed);
                    
                    if (embed) {
                        const originalUrl = embed.getAttribute('original-url');
                        console.log('original-url в основном DOM:', originalUrl);
                        return originalUrl;
                    }
                    
                    // Дополнительный поиск по всем embed элементам
                    const allEmbeds = document.querySelectorAll('embed');
                    console.log('Всего embed элементов:', allEmbeds.length);
                    
                    for (let i = 0; i < allEmbeds.length; i++) {
                        const emb = allEmbeds[i];
                        console.log('Embed', i, 'type:', emb.getAttribute('type'));
                        if (emb.getAttribute('type') === 'application/x-google-chrome-pdf') {
                            const originalUrl = emb.getAttribute('original-url');
                            console.log('Найден original-url:', originalUrl);
                            return originalUrl;
                        }
                    }
                    
                    return null;
                }
                
                return findEmbedInShadowDOM();
                """
                
                original_url = self.driver.execute_script(js_script)
                
                if original_url:
                    logger.info(f"🔗 Найдена реальная ссылка на PDF через JavaScript: {original_url}")
                else:
                    logger.warning("⚠️ Embed элемент не найден через JavaScript")
                    
            except Exception as js_error:
                logger.warning(f"⚠️ Ошибка при поиске через JavaScript: {js_error}")
            
            # Если JavaScript не сработал, пробуем обычный поиск
            if not original_url:
                try:
                    # Сначала пробуем найти обычный embed элемент
                    embed_element = self.driver.find_element(By.CSS_SELECTOR, "embed[type='application/x-google-chrome-pdf']")
                    original_url = embed_element.get_attribute('original-url')
                    
                    if original_url:
                        logger.info(f"🔗 Найдена реальная ссылка на PDF в embed: {original_url}")
                    else:
                        logger.warning("⚠️ Атрибут original-url не найден в embed элементе")
                        
                except Exception as embed_error:
                    logger.debug(f"Embed элемент не найден: {embed_error}")
            
            # Если нашли реальную ссылку, скачиваем PDF
            if original_url:
                # Скачиваем PDF по реальной ссылке
                result = self._download_with_requests_cookies(original_url, filepath)
                if result:
                    logger.info("✅ PDF скачан по реальной ссылке")
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
                    return result
                else:
                    logger.warning("⚠️ Не удалось скачать PDF по реальной ссылке")
            
            # Если не нашли реальную ссылку, пробуем другие методы
            logger.warning("❌ Не удалось найти реальную ссылку на PDF через embed элемент")
            
            # Получаем HTML содержимое
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Ищем различные варианты ссылок на PDF
            pdf_urls = []
            
            # 1. Прямые ссылки на PDF
            for link in soup.find_all('a', href=True):
                href = link['href']
                if '.pdf' in href.lower() or 'Document/Pdf' in href or 'Kad/PdfDocument' in href:
                    pdf_urls.append(href)
            
            # 2. Ссылки в JavaScript
            for script in soup.find_all('script'):
                if script.string:
                    # Ищем URL с PDF
                    pdf_matches = re.findall(r'["\']([^"\']*\.pdf[^"\']*)["\']', script.string, re.IGNORECASE)
                    pdf_urls.extend(pdf_matches)
                    
                    # Ищем URL с Document/Pdf
                    doc_matches = re.findall(r'["\']([^"\']*Document/Pdf[^"\']*)["\']', script.string, re.IGNORECASE)
                    pdf_urls.extend(doc_matches)
                    
                    # Ищем URL с Kad/PdfDocument
                    kad_matches = re.findall(r'["\']([^"\']*Kad/PdfDocument[^"\']*)["\']', script.string, re.IGNORECASE)
                    pdf_urls.extend(kad_matches)
            
            # 3. Ссылки в data-атрибутах
            for element in soup.find_all(attrs={'data-pdf': True}):
                pdf_urls.append(element['data-pdf'])
            
            # 4. Ссылки в onclick
            for element in soup.find_all(onclick=True):
                onclick = element['onclick']
                pdf_matches = re.findall(r'["\']([^"\']*\.pdf[^"\']*)["\']', onclick, re.IGNORECASE)
                pdf_urls.extend(pdf_matches)
            
            if pdf_urls:
                # Убираем дубликаты и берем первую ссылку
                unique_urls = list(set(pdf_urls))
                pdf_url = unique_urls[0]
                
                if not pdf_url.startswith('http'):
                    pdf_url = urljoin(url, pdf_url)
                
                logger.info(f"🔗 Найдена прямая ссылка на PDF: {pdf_url}")
                
                # Пробуем скачать найденную ссылку через requests
                result = self._download_with_requests_cookies(pdf_url, filepath)
                if result:
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
                    return result
                
                # Если requests не сработал, пробуем через браузер
                self.driver.get(pdf_url)
                time.sleep(5)  # Ждем скачивания
                
                # Ищем скачанный файл в папке Загрузки
                filename = os.path.basename(filepath)
                downloaded_file = self._find_downloaded_file(filename)
                if downloaded_file:
                    # Перемещаем файл в нужную папку
                    final_filepath = self._move_file_from_downloads(downloaded_file, filepath)
                    if final_filepath:
                        logger.info(f"✅ PDF скачан по извлеченной ссылке: {final_filepath}")
                        self.driver.close()
                        self.driver.switch_to.window(self.driver.window_handles[0])
                        return os.path.basename(final_filepath)
            else:
                logger.warning("❌ Прямые ссылки на PDF не найдены в HTML")
            
            # Закрываем вкладку
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])
            return False
            
        except Exception as e:
            logger.warning(f"⚠️ Алгоритм извлечения прямых ссылок не сработал: {e}")
            # Закрываем вкладку при ошибке
            try:
                if len(self.driver.window_handles) > 1:
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
            except:
                pass
            return False
    
    def _download_with_improved_javascript(self, url, filepath):
        """Алгоритм 4: Улучшенное скачивание через JavaScript (последний fallback)"""
        try:
            logger.info("🔄 Алгоритм 4: Улучшенное JavaScript скачивание")
            
            # Открываем URL в новой вкладке
            self.driver.execute_script("window.open('');")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            self.driver.get(url)
            time.sleep(5)  # Ждем полной загрузки страницы
            
            filename = os.path.basename(filepath)
            
            # Метод 1: Улучшенное создание ссылки для скачивания
            try:
                download_script = """
                // Создаем ссылку для скачивания
                var link = document.createElement('a');
                link.href = arguments[0];
                link.download = arguments[1];
                link.target = '_blank';
                link.style.display = 'none';
                document.body.appendChild(link);
                
                // Симулируем клик
                var clickEvent = new MouseEvent('click', {
                    view: window,
                    bubbles: true,
                    cancelable: true
                });
                link.dispatchEvent(clickEvent);
                
                // Удаляем ссылку
                setTimeout(function() {
                    document.body.removeChild(link);
                }, 1000);
                """
                
                self.driver.execute_script(download_script, url, filename)
                time.sleep(8)  # Ждем скачивания
                
                # Ищем скачанный файл
                downloaded_file = self._find_downloaded_file(filename)
                if downloaded_file:
                    final_filepath = self._move_file_from_downloads(downloaded_file, filepath)
                    if final_filepath:
                        logger.info(f"✅ Файл скачан через улучшенный JavaScript: {final_filepath}")
                        self.driver.close()
                        self.driver.switch_to.window(self.driver.window_handles[0])
                        return os.path.basename(final_filepath)
                
            except Exception as e:
                logger.debug(f"Улучшенный JavaScript скачивание не сработал: {e}")
            
            # Метод 2: Fetch API с улучшенной обработкой
            try:
                fetch_script = """
                fetch(arguments[0], {
                    method: 'GET',
                    headers: {
                        'Accept': 'application/pdf,application/octet-stream,*/*',
                        'User-Agent': navigator.userAgent
                    },
                    credentials: 'include'
                })
                .then(response => {
                    if (response.ok) {
                        return response.blob();
                    }
                    throw new Error('Network response was not ok');
                })
                .then(blob => {
                    var url = window.URL.createObjectURL(blob);
                    var link = document.createElement('a');
                    link.href = url;
                    link.download = arguments[1];
                    link.style.display = 'none';
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                    window.URL.revokeObjectURL(url);
                })
                .catch(error => {
                    console.error('Fetch error:', error);
                });
                """
                
                self.driver.execute_script(fetch_script, url, filename)
                time.sleep(8)  # Ждем скачивания
                
                # Ищем скачанный файл
                downloaded_file = self._find_downloaded_file(filename)
                if downloaded_file:
                    final_filepath = self._move_file_from_downloads(downloaded_file, filepath)
                    if final_filepath:
                        logger.info(f"✅ Файл скачан через улучшенный fetch API: {final_filepath}")
                        self.driver.close()
                        self.driver.switch_to.window(self.driver.window_handles[0])
                        return os.path.basename(final_filepath)
                
            except Exception as e:
                logger.debug(f"Улучшенный fetch API скачивание не сработал: {e}")
            
            # Закрываем вкладку
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])
            return False
            
        except Exception as e:
            logger.warning(f"⚠️ Улучшенный JavaScript скачивание не сработал: {e}")
            # Закрываем вкладку при ошибке
            try:
                if len(self.driver.window_handles) > 1:
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
            except:
                pass
            return False
    
    def _download_with_javascript(self, url, filepath):
        """Принудительное скачивание через JavaScript"""
        try:
            logger.info("🔄 Скачивание через JavaScript")
            
            # Открываем URL в новой вкладке
            self.driver.execute_script("window.open('');")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            self.driver.get(url)
            time.sleep(3)
            
            filename = os.path.basename(filepath)
            
            # Метод 1: Создание ссылки для скачивания
            try:
                download_script = """
                var link = document.createElement('a');
                link.href = arguments[0];
                link.download = arguments[1];
                link.target = '_blank';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                """
                
                self.driver.execute_script(download_script, url, filename)
                time.sleep(5)  # Ждем скачивания
                
                # Ищем скачанный файл
                downloaded_file = self._find_downloaded_file(filename)
                if downloaded_file:
                    final_filepath = self._move_file_from_downloads(downloaded_file, filepath)
                    if final_filepath:
                        logger.info(f"✅ Файл скачан через JavaScript: {final_filepath}")
                        self.driver.close()
                        self.driver.switch_to.window(self.driver.window_handles[0])
                        return os.path.basename(final_filepath)
                
            except Exception as e:
                logger.debug(f"JavaScript скачивание не сработало: {e}")
            
            # Метод 2: Fetch API
            try:
                fetch_script = """
                fetch(arguments[0])
                    .then(response => response.blob())
                    .then(blob => {
                        var url = window.URL.createObjectURL(blob);
                        var link = document.createElement('a');
                        link.href = url;
                        link.download = arguments[1];
                        link.click();
                        window.URL.revokeObjectURL(url);
                    });
                """
                
                self.driver.execute_script(fetch_script, url, filename)
                time.sleep(5)  # Ждем скачивания
                
                # Ищем скачанный файл
                downloaded_file = self._find_downloaded_file(filename)
                if downloaded_file:
                    final_filepath = self._move_file_from_downloads(downloaded_file, filepath)
                    if final_filepath:
                        logger.info(f"✅ Файл скачан через fetch API: {final_filepath}")
                        self.driver.close()
                        self.driver.switch_to.window(self.driver.window_handles[0])
                        return os.path.basename(final_filepath)
                
            except Exception as e:
                logger.debug(f"Fetch API скачивание не сработало: {e}")
            
            # Закрываем вкладку
            self.driver.close()
            self.driver.switch_to.window(self.driver.window_handles[0])
            return False
            
        except Exception as e:
            logger.warning(f"⚠️ JavaScript скачивание не сработало: {e}")
            # Закрываем вкладку при ошибке
            try:
                if len(self.driver.window_handles) > 1:
                    self.driver.close()
                    self.driver.switch_to.window(self.driver.window_handles[0])
            except:
                pass
            return False
    
    def _find_downloaded_file(self, expected_filename):
        """Ищет скачанный файл в папке Загрузки"""
        try:
            logger.info(f"🔍 Поиск файла в папке Загрузки: {self.downloads_dir}")
            
            # Ищем файл по точному имени
            file_path = os.path.join(self.downloads_dir, expected_filename)
            if os.path.exists(file_path):
                logger.info(f"✅ Найден файл по точному имени: {file_path}")
                return file_path
            
            # Ищем файл по частичному совпадению (без расширения)
            base_name = os.path.splitext(expected_filename)[0]
            pattern = os.path.join(self.downloads_dir, f"*{base_name}*")
            matches = glob.glob(pattern)
            if matches:
                # Берем самый новый файл
                latest_file = max(matches, key=os.path.getctime)
                logger.info(f"✅ Найден файл по частичному совпадению: {latest_file}")
                return latest_file
            
            # Ищем PDF файлы, скачанные недавно (за последние 60 секунд)
            pdf_pattern = os.path.join(self.downloads_dir, "*.pdf")
            pdf_files = glob.glob(pdf_pattern)
            if pdf_files:
                current_time = time.time()
                recent_files = [f for f in pdf_files if current_time - os.path.getctime(f) < 60]
                if recent_files:
                    latest_file = max(recent_files, key=os.path.getctime)
                    logger.info(f"✅ Найден недавно скачанный PDF: {latest_file}")
                    return latest_file
                else:
                    logger.warning("⚠️ PDF файлы найдены, но ни один не был скачан недавно")
            else:
                logger.warning("⚠️ PDF файлы в папке Загрузки не найдены")
            
            # Логируем содержимое папки для отладки
            try:
                files_in_downloads = os.listdir(self.downloads_dir)
                logger.info(f"📁 Файлы в папке Загрузки: {files_in_downloads[:10]}")  # Показываем первые 10 файлов
            except Exception as e:
                logger.warning(f"⚠️ Не удалось прочитать содержимое папки Загрузки: {e}")
            
            return None
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка поиска скачанного файла: {e}")
            return None
    
    def _move_file_from_downloads(self, source_path, target_path):
        """Перемещает файл из папки Загрузки в целевую папку"""
        try:
            if not os.path.exists(source_path):
                logger.warning(f"⚠️ Исходный файл не найден: {source_path}")
                return None
            
            # Проверяем, что файл не пустой
            file_size = os.path.getsize(source_path)
            if file_size == 0:
                logger.warning(f"⚠️ Файл пустой: {source_path}")
                return None
            
            # Проверяем, что это PDF файл (по содержимому)
            try:
                with open(source_path, 'rb') as f:
                    header = f.read(4)
                    if not header.startswith(b'%PDF'):
                        logger.warning(f"⚠️ Файл не является PDF: {source_path} (заголовок: {header})")
                        # Не возвращаем None, так как это может быть валидный файл с другим заголовком
            except Exception as e:
                logger.warning(f"⚠️ Не удалось проверить заголовок файла: {e}")
            
            # Создаем целевую папку если её нет
            target_dir = os.path.dirname(target_path)
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
            
            # Перемещаем файл
            shutil.move(source_path, target_path)
            logger.info(f"📁 Файл перемещен: {source_path} -> {target_path} (размер: {file_size} байт)")
            return target_path
            
        except Exception as e:
            logger.error(f"❌ Ошибка перемещения файла: {e}")
            return None
    
    def ensure_driver_ready(self):
        """УСТАРЕЛО: WebDriver теперь инициализируется в каждом запросе"""
        logger.warning("⚠️ ensure_driver_ready() устарел - WebDriver инициализируется в parse_case()")
        return True
    
    def parse_case(self, case_number):
        """Основная функция парсинга дела - НОВЫЙ АЛГОРИТМ"""
        # ЖЕСТКОЕ ОГРАНИЧЕНИЕ: только один запуск за раз
        if self.is_processing:
            logger.error("🛑 ПАРСЕР УЖЕ РАБОТАЕТ! Повторный запуск заблокирован!")
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
            
            # ШАГ 3: Обрабатываем ВСЕ файлы по первому найденному делу
            logger.info("📁 ШАГ 3: Обработка файлов")
            case_url, case_text = case_links[0]
            logger.info(f"🔄 Обработка дела: {case_text}")
            
            downloaded_files = []
            
            # Сначала пробуем стандартный метод
            try:
                logger.info("🔍 Попытка стандартного извлечения PDF...")
                downloaded_files = self.download_pdf_files(case_url, case_number)
                logger.info(f"📄 Стандартный метод: найдено {len(downloaded_files)} файлов")
            except Exception as e:
                logger.error(f"❌ Ошибка в стандартном методе: {e}")
            
            # Если стандартный метод не дал результатов, используем альтернативные алгоритмы
            if not downloaded_files:
                logger.info("🔄 Стандартный метод не дал результатов, запуск альтернативных алгоритмов...")
                try:
                    pdf_extractor = PDFExtractionAlgorithms(self.driver, self.files_dir)
                    alternative_files = pdf_extractor.run_all_algorithms(case_number)
                    downloaded_files.extend(alternative_files)
                    logger.info(f"📄 Альтернативные алгоритмы: найдено {len(alternative_files)} файлов")
                except Exception as e:
                    logger.error(f"❌ Ошибка в альтернативных алгоритмах: {e}")
            
            # Если все еще нет файлов, пробуем дополнительные методы
            if not downloaded_files:
                logger.info("🔄 Дополнительные методы поиска PDF...")
                try:
                    additional_files = self._try_additional_pdf_methods(case_url, case_number)
                    downloaded_files.extend(additional_files)
                    logger.info(f"📄 Дополнительные методы: найдено {len(additional_files)} файлов")
                except Exception as e:
                    logger.error(f"❌ Ошибка в дополнительных методах: {e}")
            
            logger.info(f"✅ Обработка завершена. Скачано файлов: {len(downloaded_files)}")
            return downloaded_files
            
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
    
    def get_downloaded_files(self):
        """Возвращает список скачанных файлов"""
        if not os.path.exists(self.files_dir):
            return []
        
        files = []
        for filename in os.listdir(self.files_dir):
            if os.path.isfile(os.path.join(self.files_dir, filename)):
                files.append(filename)
        
        return sorted(files)
    
    def _try_additional_pdf_methods(self, case_url, case_number):
        """Дополнительные методы поиска PDF файлов"""
        logger.info("🔍 Дополнительные методы поиска PDF")
        downloaded_files = []
        
        try:
            # Метод 1: Поиск в исходном коде страницы
            page_source = self.driver.page_source
            pdf_patterns = [
                r'href=["\']([^"\']*\.pdf[^"\']*)["\']',
                r'src=["\']([^"\']*\.pdf[^"\']*)["\']',
                r'data-pdf=["\']([^"\']*\.pdf[^"\']*)["\']',
                r'data-file=["\']([^"\']*\.pdf[^"\']*)["\']',
                r'data-url=["\']([^"\']*\.pdf[^"\']*)["\']'
            ]
            
            pdf_links = []
            for pattern in pdf_patterns:
                matches = re.findall(pattern, page_source, re.IGNORECASE)
                pdf_links.extend(matches)
            
            # Метод 2: Поиск через JavaScript
            js_scripts = [
                "return Array.from(document.querySelectorAll('a[href*=\".pdf\"]')).map(a => a.href);",
                "return Array.from(document.querySelectorAll('[data-pdf]')).map(el => el.getAttribute('data-pdf'));",
                "return Array.from(document.querySelectorAll('[data-file]')).map(el => el.getAttribute('data-file'));"
            ]
            
            for script in js_scripts:
                try:
                    links = self.driver.execute_script(script)
                    if links:
                        pdf_links.extend(links)
                except:
                    continue
            
            # Скачиваем найденные файлы
            for i, link in enumerate(set(pdf_links)):
                try:
                    if link.startswith('//'):
                        link = 'https:' + link
                    elif link.startswith('/'):
                        base_url = '/'.join(case_url.split('/')[:3])
                        link = base_url + link
                    elif not link.startswith('http'):
                        link = urljoin(case_url, link)
                    
                    filename = f"additional_method_{i+1}.pdf"
                    filepath = os.path.join(self.files_dir, filename)
                    
                    response = requests.get(link, timeout=30)
                    if response.status_code == 200 and len(response.content) > 1000:
                        with open(filepath, 'wb') as f:
                            f.write(response.content)
                        downloaded_files.append(filepath)
                        logger.info(f"✅ Дополнительный метод: скачан {filename}")
                    
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка скачивания {link}: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"❌ Ошибка в дополнительных методах: {e}")
        
        return downloaded_files

    def close(self):
        """Закрывает WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("WebDriver закрыт")
            except Exception as e:
                logger.error(f"Ошибка закрытия WebDriver: {e}")
