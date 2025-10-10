"""
Настройки Selenium для автоматического скачивания PDF файлов
Вместо открытия PDF в браузере, файлы будут автоматически скачиваться
"""

import os
import platform
from selenium.webdriver.chrome.options import Options
import undetected_chromedriver as uc

def get_downloads_directory():
    """
    Определяет папку для скачивания файлов с учетом ОС.
    На Windows пробует D:\\DOWNLOADS и стандартные Загрузки.
    На Linux/macOS — ~/Downloads, затем /tmp/kad_downloads.
    """
    system = platform.system().lower()
    if system == "windows":
        download_dirs = [
            "D:\\DOWNLOADS",
            os.path.join(os.path.expanduser("~"), "Downloads"),
            os.path.join(os.path.expanduser("~"), "Загрузки"),
        ]
        for download_dir in download_dirs:
            if os.path.exists(download_dir):
                return download_dir
        # fallback для Windows
        fallback_dir = "D:\\DOWNLOADS"
        try:
            os.makedirs(fallback_dir, exist_ok=True)
            return fallback_dir
        except Exception:
            return os.getcwd()
    else:
        # Linux / macOS
        download_dirs = [
            os.path.join(os.path.expanduser("~"), "Downloads"),
            "/tmp/kad_downloads",
        ]
        for download_dir in download_dirs:
            try:
                if not os.path.exists(download_dir):
                    os.makedirs(download_dir, exist_ok=True)
                return download_dir
            except Exception:
                continue
        return os.getcwd()

def move_downloaded_files(downloads_dir, target_dir, case_number):
    """
    Перемещает скачанные PDF файлы из папки скачивания в целевую папку
    
    Args:
        downloads_dir: Папка где скачались файлы
        target_dir: Целевая папка (backend/files)
        case_number: Номер дела для именования файлов
        
    Returns:
        list: Список путей к перемещенным файлам
    """
    import shutil
    import time
    import glob
    from datetime import datetime
    
    moved_files = []
    
    # Создаем целевую папку если её нет
    os.makedirs(target_dir, exist_ok=True)
    
    # Ждем немного чтобы файлы успели скачаться
    time.sleep(2)
    
    # Ищем PDF файлы в папке скачивания
    pdf_patterns = [
        os.path.join(downloads_dir, "*.pdf"),
        os.path.join(downloads_dir, "*.PDF")
    ]
    
    downloaded_files = []
    for pattern in pdf_patterns:
        downloaded_files.extend(glob.glob(pattern))
    
    if not downloaded_files:
        print(f"⚠️ PDF файлы не найдены в {downloads_dir}")
        return moved_files
    
    print(f"📄 Найдено {len(downloaded_files)} PDF файлов для перемещения")
    
    for i, file_path in enumerate(downloaded_files):
        try:
            # Получаем имя файла
            filename = os.path.basename(file_path)
            
            # Создаем новое имя файла с номером дела и временной меткой
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_case_number = case_number.replace('/', '_').replace('\\', '_')
            new_filename = f"{safe_case_number}_{timestamp}_{i+1}_{filename}"
            
            # Путь к целевому файлу
            target_path = os.path.join(target_dir, new_filename)
            
            # Перемещаем файл
            shutil.move(file_path, target_path)
            moved_files.append(target_path)
            
            print(f"✅ Перемещен: {filename} -> {new_filename}")
            
        except Exception as e:
            print(f"❌ Ошибка перемещения файла {file_path}: {e}")
            continue
    
    return moved_files

def get_download_preferences(downloads_dir):
    """
    Возвращает настройки предпочтений для автоматического скачивания PDF
    
    Args:
        downloads_dir: Путь к папке для скачивания файлов
        
    Returns:
        dict: Словарь с настройками предпочтений Chrome
    """
    return {
        # Основные настройки скачивания
        "download.default_directory": downloads_dir,
        "download.prompt_for_download": False,  # Не спрашивать разрешение на скачивание
        "download.directory_upgrade": True,    # Обновлять папку скачивания
        
        # Настройки для PDF файлов - КЛЮЧЕВЫЕ НАСТРОЙКИ
        "plugins.always_open_pdf_externally": True,  # Всегда скачивать PDF вместо открытия в браузере
        "plugins.plugins_disabled": ["Chrome PDF Viewer"],  # Отключить встроенный просмотрщик PDF
        "profile.default_content_settings.plugins": 1,  # Разрешить плагины
        "profile.content_settings.exceptions.plugins.*.setting": 1,  # Разрешить плагины для всех сайтов
        "profile.default_content_setting_values.plugins": 1,  # Разрешить плагины
        "profile.managed_default_content_settings.plugins": 1,  # Разрешить плагины
        "profile.default_content_setting_values.automatic_downloads": 1,  # Разрешить автоматические скачивания
        "profile.content_settings.exceptions.automatic_downloads.*.setting": 1,  # Разрешить автоматические скачивания для всех сайтов
        
        # Настройки контента
        "profile.default_content_setting_values.notifications": 2,  # Блокировать уведомления
        "profile.default_content_settings.popups": 0,              # Блокировать всплывающие окна
        "profile.managed_default_content_settings.images": 1,      # Разрешить изображения
        
        # Настройки безопасности
        "credentials_enable_service": False,           # Отключить сохранение паролей
        "profile.password_manager_enabled": False,     # Отключить менеджер паролей
        
        # Настройки языка
        "intl.accept_languages": "ru-RU,ru,en-US,en",
        
        # Дополнительные настройки для PDF
        "profile.content_settings.exceptions.automatic_downloads.*.setting": 1,  # Разрешить автоматические скачивания
        "profile.default_content_setting_values.automatic_downloads": 1,        # Разрешить автоматические скачивания
    }

def configure_chrome_options_for_pdf_download(options, downloads_dir):
    """
    Настраивает Chrome Options для автоматического скачивания PDF
    
    Args:
        options: Объект ChromeOptions
        downloads_dir: Путь к папке для скачивания
    """
    # Получаем настройки предпочтений
    prefs = get_download_preferences(downloads_dir)
    
    # Применяем настройки предпочтений
    options.add_experimental_option("prefs", prefs)
    
    # Дополнительные аргументы для отключения встроенного просмотрщика PDF
    pdf_download_args = [
        '--disable-plugins-discovery',           # Отключить обнаружение плагинов
        '--disable-extensions-file-access-check', # Отключить проверку доступа к файлам расширений
        '--disable-extensions-http-throttling',   # Отключить ограничение HTTP для расширений
        '--disable-pdf-extension',               # Отключить расширение PDF
        '--disable-print-preview',               # Отключить предварительный просмотр печати
        '--disable-web-security',                # Отключить веб-безопасность (для обхода CORS)
        '--allow-running-insecure-content',      # Разрешить выполнение небезопасного контента
        '--disable-features=VizDisplayCompositor', # Отключить композитор дисплея
    ]
    
    # Добавляем аргументы
    for arg in pdf_download_args:
        options.add_argument(arg)
    
    # Экспериментальные опции: в некоторых версиях Chrome на Linux они могут вызывать ошибку.
    # Применяем только на Windows.
    if platform.system().lower() == "windows":
        options.add_experimental_option("excludeSwitches", [
            "enable-automation",
            "enable-logging",
            "disable-popup-blocking"
        ])
        options.add_experimental_option('useAutomationExtension', False)

def create_undetected_chrome_options():
    """
    Создает настройки для undetected-chromedriver с поддержкой скачивания PDF
    
    Returns:
        uc.ChromeOptions: Настроенный объект опций
    """
    # Определяем папку для скачивания
    downloads_dir = get_downloads_directory()
    print(f"📁 Папка для скачивания: {downloads_dir}")
    
    options = uc.ChromeOptions()
    
    # Основные антидетект настройки
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    # Применяем experimental options только на Windows
    if platform.system().lower() == "windows":
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
    
    # Настройки для отключения встроенного просмотрщика PDF
    options.add_argument('--disable-plugins-discovery')
    options.add_argument('--disable-pdf-extension')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-plugins')
    options.add_argument('--disable-default-apps')
    
    # Настройки окна
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--start-maximized')
    
    # Настройки стабильности
    options.add_argument('--disable-web-security')
    options.add_argument('--disable-features=VizDisplayCompositor')
    options.add_argument('--disable-ipc-flooding-protection')
    options.add_argument('--disable-renderer-backgrounding')
    options.add_argument('--disable-backgrounding-occluded-windows')
    options.add_argument('--disable-client-side-phishing-detection')
    options.add_argument('--disable-sync')
    options.add_argument('--disable-translate')
    options.add_argument('--disable-background-timer-throttling')
    
    # Настройки для PDF скачивания
    configure_chrome_options_for_pdf_download(options, downloads_dir)
    
    return options

def create_standard_chrome_options():
    """
    Создает стандартные настройки Chrome с поддержкой скачивания PDF
    
    Returns:
        Options: Настроенный объект опций
    """
    # Определяем папку для скачивания
    downloads_dir = get_downloads_directory()
    print(f"📁 Папка для скачивания: {downloads_dir}")
    
    options = Options()
    
    # Основные антидетект настройки
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-blink-features=AutomationControlled')
    # Применяем experimental options только на Windows
    if platform.system().lower() == "windows":
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
    
    # Настройки для отключения встроенного просмотрщика PDF
    options.add_argument('--disable-plugins-discovery')
    options.add_argument('--disable-pdf-extension')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-plugins')
    options.add_argument('--disable-default-apps')
    
    # Настройки окна и производительности
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-gpu')
    options.add_argument('--remote-debugging-port=9222')
    options.add_argument('--disable-web-security')
    options.add_argument('--disable-features=VizDisplayCompositor')
    
    # Настройки для PDF скачивания
    configure_chrome_options_for_pdf_download(options, downloads_dir)
    
    return options

def setup_pdf_download_script(driver):
    """
    Настраивает JavaScript для принудительного скачивания PDF
    
    Args:
        driver: WebDriver объект
    """
    try:
        # Скрипт для принудительного скачивания PDF
        pdf_download_script = """
        // Переопределяем поведение PDF ссылок
        document.addEventListener('click', function(event) {
            const target = event.target;
            const href = target.getAttribute('href') || target.closest('a')?.getAttribute('href');
            
            if (href && (href.includes('.pdf') || href.includes('Document/Pdf'))) {
                event.preventDefault();
                event.stopPropagation();
                
                console.log('PDF ссылка обнаружена, принудительное скачивание:', href);
                
                // Создаем скрытую ссылку для скачивания
                const downloadLink = document.createElement('a');
                downloadLink.href = href;
                downloadLink.download = '';
                downloadLink.style.display = 'none';
                document.body.appendChild(downloadLink);
                downloadLink.click();
                document.body.removeChild(downloadLink);
                
                return false;
            }
        });
        
        // Переопределяем window.open для PDF
        const originalOpen = window.open;
        window.open = function(url, name, specs) {
            if (url && (url.includes('.pdf') || url.includes('Document/Pdf'))) {
                console.log('PDF window.open обнаружен, принудительное скачивание:', url);
                
                const downloadLink = document.createElement('a');
                downloadLink.href = url;
                downloadLink.download = '';
                downloadLink.style.display = 'none';
                document.body.appendChild(downloadLink);
                downloadLink.click();
                document.body.removeChild(downloadLink);
                
                return null;
            }
            return originalOpen.call(this, url, name, specs);
        };
        
        // Переопределяем поведение iframe для PDF
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                mutation.addedNodes.forEach(function(node) {
                    if (node.nodeType === 1) { // Element node
                        if (node.tagName === 'IFRAME' || node.tagName === 'EMBED') {
                            const src = node.getAttribute('src') || node.getAttribute('data');
                            if (src && (src.includes('.pdf') || src.includes('Document/Pdf'))) {
                                console.log('PDF iframe/embed обнаружен, принудительное скачивание:', src);
                                
                                const downloadLink = document.createElement('a');
                                downloadLink.href = src;
                                downloadLink.download = '';
                                downloadLink.style.display = 'none';
                                document.body.appendChild(downloadLink);
                                downloadLink.click();
                                document.body.removeChild(downloadLink);
                            }
                        }
                    }
                });
            });
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
        
        console.log('PDF принудительное скачивание настроено');
        """
        
        # Выполняем скрипт
        driver.execute_script(pdf_download_script)
        print("✅ JavaScript для принудительного скачивания PDF настроен")
        
    except Exception as e:
        print(f"⚠️ Ошибка настройки JavaScript для PDF: {e}")

def test_pdf_download_setup(driver, test_url="https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"):
    """
    Тестирует настройку скачивания PDF
    
    Args:
        driver: WebDriver объект
        test_url: URL тестового PDF файла
    """
    try:
        print("🧪 Тестирование настройки скачивания PDF...")
        
        # Переходим на тестовую страницу
        driver.get(test_url)
        
        # Ждем загрузки
        import time
        time.sleep(3)
        
        # Проверяем, что PDF не открылся в браузере
        current_url = driver.current_url
        if current_url == test_url:
            print("✅ PDF не открылся в браузере (должен был скачаться)")
        else:
            print(f"⚠️ PDF открылся в браузере: {current_url}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка тестирования PDF скачивания: {e}")
        return False
