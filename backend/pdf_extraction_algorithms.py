"""
Новые алгоритмы извлечения PDF файлов
Основаны на примерах из first.py, second.py, third.py и complex.py
"""

import os
import time
import logging
import requests
import json
import re
from io import BytesIO
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.common.exceptions import TimeoutException, NoSuchElementException

logger = logging.getLogger(__name__)

# ЧЕРНЫЙ СПИСОК URL - документы, которые НЕ нужно скачивать
PDF_URL_BLACKLIST = [
    'Content/Политика конфиденциальности.pdf',
    '/Content/Политика конфиденциальности.pdf',
    'https://kad.arbitr.ru/Content/Политика конфиденциальности.pdf',
    'privacy',
    'policy',
    'terms',
    'agreement',
    'cookie',
    'help',
    'manual',
    'instruction'
]

class PDFExtractionAlgorithms:
    """Класс с новыми алгоритмами извлечения PDF"""
    
    def __init__(self, driver, files_dir, downloads_dir=None):
        self.driver = driver
        self.files_dir = files_dir
        self.downloads_dir = downloads_dir
        os.makedirs(files_dir, exist_ok=True)
    
    def _is_blacklisted_url(self, url):
        """
        Проверяет, находится ли URL в черном списке
        
        Args:
            url: URL для проверки
            
        Returns:
            True если URL в черном списке
        """
        if not url:
            return True
        
        url_lower = url.lower()
        
        # Проверяем черный список
        for blacklisted in PDF_URL_BLACKLIST:
            if blacklisted.lower() in url_lower:
                logger.warning(f"🚫 URL в черном списке: {url}")
                return True
        
        return False
    
    def _is_case_document_url(self, url):
        """
        Проверяет, является ли URL документом дела (а не служебным документом)
        
        Args:
            url: URL для проверки
            
        Returns:
            True если это документ дела
        """
        if not url:
            return False
        
        url_lower = url.lower()
        
        # Позитивные индикаторы документа дела
        case_indicators = [
            'document/pdf',
            'kad/pdfdocument',
            'pdfdocument',
            'document/getpdf',
            'getpdf',
            '/card/',
            'caseid',
            'documentid'
        ]
        
        for indicator in case_indicators:
            if indicator in url_lower:
                logger.info(f"✅ Документ дела: {url}")
                return True
        
        # Если нет явных индикаторов, но есть GUID-подобные структуры
        import re
        guid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
        if re.search(guid_pattern, url_lower, re.IGNORECASE):
            logger.info(f"✅ Документ с GUID: {url}")
            return True
        
        logger.debug(f"⚠️ Не похоже на документ дела: {url}")
        return False
    
    def find_pdf_url_direct(self, page_url):
        """
        Алгоритм 1: Поиск прямого URL PDF файла через анализ страницы
        ИСПРАВЛЕН: Учитывает специфику kad.arbitr.ru с POST запросами
        """
        logger.info("🔍 АЛГОРИТМ 1: Поиск прямого URL PDF файла")
        
        try:
            # Проверяем, что мы уже на странице PDF документа
            if '/Document/Pdf/' in page_url and page_url.endswith('.pdf'):
                logger.info("✅ Текущий URL уже является PDF документом")
                return self._download_pdf_via_post(page_url, "current_url", "ALGORITHM_1")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Referer': 'https://kad.arbitr.ru/'
            }
            
            response = requests.get(page_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            logger.info(f"📄 Анализируем HTML страницы (размер: {len(response.text)} символов)")
            
            # Специфичные паттерны для kad.arbitr.ru
            pdf_patterns = [
                # Прямые ссылки на PDF с GUID
                r'href=["\']([^"\']*Document/Pdf/[0-9a-f-]+/[0-9a-f-]+/[^"\']*\.pdf[^"\']*)["\']',
                r'src=["\']([^"\']*Document/Pdf/[0-9a-f-]+/[0-9a-f-]+/[^"\']*\.pdf[^"\']*)["\']',
                
                # JavaScript переменные с PDF URL
                r'var\s+\w*[Pp]df\w*[Uu]rl\s*=\s*["\']([^"\']*Document/Pdf[^"\']*)["\']',
                r'let\s+\w*[Pp]df\w*[Uu]rl\s*=\s*["\']([^"\']*Document/Pdf[^"\']*)["\']',
                r'const\s+\w*[Pp]df\w*[Uu]rl\s*=\s*["\']([^"\']*Document/Pdf[^"\']*)["\']',
                
                # JSON данные
                r'"pdfUrl":\s*["\']([^"\']*Document/Pdf[^"\']*)["\']',
                r'"documentUrl":\s*["\']([^"\']*Document/Pdf[^"\']*)["\']',
                r'"url":\s*["\']([^"\']*Document/Pdf[^"\']*)["\']',
                
                # onclick события
                r'onclick=["\']([^"\']*Document/Pdf[^"\']*)["\']',
                r'onclick=["\']([^"\']*window\.open\(["\']([^"\']*Document/Pdf[^"\']*)["\']',
                
                # data атрибуты
                r'data-pdf-url=["\']([^"\']*Document/Pdf[^"\']*)["\']',
                r'data-document-url=["\']([^"\']*Document/Pdf[^"\']*)["\']',
                r'data-url=["\']([^"\']*Document/Pdf[^"\']*)["\']'
            ]
            
            found_urls = []
            
            for i, pattern in enumerate(pdf_patterns):
                try:
                    matches = re.findall(pattern, response.text, re.IGNORECASE)
                    if matches:
                        logger.info(f"🔍 Паттерн {i+1} нашел {len(matches)} совпадений")
                        for match in matches:
                            if isinstance(match, tuple):
                                match = match[0] if match[0] else match[1]
                            
                            # Очищаем URL
                            url = match.strip()
                            if url and len(url) > 10:  # Минимальная длина URL
                                # Убираем лишние символы
                                url = url.replace('"', '').replace("'", '').replace(')', '').replace('(', '')
                                found_urls.append(url)
                                logger.info(f"📎 Найден URL: {url}")
                except Exception as e:
                    logger.debug(f"Ошибка в паттерне {i+1}: {e}")
                    continue
            
            # Обрабатываем найденные URL
            if found_urls:
                # Убираем дубликаты
                unique_urls = list(set(found_urls))
                logger.info(f"✅ Найдено {len(unique_urls)} уникальных PDF URL")
                
                downloaded_files = []
                for i, pdf_url in enumerate(unique_urls):
                    try:
                        # Преобразуем относительные URL в абсолютные
                        if not pdf_url.startswith('http'):
                            if pdf_url.startswith('/'):
                                base_url = '/'.join(page_url.split('/')[:3])
                                pdf_url = base_url + pdf_url
                            else:
                                pdf_url = page_url.rstrip('/') + '/' + pdf_url
                        
                        # ПРОВЕРКА ЧЕРНОГО СПИСКА
                        if self._is_blacklisted_url(pdf_url):
                            logger.warning(f"🚫 URL {i+1} в черном списке, пропускаем: {pdf_url}")
                            continue
                        
                        # ПРОВЕРКА: Документ дела или служебный документ
                        if not self._is_case_document_url(pdf_url):
                            logger.warning(f"⚠️ URL {i+1} не является документом дела, пропускаем: {pdf_url}")
                            continue
                        
                        # Скачиваем PDF через POST запрос
                        files = self._download_pdf_via_post(pdf_url, f"pattern_{i+1}", "ALGORITHM_1")
                        if files:
                            downloaded_files.extend(files)
                            logger.info(f"✅ URL {i+1} скачан успешно")
                        else:
                            logger.warning(f"⚠️ URL {i+1} не удалось скачать")
                            
                    except Exception as e:
                        logger.error(f"❌ Ошибка обработки URL {i+1}: {e}")
                        continue
                
                return downloaded_files
            else:
                logger.warning("⚠️ PDF URL не найдены в HTML")
                return []
                
        except Exception as e:
            logger.error(f"❌ Ошибка в АЛГОРИТМЕ 1: {e}")
            return []
    
    def extract_pdf_via_selenium(self, page_url):
        """
        Алгоритм 2: Извлечение PDF через Selenium автоматизацию
        ИСПРАВЛЕН: Учитывает Chrome PDF Viewer и Shadow DOM kad.arbitr.ru
        """
        logger.info("🔍 АЛГОРИТМ 2: Извлечение PDF через Selenium")
        
        try:
            # Используем существующий driver вместо создания нового
            if not self.driver:
                logger.warning("⚠️ WebDriver не инициализирован")
                return []
            
            logger.info(f"🌐 Переходим на страницу: {page_url}")
            self.driver.get(page_url)
            
            # Ждем загрузки страницы с увеличенным таймаутом
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Дополнительная пауза для загрузки Shadow DOM
            time.sleep(1.5)
            
            downloaded_files = []
            
            # Метод 1: Поиск через JavaScript в Shadow DOM (специфично для kad.arbitr.ru)
            try:
                logger.info("🔄 Поиск PDF через JavaScript в Shadow DOM")
                
                # Выполняем JavaScript для поиска PDF в Shadow DOM
                js_script = """
                function findPdfInShadowDOM() {
                    console.log('Поиск PDF в Shadow DOM kad.arbitr.ru...');
                    
                    // Ищем template с shadowrootmode="closed"
                    const templates = document.querySelectorAll('template[shadowrootmode="closed"]');
                    console.log('Найдено template с shadowrootmode:', templates.length);
                    
                    for (let i = 0; i < templates.length; i++) {
                        const template = templates[i];
                        console.log('Template', i, ':', template.innerHTML.substring(0, 200));
                        
                        // Ищем iframe в template
                        const iframe = template.querySelector('iframe[type="application/pdf"]');
                        if (iframe) {
                            const src = iframe.getAttribute('src');
                            console.log('Найден PDF iframe в template:', src);
                            
                            if (src && src !== 'about:blank') {
                                return src;
                            }
                        }
                    }
                    
                    // Ищем embed элементы
                    const embeds = document.querySelectorAll('embed[type="application/pdf"], embed[type="application/x-google-chrome-pdf"]');
                    console.log('Найдено embed элементов:', embeds.length);
                    
                    for (let i = 0; i < embeds.length; i++) {
                        const embed = embeds[i];
                        const src = embed.getAttribute('src');
                        const originalUrl = embed.getAttribute('original-url');
                        
                        console.log('Embed', i, 'src:', src, 'original-url:', originalUrl);
                        
                        if (originalUrl) {
                            return originalUrl;
                        } else if (src && src !== 'about:blank') {
                            return src;
                        }
                    }
                    
                    // Поиск по всем iframe
                    const iframes = document.querySelectorAll('iframe');
                    console.log('Найдено iframe:', iframes.length);
                    
                    for (let i = 0; i < iframes.length; i++) {
                        const iframe = iframes[i];
                        const src = iframe.get_attribute('src');
                        const type = iframe.getAttribute('type');
                        
                        console.log('iframe', i, 'src:', src, 'type:', type);
                        
                        if (src && src !== 'about:blank' && 
                            (type === 'application/pdf' || src.includes('pdf') || src.includes('Document'))) {
                            return src;
                        }
                    }
                    
                    return null;
                }
                
                return findPdfInShadowDOM();
                """
                
                pdf_url = self.driver.execute_script(js_script)
                
                if pdf_url:
                    logger.info(f"✅ Найден PDF URL через JavaScript: {pdf_url}")
                    files = self._download_pdf_via_post(pdf_url, "selenium_js", "ALGORITHM_2")
                    if files:
                        downloaded_files.extend(files)
                else:
                    logger.warning("⚠️ PDF URL не найден через JavaScript")
                    
            except Exception as e:
                logger.warning(f"⚠️ Ошибка поиска через JavaScript: {e}")
            
            # Метод 2: Поиск кнопки #save
            try:
                logger.info("🔄 Поиск кнопки #save")
                
                save_button = self.driver.find_element(By.CSS_SELECTOR, "#save")
                if save_button and save_button.is_displayed():
                    logger.info("✅ Найдена кнопка #save")
                    
                    # Получаем текущий URL страницы (это и есть PDF URL)
                    current_url = self.driver.current_url
                    if '/Document/Pdf/' in current_url:
                        logger.info(f"✅ Текущий URL является PDF документом: {current_url}")
                        files = self._download_pdf_via_post(current_url, "save_button", "ALGORITHM_2")
                        if files:
                            downloaded_files.extend(files)
                else:
                    logger.warning("⚠️ Кнопка #save не найдена или не видна")
                    
            except Exception as e:
                logger.warning(f"⚠️ Ошибка поиска кнопки #save: {e}")
            
            # Метод 3: Поиск через анализ iframe
            try:
                logger.info("🔄 Поиск PDF через анализ iframe")
                
                iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
                logger.info(f"📄 Найдено {len(iframes)} iframe элементов")
                
                for i, iframe in enumerate(iframes):
                    try:
                        src = iframe.get_attribute('src')
                        iframe_type = iframe.get_attribute('type')
                        logger.info(f"🔍 iframe {i+1}: src={src}, type={iframe_type}")
                        
                        if src and src != 'about:blank':
                            if iframe_type == 'application/pdf' or 'pdf' in src.lower() or 'Document' in src:
                                logger.info(f"✅ Найден PDF iframe: {src}")
                                files = self._download_pdf_via_post(src, f"iframe_{i+1}", "ALGORITHM_2")
                                if files:
                                    downloaded_files.extend(files)
                    except Exception as e:
                        logger.warning(f"⚠️ Ошибка анализа iframe {i+1}: {e}")
                        continue
                        
            except Exception as e:
                logger.warning(f"⚠️ Ошибка поиска через iframe: {e}")
            
            # Метод 4: Поиск кнопок скачивания
            try:
                logger.info("🔄 Поиск кнопок скачивания PDF")
                
                download_selectors = [
                    "button[onclick*='pdf']",
                    "a[href*='pdf']",
                    "button[onclick*='Document']",
                    "a[href*='Document']",
                    ".download-pdf",
                    "#download-pdf",
                    "button[title*='скачать']",
                    "a[title*='скачать']",
                    "button[title*='Скачать']",
                    "a[title*='Скачать']"
                ]
                
                for selector in download_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for element in elements:
                            try:
                                href = element.get_attribute('href')
                                onclick = element.get_attribute('onclick')
                                
                                if href and 'pdf' in href.lower():
                                    logger.info(f"✅ Найдена ссылка на PDF: {href}")
                                    files = self._download_pdf_via_post(href, "download_link", "ALGORITHM_2")
                                    if files:
                                        downloaded_files.extend(files)
                                        
                                elif onclick and ('pdf' in onclick.lower() or 'Document' in onclick):
                                    logger.info(f"✅ Найдена кнопка PDF: {onclick}")
                                    # Извлекаем URL из onclick
                                    url_match = re.search(r'["\']([^"\']*Document/Pdf[^"\']*)["\']', onclick)
                                    if url_match:
                                        pdf_url = url_match.group(1)
                                        files = self._download_pdf_via_post(pdf_url, "download_button", "ALGORITHM_2")
                                        if files:
                                            downloaded_files.extend(files)
                            except Exception as e:
                                logger.debug(f"Ошибка обработки элемента: {e}")
                                continue
                    except Exception as e:
                        logger.debug(f"Ошибка с селектором {selector}: {e}")
                        continue
                        
            except Exception as e:
                logger.warning(f"⚠️ Ошибка поиска кнопок скачивания: {e}")
            
            return downloaded_files
            
        except Exception as e:
            logger.error(f"❌ Ошибка в АЛГОРИТМЕ 2: {e}")
            return []
    
    def find_pdf_in_network_requests(self, page_url):
        """
        Алгоритм 3: Перехват сетевых запросов
        ИСПРАВЛЕН: Использует Chrome DevTools Protocol для перехвата POST запросов к PDF
        """
        logger.info("🔍 АЛГОРИТМ 3: Перехват сетевых запросов")
        
        try:
            if not self.driver:
                logger.warning("⚠️ WebDriver не инициализирован")
                return []
            
            logger.info(f"🌐 Переходим на страницу: {page_url}")
            self.driver.get(page_url)
            
            # Ждем загрузки страницы
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Включаем перехват сетевых запросов через CDP
            logger.info("🔄 Включаем перехват сетевых запросов через CDP...")
            
            try:
                # Включаем Network domain
                self.driver.execute_cdp_cmd('Network.enable', {})
                logger.info("✅ Network domain включен")
                
            except Exception as e:
                logger.warning(f"⚠️ Не удалось включить CDP перехват: {e}")
            
            # Альтернативный метод: перехват через JavaScript
            logger.info("🔄 Перехват через JavaScript...")
            
            js_script = """
            const originalFetch = window.fetch;
            const interceptedRequests = [];
            
            // Перехватываем fetch запросы
            window.fetch = function(...args) {
                const url = args[0];
                const options = args[1] || {};
                
                console.log('Перехвачен fetch запрос:', url, options);
                
                // Сохраняем запросы к PDF
                if (url.includes('Document/Pdf') || url.includes('.pdf')) {
                    interceptedRequests.push({
                        url: url,
                        method: options.method || 'GET',
                        headers: options.headers || {},
                        body: options.body
                    });
                }
                
                return originalFetch.apply(this, args);
            };
            
            // Перехватываем XMLHttpRequest
            const originalXHR = window.XMLHttpRequest;
            window.XMLHttpRequest = function() {
                const xhr = new originalXHR();
                const originalOpen = xhr.open;
                const originalSend = xhr.send;
                
                xhr.open = function(method, url, ...args) {
                    console.log('Перехвачен XHR запрос:', method, url);
                    
                    // Сохраняем запросы к PDF
                    if (url.includes('Document/Pdf') || url.includes('.pdf')) {
                        interceptedRequests.push({
                            url: url,
                            method: method,
                            headers: {},
                            body: null
                        });
                    }
                    
                    return originalOpen.apply(this, [method, url, ...args]);
                };
                
                xhr.send = function(data) {
                    console.log('XHR отправка данных:', data);
                    return originalSend.apply(this, [data]);
                };
                
                return xhr;
            };
            
            // Сохраняем массив в глобальной области
            window.interceptedRequests = interceptedRequests;
            
            return interceptedRequests.length;
            """
            
            # Выполняем скрипт перехвата
            initial_count = self.driver.execute_script(js_script)
            logger.info(f"📊 Начальное количество перехваченных запросов: {initial_count}")
            
            # Ждем перехвата запросов (PDF загружается автоматически)
            logger.info("⏳ Ожидание перехвата PDF запросов...")
            time.sleep(3)
            
            # Получаем перехваченные запросы
            intercepted_requests = self.driver.execute_script("return window.interceptedRequests || [];")
            
            if intercepted_requests:
                logger.info(f"✅ Перехвачено {len(intercepted_requests)} PDF запросов")
                
                downloaded_files = []
                
                for i, request in enumerate(intercepted_requests):
                    try:
                        url = request.get('url', '')
                        method = request.get('method', 'GET')
                        
                        logger.info(f"🔍 Запрос {i+1}: {method} {url}")
                        
                        # Скачиваем через перехваченный URL
                        if method.upper() == 'POST':
                            # Для POST запросов используем специальный метод
                            files = self._download_pdf_via_post(url, f"network_post_{i+1}", "ALGORITHM_3")
                        else:
                            # Для GET запросов используем обычный метод
                            files = self._download_pdf_direct(url, f"network_get_{i+1}", "ALGORITHM_3")
                        
                        if files:
                            downloaded_files.extend(files)
                            logger.info(f"✅ Запрос {i+1} обработан успешно")
                        else:
                            logger.warning(f"⚠️ Запрос {i+1} не дал результатов")
                                
                    except Exception as e:
                        logger.warning(f"⚠️ Ошибка обработки запроса {i+1}: {e}")
                        continue
                
                return downloaded_files
            else:
                logger.warning("⚠️ PDF запросы не перехвачены")
                
                # Fallback: попробуем найти PDF URL в текущей странице
                logger.info("🔄 Fallback: поиск PDF URL на странице...")
                current_url = self.driver.current_url
                if '/Document/Pdf/' in current_url:
                    logger.info(f"✅ Текущий URL является PDF: {current_url}")
                    files = self._download_pdf_via_post(current_url, "current_url_fallback", "ALGORITHM_3")
                    return files if files else []
                
                return []
                
        except Exception as e:
            logger.error(f"❌ Ошибка в АЛГОРИТМЕ 3: {e}")
            return []
    
    def find_pdf_via_api_requests(self, page_url):
        """
        Алгоритм 4: Поиск PDF через API запросы
        ИСПРАВЛЕН: Использует POST запросы для kad.arbitr.ru
        """
        logger.info("🔍 АЛГОРИТМ 4: Поиск PDF через API запросы")
        
        try:
            if not self.driver:
                logger.warning("⚠️ WebDriver не инициализирован")
                return []
            
            logger.info(f"🌐 Переходим на страницу: {page_url}")
            self.driver.get(page_url)
            
            # Ждем загрузки страницы
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            downloaded_files = []
            
            # Метод 1: Поиск PDF URL на странице
            try:
                logger.info("🔄 Поиск PDF URL на странице")
                
                # Ищем все ссылки на PDF
                pdf_links = self.driver.find_elements(By.CSS_SELECTOR, "a[href*='Document/Pdf'], a[href*='.pdf']")
                logger.info(f"📄 Найдено {len(pdf_links)} ссылок на PDF")
                
                for i, link in enumerate(pdf_links):
                    try:
                        href = link.get_attribute('href')
                        if href and '/Document/Pdf/' in href:
                            logger.info(f"📥 API запрос {i+1}: {href}")
                            
                            # Проверки
                            if self._is_blacklisted_url(href):
                                logger.warning(f"🚫 URL {i+1} в черном списке")
                                continue
                            
                            if not self._is_case_document_url(href):
                                logger.warning(f"⚠️ URL {i+1} не является документом дела")
                                continue
                            
                            # Скачиваем через POST
                            files = self._download_pdf_via_post(href, f"api_link_{i+1}", "ALGORITHM_4")
                            if files:
                                downloaded_files.extend(files)
                                logger.info(f"✅ API запрос {i+1} успешен")
                            else:
                                logger.warning(f"⚠️ API запрос {i+1} не дал результатов")
                                
                    except Exception as e:
                        logger.warning(f"⚠️ Ошибка API запроса {i+1}: {e}")
                        continue
                        
            except Exception as e:
                logger.warning(f"⚠️ Ошибка поиска PDF ссылок: {e}")
            
            # Метод 2: Прямые POST запросы к PDF URL
            try:
                logger.info("🔄 Прямые POST запросы к PDF URL")
                
                # Если текущий URL уже является PDF документом
                current_url = self.driver.current_url
                if '/Document/Pdf/' in current_url:
                    logger.info(f"✅ Текущий URL является PDF документом: {current_url}")
                    
                    # Проверки
                    if not self._is_blacklisted_url(current_url):
                        if self._is_case_document_url(current_url):
                            files = self._download_pdf_via_post(current_url, "current_url_api", "ALGORITHM_4")
                            if files:
                                downloaded_files.extend(files)
                                logger.info("✅ Прямой POST запрос успешен")
                        else:
                            logger.warning("⚠️ Текущий URL не является документом дела")
                    else:
                        logger.warning("🚫 Текущий URL в черном списке")
                
            except Exception as e:
                logger.warning(f"⚠️ Ошибка прямых POST запросов: {e}")
            
            # Метод 3: Поиск через JavaScript переменные
            try:
                logger.info("🔄 Поиск PDF URL через JavaScript переменные")
                
                js_script = """
                function findPdfUrlsInJS() {
                    const pdfUrls = [];
                    
                    // Ищем в глобальных переменных
                    const globalVars = ['pdfUrl', 'documentUrl', 'fileUrl', 'downloadUrl'];
                    for (let varName of globalVars) {
                        if (window[varName] && typeof window[varName] === 'string') {
                            if (window[varName].includes('Document/Pdf')) {
                                pdfUrls.push(window[varName]);
                                console.log('Найден PDF URL в глобальной переменной', varName, ':', window[varName]);
                            }
                        }
                    }
                    
                    // Ищем в data атрибутах
                    const elements = document.querySelectorAll('[data-pdf-url], [data-document-url], [data-file-url]');
                    for (let element of elements) {
                        const pdfUrl = element.getAttribute('data-pdf-url') || 
                                     element.getAttribute('data-document-url') || 
                                     element.getAttribute('data-file-url');
                        if (pdfUrl && pdfUrl.includes('Document/Pdf')) {
                            pdfUrls.push(pdfUrl);
                            console.log('Найден PDF URL в data атрибуте:', pdfUrl);
                        }
                    }
                    
                    // Ищем в onclick событиях
                    const onclickElements = document.querySelectorAll('[onclick*="Document"], [onclick*="Pdf"]');
                    for (let element of onclickElements) {
                        const onclick = element.getAttribute('onclick');
                        if (onclick) {
                            const urlMatch = onclick.match(/['"]([^'"]*Document/Pdf[^'"]*)['"]/);
                            if (urlMatch) {
                                pdfUrls.push(urlMatch[1]);
                                console.log('Найден PDF URL в onclick:', urlMatch[1]);
                            }
                        }
                    }
                    
                    return [...new Set(pdfUrls)]; // Убираем дубликаты
                }
                
                return findPdfUrlsInJS();
                """
                
                js_pdf_urls = self.driver.execute_script(js_script)
                
                if js_pdf_urls:
                    logger.info(f"✅ Найдено {len(js_pdf_urls)} PDF URL в JavaScript")
                    
                    for i, pdf_url in enumerate(js_pdf_urls):
                        try:
                            # Преобразуем относительные URL в абсолютные
                            if not pdf_url.startswith('http'):
                                if pdf_url.startswith('/'):
                                    base_url = '/'.join(page_url.split('/')[:3])
                                    full_url = base_url + pdf_url
                                else:
                                    full_url = page_url.rstrip('/') + '/' + pdf_url
                            else:
                                full_url = pdf_url
                            
                            logger.info(f"📥 JavaScript API запрос {i+1}: {full_url}")
                            
                            # Проверки
                            if self._is_blacklisted_url(full_url):
                                logger.warning(f"🚫 URL {i+1} в черном списке")
                                continue
                            
                            if not self._is_case_document_url(full_url):
                                logger.warning(f"⚠️ URL {i+1} не является документом дела")
                                continue
                            
                            # Скачиваем через POST
                            files = self._download_pdf_via_post(full_url, f"js_api_{i+1}", "ALGORITHM_4")
                            if files:
                                downloaded_files.extend(files)
                                logger.info(f"✅ JavaScript API запрос {i+1} успешен")
                            else:
                                logger.warning(f"⚠️ JavaScript API запрос {i+1} не дал результатов")
                                
                        except Exception as e:
                            logger.warning(f"⚠️ Ошибка JavaScript API запроса {i+1}: {e}")
                            continue
                else:
                    logger.warning("⚠️ PDF URL не найдены в JavaScript")
                    
            except Exception as e:
                logger.warning(f"⚠️ Ошибка поиска в JavaScript: {e}")
            
            if downloaded_files:
                logger.info(f"✅ АЛГОРИТМ 4 завершен: найдено {len(downloaded_files)} файлов")
            else:
                logger.warning("⚠️ АЛГОРИТМ 4 не дал результатов")
            
            return downloaded_files
            
        except Exception as e:
            logger.error(f"❌ Ошибка в АЛГОРИТМЕ 4: {e}")
            return []
    
    def comprehensive_pdf_extraction(self, page_url):
        """
        Алгоритм 5: Комплексный подход
        Основан на complex.py
        """
        logger.info("🔍 АЛГОРИТМ 5: Комплексный подход")
        
        try:
            all_files = []
            
            # 1. Пытаемся найти прямой URL через анализ страницы
            logger.info("🔄 Комплексный подход: Поиск прямого URL")
            direct_files = self.find_pdf_url_direct(page_url)
            if direct_files:
                all_files.extend(direct_files)
                logger.info(f"✅ Комплексный подход: прямой URL найден {len(direct_files)} файлов")
                # ЛОГИРОВАНИЕ: Проверяем реально ли скачаны файлы
                for f in direct_files:
                    if os.path.exists(f):
                        size = os.path.getsize(f)
                        logger.info(f"📦 Файл существует: {os.path.basename(f)} ({size} байт)")
                    else:
                        logger.error(f"❌ Файл НЕ существует: {f}")
            
            # 2. Пытаемся найти через сетевые запросы Selenium
            logger.info("🔄 Комплексный подход: Перехват сетевых запросов")
            network_files = self.find_pdf_in_network_requests(page_url)
            if network_files:
                all_files.extend(network_files)
                logger.info(f"✅ Комплексный подход: сетевые запросы найдены {len(network_files)} файлов")
                # ЛОГИРОВАНИЕ: Проверяем реально ли скачаны файлы
                for f in network_files:
                    if os.path.exists(f):
                        size = os.path.getsize(f)
                        logger.info(f"📦 Файл существует: {os.path.basename(f)} ({size} байт)")
                    else:
                        logger.error(f"❌ Файл НЕ существует: {f}")
            
            # 3. Пытаемся извлечь через Selenium автоматизацию
            logger.info("🔄 Комплексный подход: Selenium автоматизация")
            selenium_files = self.extract_pdf_via_selenium(page_url)
            if selenium_files:
                all_files.extend(selenium_files)
                logger.info(f"✅ Комплексный подход: Selenium найден {len(selenium_files)} файлов")
                # ЛОГИРОВАНИЕ: Проверяем реально ли скачаны файлы
                for f in selenium_files:
                    if os.path.exists(f):
                        size = os.path.getsize(f)
                        logger.info(f"📦 Файл существует: {os.path.basename(f)} ({size} байт)")
                    else:
                        logger.error(f"❌ Файл НЕ существует: {f}")
            
            # 4. Пытаемся найти через API запросы
            logger.info("🔄 Комплексный подход: API запросы")
            api_files = self.find_pdf_via_api_requests(page_url)
            if api_files:
                all_files.extend(api_files)
                logger.info(f"✅ Комплексный подход: API запросы найдены {len(api_files)} файлов")
                # ЛОГИРОВАНИЕ: Проверяем реально ли скачаны файлы
                for f in api_files:
                    if os.path.exists(f):
                        size = os.path.getsize(f)
                        logger.info(f"📦 Файл существует: {os.path.basename(f)} ({size} байт)")
                    else:
                        logger.error(f"❌ Файл НЕ существует: {f}")
            
            if all_files:
                logger.info(f"✅ АЛГОРИТМ 5 завершен: найдено {len(all_files)} файлов")
                return all_files
            else:
                logger.warning("⚠️ АЛГОРИТМ 5 не дал результатов")
                return []
            
        except Exception as e:
            logger.error(f"❌ Ошибка в АЛГОРИТМЕ 5: {e}")
            return []
    
    def _download_pdf_direct(self, pdf_url, method_name, algorithm_name="unknown"):
        """
        Скачивает PDF по прямому URL с указанием алгоритма в названии
        """
        try:
            # Проверяем, что URL не пустой и валидный
            if not pdf_url or len(pdf_url.strip()) < 5:
                logger.warning(f"⚠️ Пустой или невалидный URL: {pdf_url}")
                return []
            
            # Нормализуем URL
            pdf_url = pdf_url.strip()
            if not pdf_url.startswith('http'):
                logger.warning(f"⚠️ Относительный URL не поддерживается: {pdf_url}")
                return []
            
            # ЛОГИРОВАНИЕ URL страницы
            try:
                current_page_url = self.driver.current_url if self.driver else "N/A"
                logger.info(f"📍 [URL LOG] Текущая страница: {current_page_url}")
                logger.info(f"📥 [URL LOG] Скачивание с URL: {pdf_url}")
                logger.info(f"🔧 [URL LOG] Алгоритм: {algorithm_name}, Метод: {method_name}")
            except Exception as e:
                logger.debug(f"Ошибка получения текущего URL: {e}")
            
            logger.info(f"📥 Скачивание PDF через {algorithm_name}: {pdf_url}")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/pdf,application/octet-stream,*/*',
                'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            response = requests.get(pdf_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Проверяем, что это действительно PDF
            content_type = response.headers.get('content-type', '').lower()
            if 'pdf' not in content_type and not response.content.startswith(b'%PDF'):
                logger.warning(f"⚠️ Файл не является PDF (Content-Type: {content_type}): {pdf_url}")
                return []
            
            # Проверяем размер файла
            if len(response.content) < 1000:  # Минимум 1KB
                logger.warning(f"⚠️ Файл слишком мал ({len(response.content)} байт): {pdf_url}")
                return []
            
            # Генерируем уникальное имя файла с хешем URL для избежания дубликатов
            import hashlib
            url_hash = hashlib.md5(pdf_url.encode()).hexdigest()[:8]
            filename = f"{algorithm_name}_{method_name}_{url_hash}.pdf"
            filepath = os.path.join(self.files_dir, filename)
            
            # Проверяем, не скачивали ли мы уже этот файл
            if os.path.exists(filepath):
                existing_size = os.path.getsize(filepath)
                if existing_size == len(response.content):
                    logger.info(f"ℹ️ Файл уже существует с тем же размером: {filename}")
                    return [filepath]
            
            # Сохраняем файл
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            final_filename = os.path.basename(filepath)
            logger.info(f"✅ PDF сохранен через {algorithm_name}: {final_filename} ({len(response.content)} байт)")
            return [filepath]
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"⚠️ Ошибка HTTP запроса через {algorithm_name} {pdf_url}: {e}")
            return []
        except Exception as e:
            logger.error(f"❌ Ошибка скачивания через {algorithm_name} {pdf_url}: {e}")
            return []
    
    def _download_pdf_via_post(self, pdf_url, method_name, algorithm_name="unknown"):
        """
        Скачивает PDF через POST запрос (специфично для kad.arbitr.ru)
        ОБНОВЛЕНО: Использует точные заголовки и данные из анализа сети
        """
        try:
            # Проверяем, что URL не пустой и валидный
            if not pdf_url or len(pdf_url.strip()) < 5:
                logger.warning(f"⚠️ [POST] Пустой или невалидный URL: {pdf_url}")
                return []
            
            # Нормализуем URL
            pdf_url = pdf_url.strip()
            if not pdf_url.startswith('http'):
                logger.warning(f"⚠️ [POST] Относительный URL не поддерживается: {pdf_url}")
                return []
            
            logger.info(f"📥 [POST] Запрос PDF через {algorithm_name}: {pdf_url}")
            
            # Точные заголовки из анализа сети
            headers = {
                'authority': 'kad.arbitr.ru',
                'method': 'POST',
                'scheme': 'https',
                'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'accept-encoding': 'gzip, deflate, br, zstd',
                'accept-language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
                'cache-control': 'no-cache',
                'content-type': 'application/x-www-form-urlencoded',
                'origin': 'https://kad.arbitr.ru',
                'pragma': 'no-cache',
                'priority': 'u=0, i',
                'referer': pdf_url,  # Используем тот же URL как referer
                'sec-ch-ua': '"Chromium";v="140", "Not=A?Brand";v="24", "Google Chrome";v="140"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'document',
                'sec-fetch-mode': 'navigate',
                'sec-fetch-site': 'same-origin',
                'upgrade-insecure-requests': '1',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36'
            }
            
            # Получаем cookies из браузера
            try:
                cookies = self.driver.get_cookies()
                cookie_dict = {cookie['name']: cookie['value'] for cookie in cookies}
                logger.info(f"🍪 [POST] Используем {len(cookie_dict)} cookies из браузера")
            except Exception as e:
                logger.warning(f"⚠️ [POST] Не удалось получить cookies: {e}")
                cookie_dict = {}
            
            # Пробуем разные POST данные на основе анализа
            post_data_variants = [
                # Вариант 1: Пустые данные (как в анализе)
                {},
                # Вариант 2: isAddStamp=True (из URL параметра)
                {'isAddStamp': 'True'},
                # Вариант 3: Пустые данные с content-length: 60 (как в анализе)
                {'': ''},
                # Вариант 4: Комбинация параметров
                {'isAddStamp': 'True', 'format': 'pdf'},
                # Вариант 5: Дополнительные параметры
                {'download': 'true', 'isAddStamp': 'True'},
            ]
            
            for i, post_data in enumerate(post_data_variants):
                try:
                    logger.info(f"🔄 [POST] Вариант {i+1}: {post_data}")
                    
                    # Выполняем POST запрос
                    response = requests.post(
                        pdf_url, 
                        headers=headers, 
                        data=post_data, 
                        cookies=cookie_dict,
                        timeout=30,
                        allow_redirects=True
                    )
                    
                    # Подробное логирование ответа
                    logger.info(f"📊 [POST] Вариант {i+1} - Статус: {response.status_code}")
                    logger.info(f"📊 [POST] Вариант {i+1} - Content-Type: {response.headers.get('content-type', 'N/A')}")
                    logger.info(f"📊 [POST] Вариант {i+1} - Content-Length: {response.headers.get('content-length', 'N/A')}")
                    logger.info(f"📊 [POST] Вариант {i+1} - Server: {response.headers.get('server', 'N/A')}")
                    logger.info(f"📊 [POST] Вариант {i+1} - Размер ответа: {len(response.content)} байт")
                    
                    # Проверяем статус код
                    if response.status_code != 200:
                        logger.warning(f"⚠️ [POST] Вариант {i+1} - Неуспешный статус: {response.status_code}")
                        logger.warning(f"⚠️ [POST] Вариант {i+1} - Ответ сервера: {response.text[:500]}")
                        continue
                    
                    # Проверяем, что это действительно PDF
                    content_type = response.headers.get('content-type', '').lower()
                    is_pdf_content = 'pdf' in content_type or response.content.startswith(b'%PDF')
                    
                    logger.info(f"📄 [POST] Вариант {i+1} - PDF контент: {is_pdf_content}")
                    logger.info(f"📄 [POST] Вариант {i+1} - Начало файла: {response.content[:50]}")
                    
                    if is_pdf_content:
                        logger.info(f"✅ [POST] Вариант {i+1} успешен: {content_type}")
                        
                        # Проверяем размер файла
                        if len(response.content) < 1000:  # Минимум 1KB
                            logger.warning(f"⚠️ [POST] Вариант {i+1} - Файл слишком мал ({len(response.content)} байт)")
                            continue
                        
                        # Генерируем уникальное имя файла
                        import hashlib
                        url_hash = hashlib.md5(pdf_url.encode()).hexdigest()[:8]
                        filename = f"{algorithm_name}_{method_name}_post_{url_hash}.pdf"
                        filepath = os.path.join(self.files_dir, filename)
                        
                        # Сохраняем файл
                        with open(filepath, 'wb') as f:
                            f.write(response.content)
                        
                        final_filename = os.path.basename(filepath)
                        logger.info(f"✅ [POST] PDF сохранен через {algorithm_name}: {final_filename} ({len(response.content)} байт)")
                        return [filepath]
                    else:
                        logger.warning(f"⚠️ [POST] Вариант {i+1} - Не PDF контент: {content_type}")
                        logger.warning(f"⚠️ [POST] Вариант {i+1} - Начало ответа: {response.text[:200]}")
                        continue
                        
                except requests.exceptions.RequestException as e:
                    logger.error(f"❌ [POST] Вариант {i+1} - Ошибка запроса: {e}")
                    continue
                except Exception as e:
                    logger.error(f"❌ [POST] Вариант {i+1} - Неожиданная ошибка: {e}")
                    continue
            
            # Если POST не сработал, пробуем GET
            logger.warning("🔄 [POST] Все POST варианты не сработали, пробуем GET...")
            return self._download_pdf_direct(pdf_url, method_name, algorithm_name)
            
        except Exception as e:
            logger.error(f"❌ [POST] Критическая ошибка POST скачивания через {algorithm_name} {pdf_url}: {e}")
            import traceback
            logger.error(f"❌ [POST] Traceback: {traceback.format_exc()}")
            return []
    
    def run_all_algorithms(self, case_number):
        """
        Запуск всех алгоритмов извлечения PDF последовательно
        ОБНОВЛЕНО: Подробное логирование ошибок и ответов сервера
        """
        logger.info("🚀 Запуск ВСЕХ алгоритмов извлечения PDF")
        logger.info("=" * 80)
        
        # Получаем URL текущей страницы
        try:
            page_url = self.driver.current_url
            logger.info(f"📍 Текущая страница: {page_url}")
        except Exception as e:
            logger.error(f"❌ Не удалось получить URL текущей страницы: {e}")
            return []
        
        # ПРОВЕРКА: Если мы уже на странице PDF документа, попробуем скачать напрямую
        if '/Document/Pdf/' in page_url or page_url.endswith('.pdf'):
            logger.info("🎯 Обнаружена прямая ссылка на PDF документ!")
            logger.info(f"🔗 URL документа: {page_url}")
            
            # Попробуем скачать прямым запросом
            try:
                logger.info("📥 Попытка прямого скачивания по URL страницы...")
                direct_files = self._download_pdf_direct(page_url, "direct_page_url", "DIRECT_LINK")
                if direct_files:
                    logger.info(f"✅ Прямое скачивание успешно: {len(direct_files)} файлов")
                    # Продолжаем с остальными алгоритмами для максимального покрытия
            except Exception as e:
                logger.warning(f"⚠️ Прямое скачивание не удалось: {e}")
                import traceback
                logger.warning(f"⚠️ Traceback: {traceback.format_exc()}")
    
        all_downloaded_files = []
        
        # Алгоритм 1: Поиск прямого URL
        try:
            logger.info("🔄 АЛГОРИТМ 1: Поиск прямого URL")
            logger.info("-" * 50)
            files = self.find_pdf_url_direct(page_url)
            if files:
                all_downloaded_files.extend(files)
                logger.info(f"✅ АЛГОРИТМ 1 завершен: найдено {len(files)} файлов")
                for i, file_path in enumerate(files, 1):
                    if os.path.exists(file_path):
                        size = os.path.getsize(file_path)
                        logger.info(f"   📄 Файл {i}: {os.path.basename(file_path)} ({size} байт)")
                    else:
                        logger.warning(f"   ❌ Файл {i} не существует: {file_path}")
            else:
                logger.warning("⚠️ АЛГОРИТМ 1 не дал результатов")
        except Exception as e:
            logger.error(f"❌ Ошибка в АЛГОРИТМЕ 1: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
        
        # Алгоритм 2: Selenium автоматизация
        try:
            logger.info("🔄 АЛГОРИТМ 2: Selenium автоматизация")
            logger.info("-" * 50)
            files = self.extract_pdf_via_selenium(page_url)
            if files:
                all_downloaded_files.extend(files)
                logger.info(f"✅ АЛГОРИТМ 2 завершен: найдено {len(files)} файлов")
                for i, file_path in enumerate(files, 1):
                    if os.path.exists(file_path):
                        size = os.path.getsize(file_path)
                        logger.info(f"   📄 Файл {i}: {os.path.basename(file_path)} ({size} байт)")
                    else:
                        logger.warning(f"   ❌ Файл {i} не существует: {file_path}")
            else:
                logger.warning("⚠️ АЛГОРИТМ 2 не дал результатов")
        except Exception as e:
            logger.error(f"❌ Ошибка в АЛГОРИТМЕ 2: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
        
        # Алгоритм 3: Перехват сетевых запросов
        try:
            logger.info("🔄 АЛГОРИТМ 3: Перехват сетевых запросов")
            logger.info("-" * 50)
            files = self.find_pdf_in_network_requests(page_url)
            if files:
                all_downloaded_files.extend(files)
                logger.info(f"✅ АЛГОРИТМ 3 завершен: найдено {len(files)} файлов")
                for i, file_path in enumerate(files, 1):
                    if os.path.exists(file_path):
                        size = os.path.getsize(file_path)
                        logger.info(f"   📄 Файл {i}: {os.path.basename(file_path)} ({size} байт)")
                    else:
                        logger.warning(f"   ❌ Файл {i} не существует: {file_path}")
            else:
                logger.warning("⚠️ АЛГОРИТМ 3 не дал результатов")
        except Exception as e:
            logger.error(f"❌ Ошибка в АЛГОРИТМЕ 3: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
        
        # Алгоритм 4: API запросы
        try:
            logger.info("🔄 АЛГОРИТМ 4: API запросы")
            logger.info("-" * 50)
            files = self.find_pdf_via_api_requests(page_url)
            if files:
                all_downloaded_files.extend(files)
                logger.info(f"✅ АЛГОРИТМ 4 завершен: найдено {len(files)} файлов")
                for i, file_path in enumerate(files, 1):
                    if os.path.exists(file_path):
                        size = os.path.getsize(file_path)
                        logger.info(f"   📄 Файл {i}: {os.path.basename(file_path)} ({size} байт)")
                    else:
                        logger.warning(f"   ❌ Файл {i} не существует: {file_path}")
            else:
                logger.warning("⚠️ АЛГОРИТМ 4 не дал результатов")
        except Exception as e:
            logger.error(f"❌ Ошибка в АЛГОРИТМЕ 4: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
        
        # Алгоритм 5: Комплексный подход
        try:
            logger.info("🔄 АЛГОРИТМ 5: Комплексный подход")
            logger.info("-" * 50)
            files = self.comprehensive_pdf_extraction(page_url)
            if files:
                all_downloaded_files.extend(files)
                logger.info(f"✅ АЛГОРИТМ 5 завершен: найдено {len(files)} файлов")
                for i, file_path in enumerate(files, 1):
                    if os.path.exists(file_path):
                        size = os.path.getsize(file_path)
                        logger.info(f"   📄 Файл {i}: {os.path.basename(file_path)} ({size} байт)")
                    else:
                        logger.warning(f"   ❌ Файл {i} не существует: {file_path}")
            else:
                logger.warning("⚠️ АЛГОРИТМ 5 не дал результатов")
        except Exception as e:
            logger.error(f"❌ Ошибка в АЛГОРИТМЕ 5: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
        
        # Алгоритм 6: Продвинутые стратегии
        try:
            logger.info("🔄 АЛГОРИТМ 6: Продвинутые стратегии")
            logger.info("-" * 50)
            files = self.run_advanced_strategies(case_number, page_url)
            if files:
                all_downloaded_files.extend(files)
                logger.info(f"✅ АЛГОРИТМ 6 завершен: найдено {len(files)} файлов")
                for i, file_path in enumerate(files, 1):
                    if os.path.exists(file_path):
                        size = os.path.getsize(file_path)
                        logger.info(f"   📄 Файл {i}: {os.path.basename(file_path)} ({size} байт)")
                    else:
                        logger.warning(f"   ❌ Файл {i} не существует: {file_path}")
            else:
                logger.warning("⚠️ АЛГОРИТМ 6 не дал результатов")
        except Exception as e:
            logger.error(f"❌ Ошибка в АЛГОРИТМЕ 6: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
        
        # Алгоритм 7: PDF.js API
        try:
            logger.info("🔄 АЛГОРИТМ 7: PDF.js API")
            logger.info("-" * 50)
            files = self.extract_pdf_from_pdfjs_api(page_url)
            if files:
                all_downloaded_files.extend(files)
                logger.info(f"✅ АЛГОРИТМ 7 завершен: найдено {len(files)} файлов")
                for i, file_path in enumerate(files, 1):
                    if os.path.exists(file_path):
                        size = os.path.getsize(file_path)
                        logger.info(f"   📄 Файл {i}: {os.path.basename(file_path)} ({size} байт)")
                    else:
                        logger.warning(f"   ❌ Файл {i} не существует: {file_path}")
            else:
                logger.warning("⚠️ АЛГОРИТМ 7 не дал результатов")
        except Exception as e:
            logger.error(f"❌ Ошибка в АЛГОРИТМЕ 7: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
        
        # Алгоритм 8: Blob URL перехват
        try:
            logger.info("🔄 АЛГОРИТМ 8: Blob URL перехват")
            logger.info("-" * 50)
            files = self.extract_pdf_via_blob_interception(page_url)
            if files:
                all_downloaded_files.extend(files)
                logger.info(f"✅ АЛГОРИТМ 8 завершен: найдено {len(files)} файлов")
                for i, file_path in enumerate(files, 1):
                    if os.path.exists(file_path):
                        size = os.path.getsize(file_path)
                        logger.info(f"   📄 Файл {i}: {os.path.basename(file_path)} ({size} байт)")
                    else:
                        logger.warning(f"   ❌ Файл {i} не существует: {file_path}")
            else:
                logger.warning("⚠️ АЛГОРИТМ 8 не дал результатов")
        except Exception as e:
            logger.error(f"❌ Ошибка в АЛГОРИТМЕ 8: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
        
        # Алгоритм 9: Кнопка "Скачать" + Мониторинг
        try:
            logger.info("🔄 АЛГОРИТМ 9: Кнопка 'Скачать' + Мониторинг")
            logger.info("-" * 50)
            files = self.download_via_button_and_monitoring(page_url)
            if files:
                all_downloaded_files.extend(files)
                logger.info(f"✅ АЛГОРИТМ 9 завершен: найдено {len(files)} файлов")
                for i, file_path in enumerate(files, 1):
                    if os.path.exists(file_path):
                        size = os.path.getsize(file_path)
                        logger.info(f"   📄 Файл {i}: {os.path.basename(file_path)} ({size} байт)")
                    else:
                        logger.warning(f"   ❌ Файл {i} не существует: {file_path}")
            else:
                logger.warning("⚠️ АЛГОРИТМ 9 не дал результатов")
        except Exception as e:
            logger.error(f"❌ Ошибка в АЛГОРИТМЕ 9: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
        
        # Алгоритм 10: Print to PDF
        try:
            logger.info("🔄 АЛГОРИТМ 10: Print to PDF")
            logger.info("-" * 50)
            files = self.download_via_print_to_pdf(page_url)
            if files:
                all_downloaded_files.extend(files)
                logger.info(f"✅ АЛГОРИТМ 10 завершен: найдено {len(files)} файлов")
                for i, file_path in enumerate(files, 1):
                    if os.path.exists(file_path):
                        size = os.path.getsize(file_path)
                        logger.info(f"   📄 Файл {i}: {os.path.basename(file_path)} ({size} байт)")
                    else:
                        logger.warning(f"   ❌ Файл {i} не существует: {file_path}")
            else:
                logger.warning("⚠️ АЛГОРИТМ 10 не дал результатов")
        except Exception as e:
            logger.error(f"❌ Ошибка в АЛГОРИТМЕ 10: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
        
        # Алгоритм 11: Ctrl+S + автоматизация диалога
        try:
            logger.info("🔄 АЛГОРИТМ 11: Ctrl+S + автоматизация диалога")
            logger.info("-" * 50)
            files = self.download_via_ctrl_s_dialog(page_url)
            if files:
                all_downloaded_files.extend(files)
                logger.info(f"✅ АЛГОРИТМ 11 завершен: найдено {len(files)} файлов")
                for i, file_path in enumerate(files, 1):
                    if os.path.exists(file_path):
                        size = os.path.getsize(file_path)
                        logger.info(f"   📄 Файл {i}: {os.path.basename(file_path)} ({size} байт)")
                    else:
                        logger.warning(f"   ❌ Файл {i} не существует: {file_path}")
            else:
                logger.warning("⚠️ АЛГОРИТМ 11 не дал результатов")
        except Exception as e:
            logger.error(f"❌ Ошибка в АЛГОРИТМЕ 11: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
        
        # Алгоритм 12: Методы из autoKad.py
        try:
            logger.info("🔄 АЛГОРИТМ 12: Методы из autoKad.py")
            logger.info("-" * 50)
            files = self.download_via_autokad_methods(page_url)
            if files:
                all_downloaded_files.extend(files)
                logger.info(f"✅ АЛГОРИТМ 12 завершен: найдено {len(files)} файлов")
                for i, file_path in enumerate(files, 1):
                    if os.path.exists(file_path):
                        size = os.path.getsize(file_path)
                        logger.info(f"   📄 Файл {i}: {os.path.basename(file_path)} ({size} байт)")
                    else:
                        logger.warning(f"   ❌ Файл {i} не существует: {file_path}")
            else:
                logger.warning("⚠️ АЛГОРИТМ 12 не дал результатов")
        except Exception as e:
            logger.error(f"❌ Ошибка в АЛГОРИТМЕ 12: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
        
        # Итоговая статистика
        logger.info("=" * 80)
        logger.info("📊 ИТОГОВАЯ СТАТИСТИКА АЛГОРИТМОВ")
        logger.info("=" * 80)
        
        # Удаляем дубликаты
        unique_files = list(set(all_downloaded_files))
        logger.info(f"🎉 ВСЕ АЛГОРИТМЫ ЗАВЕРШЕНЫ!")
        logger.info(f"📄 Всего найдено файлов: {len(all_downloaded_files)}")
        logger.info(f"📄 Уникальных файлов: {len(unique_files)}")
        
        # Проверяем существование файлов
        existing_files = []
        missing_files = []
        
        for file_path in unique_files:
            if os.path.exists(file_path):
                size = os.path.getsize(file_path)
                existing_files.append((file_path, size))
                logger.info(f"✅ Файл существует: {os.path.basename(file_path)} ({size} байт)")
            else:
                missing_files.append(file_path)
                logger.warning(f"❌ Файл не существует: {file_path}")
        
        logger.info(f"✅ Существующих файлов: {len(existing_files)}")
        logger.info(f"❌ Отсутствующих файлов: {len(missing_files)}")
        logger.info("=" * 80)
        
        return unique_files
    
    def run_advanced_strategies(self, case_number, case_url):
        """
        Запуск продвинутых стратегий извлечения PDF
        Алгоритм 6: Управляемые HTTP запросы + Перехват сетевого трафика
        ОПЦИОНАЛЬНЫЙ: Требует установки Playwright
        """
        logger.info("🚀 АЛГОРИТМ 6: Продвинутые стратегии")
        
        try:
            # Проверяем доступность Playwright
            try:
                import playwright
                playwright_available = True
                logger.info("✅ Playwright доступен")
            except ImportError:
                playwright_available = False
                logger.warning("⚠️ Playwright не установлен - используем только HTTP стратегию")
                logger.info("💡 Для установки Playwright выполните:")
                logger.info("   1) pip install playwright>=1.40.0")
                logger.info("   2) python -m playwright install chromium")
                logger.info("   ИЛИ запустите: python backend/install_playwright.py")
            
            # Импортируем новые стратегии
            from advanced_pdf_strategies import AdvancedPDFExtractor
            
            all_files = []
            
            # Стратегия 1: Управляемые HTTP запросы (ВСЕГДА доступна)
            try:
                logger.info("🔄 Стратегия 1: Управляемые HTTP запросы")
                
                # Получаем HTML содержимое и cookies из текущего драйвера
                html_content = self.driver.page_source
                cookies = self.driver.get_cookies()
                
                # Создаем экстрактор
                advanced_extractor = AdvancedPDFExtractor(self.files_dir)
                
                # Извлекаем PDF через HTTP
                http_files = advanced_extractor.extract_with_controlled_http(
                    case_url, html_content, cookies
                )
                
                if http_files:
                    all_files.extend(http_files)
                    logger.info(f"✅ HTTP стратегия: {len(http_files)} файлов")
                else:
                    logger.info("⚠️ HTTP стратегия не дала результатов")
                    
            except Exception as e:
                logger.error(f"❌ Ошибка HTTP стратегии: {e}")
            
            # Стратегия 2: Перехват сетевого трафика (Playwright) - ОПЦИОНАЛЬНАЯ
            if playwright_available:
                try:
                    logger.info("🔄 Стратегия 2: Перехват сетевого трафика")
                    
                    from playwright_integration import PlaywrightPDFExtractorSync
                    
                    # Создаем Playwright экстрактор
                    playwright_extractor = PlaywrightPDFExtractorSync(self.files_dir)
                    
                    # Извлекаем PDF через перехват
                    interception_files = playwright_extractor.extract_pdfs(case_url, timeout=30)
                    
                    if interception_files:
                        all_files.extend(interception_files)
                        logger.info(f"✅ Перехват стратегия: {len(interception_files)} файлов")
                    else:
                        logger.info("⚠️ Перехват стратегия не дала результатов")
                        
                except Exception as e:
                    logger.error(f"❌ Ошибка перехвата: {e}")
            else:
                logger.info("⏭️ Стратегия 2 пропущена (Playwright не установлен)")
            
            # Убираем дубликаты
            unique_files = list(set(all_files))
            
            if unique_files:
                logger.info(f"✅ АЛГОРИТМ 6 завершен: найдено {len(unique_files)} файлов")
            else:
                logger.warning("⚠️ АЛГОРИТМ 6 не дал результатов")
            
            return unique_files
            
        except Exception as e:
            logger.error(f"❌ Ошибка в АЛГОРИТМЕ 6: {e}")
            logger.info("💡 Для использования продвинутых стратегий установите Playwright")
            return []
    
    def extract_pdf_from_pdfjs_api(self, page_url):
        """
        Алгоритм 7: Извлечение PDF через PDF.js API
        Самый надежный метод для страниц с PDF.js
        """
        logger.info("🔍 АЛГОРИТМ 7: Извлечение через PDF.js API")
        
        try:
            if not self.driver:
                logger.warning("⚠️ WebDriver не инициализирован")
                return []
            
            logger.info(f"🌐 Переходим на страницу: {page_url}")
            self.driver.get(page_url)
            
            # Ждем загрузки PDF.js
            logger.info("⏳ Ожидание загрузки PDF.js (10 сек)...")
            time.sleep(10)
            
            # JavaScript для извлечения PDF через PDF.js API
            js_extract_pdf = """
            return new Promise((resolve) => {
                try {
                    console.log('🔍 Поиск PDF.js...');
                    
                    // Проверяем наличие PDF.js
                    if (typeof PDFViewerApplication === 'undefined') {
                        console.log('❌ PDFViewerApplication не найден');
                        resolve(null);
                        return;
                    }
                    
                    console.log('✅ PDFViewerApplication найден');
                    
                    // Ждем инициализации PDF.js
                    PDFViewerApplication.initializedPromise.then(() => {
                        console.log('✅ PDF.js инициализирован');
                        
                        const pdfDocument = PDFViewerApplication.pdfDocument;
                        
                        if (!pdfDocument) {
                            console.log('❌ PDF document не загружен');
                            resolve(null);
                            return;
                        }
                        
                        console.log('✅ PDF document найден, извлекаем данные...');
                        console.log('📄 Страниц:', pdfDocument.numPages);
                        
                        // Получаем данные PDF
                        pdfDocument.getData().then((data) => {
                            console.log('✅ Данные получены:', data.length, 'байт');
                            
                            // Преобразуем в массив для передачи в Python
                            resolve({
                                data: Array.from(data),
                                numPages: pdfDocument.numPages,
                                fingerprint: pdfDocument.fingerprints ? pdfDocument.fingerprints[0] : 'unknown'
                            });
                        }).catch((error) => {
                            console.error('❌ Ошибка getData:', error);
                            resolve(null);
                        });
                        
                    }).catch((error) => {
                        console.error('❌ Ошибка initializedPromise:', error);
                        resolve(null);
                    });
                    
                } catch (error) {
                    console.error('❌ Критическая ошибка:', error);
                    resolve(null);
                }
            });
            """
            
            # Выполняем JavaScript с увеличенным таймаутом
            logger.info("🔄 Выполнение JavaScript для извлечения PDF...")
            self.driver.set_script_timeout(60)  # 60 секунд таймаут
            
            result = self.driver.execute_async_script(js_extract_pdf)
            
            if result and result.get('data'):
                logger.info(f"✅ PDF данные получены: {len(result['data'])} байт, {result.get('numPages', '?')} страниц")
                
                # Сохраняем PDF
                pdf_bytes = bytes(result['data'])
                
                # Проверяем, что это действительно PDF
                if not pdf_bytes.startswith(b'%PDF'):
                    logger.warning("⚠️ Данные не являются PDF файлом")
                    return []
                
                import hashlib
                data_hash = hashlib.md5(pdf_bytes).hexdigest()[:8]
                filename = f"ALGORITHM_7_pdfjs_api_{data_hash}.pdf"
                filepath = os.path.join(self.files_dir, filename)
                
                with open(filepath, 'wb') as f:
                    f.write(pdf_bytes)
                
                logger.info(f"✅ PDF извлечен через PDF.js API: {filename} ({len(pdf_bytes)} байт, {result.get('numPages')} страниц)")
                return [filepath]
            else:
                logger.warning("⚠️ PDF.js не найден или PDF не загружен")
                return []
                
        except Exception as e:
            logger.error(f"❌ Ошибка в АЛГОРИТМЕ 7: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []
    
    def extract_pdf_via_blob_interception(self, page_url):
        """
        Алгоритм 8: Перехват Blob URL
        Для динамически генерируемых PDF
        """
        logger.info("🔍 АЛГОРИТМ 8: Перехват Blob URL")
        
        try:
            if not self.driver:
                logger.warning("⚠️ WebDriver не инициализирован")
                return []
            
            # Устанавливаем перехватчик ПЕРЕД загрузкой
            logger.info("🕸️ Настройка Blob перехватчиков...")
            
            setup_blob_interceptor = """
            window.interceptedBlobs = [];
            window.interceptedBlobUrls = [];
            
            console.log('🔧 Установка Blob перехватчиков...');
            
            // Перехватываем Blob
            const originalBlob = window.Blob;
            window.Blob = function(...args) {
                const blob = new originalBlob(...args);
                
                if (blob.type === 'application/pdf') {
                    try {
                        const blobUrl = URL.createObjectURL(blob);
                        window.interceptedBlobs.push({
                            url: blobUrl,
                            size: blob.size,
                            type: blob.type,
                            timestamp: Date.now()
                        });
                        console.log('✅ PDF Blob перехвачен:', blobUrl, blob.size, 'байт');
                    } catch (e) {
                        console.error('Ошибка createObjectURL:', e);
                    }
                }
                
                return blob;
            };
            
            // Перехватываем URL.createObjectURL
            const originalCreateObjectURL = URL.createObjectURL;
            URL.createObjectURL = function(obj) {
                const url = originalCreateObjectURL(obj);
                
                if (obj.type === 'application/pdf') {
                    window.interceptedBlobUrls.push({
                        url: url,
                        size: obj.size,
                        type: obj.type,
                        timestamp: Date.now()
                    });
                    console.log('✅ PDF ObjectURL перехвачен:', url, obj.size, 'байт');
                }
                
                return url;
            };
            
            console.log('✅ Blob перехватчики установлены');
            """
            
            self.driver.execute_script(setup_blob_interceptor)
            logger.info("✅ Blob перехватчики установлены")
            
            # Загружаем страницу
            logger.info(f"🌐 Загружаем страницу: {page_url}")
            self.driver.get(page_url)
            
            # Ждем создания Blob
            logger.info("⏳ Ожидание создания Blob объектов (10 сек)...")
            time.sleep(10)
            
            # Получаем перехваченные Blob
            blobs = self.driver.execute_script("return window.interceptedBlobs || [];")
            blob_urls = self.driver.execute_script("return window.interceptedBlobUrls || [];")
            
            all_blobs = blobs + blob_urls
            
            if all_blobs:
                logger.info(f"📄 Перехвачено {len(all_blobs)} Blob объектов")
                
                downloaded_files = []
                
                for i, blob_info in enumerate(all_blobs):
                    try:
                        blob_url = blob_info['url']
                        blob_size = blob_info.get('size', 0)
                        
                        logger.info(f"📥 Извлечение Blob {i+1}: {blob_url} ({blob_size} байт)")
                        
                        # Получаем данные Blob через JavaScript
                        self.driver.set_script_timeout(60)
                        
                        pdf_data = self.driver.execute_async_script("""
                            var callback = arguments[arguments.length - 1];
                            var blobUrl = arguments[0];
                            
                            console.log('Получение Blob данных:', blobUrl);
                            
                            fetch(blobUrl)
                                .then(response => {
                                    console.log('Response получен');
                                    return response.arrayBuffer();
                                })
                                .then(buffer => {
                                    console.log('ArrayBuffer получен:', buffer.byteLength, 'байт');
                                    var bytes = new Uint8Array(buffer);
                                    callback(Array.from(bytes));
                                })
                                .catch(error => {
                                    console.error('Ошибка получения Blob:', error);
                                    callback(null);
                                });
                        """, blob_url)
                        
                        if pdf_data:
                            # Сохраняем PDF
                            pdf_bytes = bytes(pdf_data)
                            
                            logger.info(f"✅ Blob данные получены: {len(pdf_bytes)} байт")
                            
                            # Проверяем, что это PDF
                            if not pdf_bytes.startswith(b'%PDF'):
                                logger.warning(f"⚠️ Blob не является PDF файлом")
                                continue
                            
                            import hashlib
                            data_hash = hashlib.md5(pdf_bytes).hexdigest()[:8]
                            filename = f"ALGORITHM_8_blob_{data_hash}.pdf"
                            filepath = os.path.join(self.files_dir, filename)
                            
                            with open(filepath, 'wb') as f:
                                f.write(pdf_bytes)
                            
                            downloaded_files.append(filepath)
                            logger.info(f"✅ Blob извлечен: {filename} ({len(pdf_bytes)} байт)")
                        else:
                            logger.warning(f"⚠️ Не удалось получить данные Blob {i+1}")
                        
                    except Exception as e:
                        logger.warning(f"⚠️ Ошибка извлечения Blob {i+1}: {e}")
                        continue
                
                return downloaded_files
            else:
                logger.warning("⚠️ Blob объекты не перехвачены")
                return []
                
        except Exception as e:
            logger.error(f"❌ Ошибка в АЛГОРИТМЕ 8: {e}")
            return []
    
    def download_via_button_and_monitoring(self, page_url):
        """
        Алгоритм 9: Кнопка "Скачать" + Мониторинг Downloads
        Универсальный метод с автоматизацией диалога
        """
        logger.info("🔍 АЛГОРИТМ 9: Кнопка 'Скачать' + Мониторинг")
        
        try:
            if not self.driver:
                logger.warning("⚠️ WebDriver не инициализирован")
                return []
            
            logger.info(f"🌐 Переходим на страницу: {page_url}")
            self.driver.get(page_url)
            time.sleep(1.5)
            
            # Специфичные селекторы для kad.arbitr.ru
            download_button_selectors = [
                "#save",  # Основная кнопка скачивания
                "button#save",
                "a#save",
                # Дополнительные селекторы
                "//button[contains(text(), 'Скачать')]",
                "//a[contains(text(), 'Скачать')]",
                "//button[contains(text(), 'Download')]",
                "//a[contains(text(), 'Download')]",
                "//button[contains(@title, 'Скачать')]",
                "//a[contains(@title, 'Скачать')]",
                "button[title*='Скачать']",
                "a[title*='Скачать']",
                "button[aria-label*='Скачать']",
                "a[aria-label*='Скачать']",
                ".download-button",
                "#download-btn",
                "button[download]",
                "a[download]",
                "[onclick*='download']",
                "[onclick*='Download']"
            ]
            
            download_btn = None
            used_selector = None
            
            for selector in download_button_selectors:
                try:
                    if selector.startswith('//'):
                        # XPath селектор
                        download_btn = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.XPATH, selector))
                        )
                    else:
                        # CSS селектор
                        download_btn = WebDriverWait(self.driver, 3).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                        )
                    
                    used_selector = selector
                    logger.info(f"✅ Найдена кнопка 'Скачать': {selector}")
                    break
                    
                except:
                    continue
            
            if not download_btn:
                logger.warning("⚠️ Кнопка 'Скачать' не найдена")
                return []
            
            # Получаем Downloads директорию из __init__
            downloads_dir = getattr(self, 'downloads_dir', None)
            if not downloads_dir or not os.path.exists(downloads_dir):
                # Fallback: используем стандартную папку Downloads
                import platform
                if platform.system() == "Windows":
                    downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
                else:
                    downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
                
                logger.info(f"📁 Используем Downloads: {downloads_dir}")
            
            # Получаем список файлов ДО скачивания
            before_files = set(os.listdir(downloads_dir)) if os.path.exists(downloads_dir) else set()
            logger.info(f"📊 Файлов в Downloads ДО: {len(before_files)}")
            
            # Кликаем по кнопке
            logger.info("🖱️ Кликаем по кнопке 'Скачать'...")
            try:
                download_btn.click()
                logger.info("✅ Клик выполнен")
            except Exception as e:
                logger.warning(f"⚠️ Обычный клик не сработал, пробуем JavaScript: {e}")
                self.driver.execute_script("arguments[0].click();", download_btn)
                logger.info("✅ JavaScript клик выполнен")
            
            # Ждем появления диалога
            time.sleep(2)
            
            # Автоматически нажимаем Enter для подтверждения
            try:
                import pyautogui
                logger.info("⌨️ Автоматическое подтверждение диалога (Enter)...")
                pyautogui.press('enter')
                time.sleep(1)
                logger.info("✅ Enter нажат")
            except ImportError:
                logger.warning("⚠️ PyAutoGUI не установлен, пропускаем автоподтверждение")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка автоподтверждения: {e}")
            
            # Мониторим появление нового файла
            logger.info("⏳ Мониторинг папки Downloads (30 сек)...")
            max_wait = 30
            start_time = time.time()
            check_count = 0
            
            while time.time() - start_time < max_wait:
                if not os.path.exists(downloads_dir):
                    time.sleep(0.5)
                    continue
                
                current_files = set(os.listdir(downloads_dir))
                new_files = current_files - before_files
                
                check_count += 1
                if check_count % 10 == 0:
                    logger.info(f"🔄 Проверка #{check_count}: новых файлов {len(new_files)}")
                
                # Ищем PDF файлы
                for filename in new_files:
                    if filename.endswith('.pdf') and not filename.endswith('.crdownload'):
                        source_path = os.path.join(downloads_dir, filename)
                        
                        # Проверяем размер (чтобы скачивание завершилось)
                        try:
                            file_size = os.path.getsize(source_path)
                            if file_size > 1000:  # Минимум 1KB
                                logger.info(f"✅ Найден новый PDF: {filename} ({file_size} байт)")
                                
                                # Перемещаем файл
                                import hashlib
                                file_hash = hashlib.md5(filename.encode()).hexdigest()[:8]
                                target_filename = f"ALGORITHM_9_button_{file_hash}.pdf"
                                target_path = os.path.join(self.files_dir, target_filename)
                                
                                import shutil
                                shutil.move(source_path, target_path)
                                
                                logger.info(f"✅ PDF скачан через кнопку: {target_filename} ({file_size} байт)")
                                return [target_path]
                        except Exception as e:
                            logger.debug(f"Ошибка проверки файла {filename}: {e}")
                            continue
                
                time.sleep(0.5)
            
            logger.warning(f"⚠️ Файл не появился в Downloads за {max_wait} секунд")
            logger.info(f"📊 Файлов в Downloads ПОСЛЕ: {len(current_files) if 'current_files' in locals() else '?'}")
            return []
            
        except Exception as e:
            logger.error(f"❌ Ошибка в АЛГОРИТМЕ 9: {e}")
            return []
    
    def download_via_print_to_pdf(self, page_url):
        """
        Алгоритм 10: Print to PDF
        ИСПРАВЛЕН: Сначала пытается скачать PDF через POST, затем использует CDP
        """
        logger.info("🔍 АЛГОРИТМ 10: Print to PDF")
        
        try:
            if not self.driver:
                logger.warning("⚠️ WebDriver не инициализирован")
                return []
            
            logger.info(f"🌐 Переходим на страницу: {page_url}")
            self.driver.get(page_url)
            
            # Ждем загрузки страницы
            logger.info("⏳ Ожидание загрузки страницы (5 сек)...")
            time.sleep(5)
            
            # СНАЧАЛА: Пытаемся скачать PDF через POST запрос
            if '/Document/Pdf/' in page_url:
                logger.info("📥 [ALGORITHM_10] Попытка скачивания PDF через POST...")
                try:
                    post_files = self._download_pdf_via_post(page_url, "print_post", "ALGORITHM_10")
                    if post_files:
                        logger.info(f"✅ [ALGORITHM_10] PDF скачан через POST: {len(post_files)} файлов")
                        return post_files
                    else:
                        logger.warning("⚠️ [ALGORITHM_10] POST запрос не дал результатов")
                except Exception as e:
                    logger.warning(f"⚠️ [ALGORITHM_10] Ошибка POST запроса: {e}")
            
            # ЕСЛИ POST НЕ СРАБОТАЛ: Используем CDP для печати в PDF
            logger.info("🖨️ [ALGORITHM_10] Используем CDP для печати в PDF...")
            
            try:
                result = self.driver.execute_cdp_cmd('Page.printToPDF', {
                    'printBackground': True,
                    'landscape': False,
                    'paperWidth': 8.27,  # A4 ширина в дюймах
                    'paperHeight': 11.69,  # A4 высота в дюймах
                    'marginTop': 0,
                    'marginBottom': 0,
                    'marginLeft': 0,
                    'marginRight': 0,
                    'preferCSSPageSize': True,
                    'displayHeaderFooter': False
                })
                
                # Декодируем base64
                import base64
                pdf_data = base64.b64decode(result['data'])
                
                logger.info(f"📊 [ALGORITHM_10] CDP результат: {len(pdf_data)} байт")
                logger.info(f"📊 [ALGORITHM_10] Начало файла: {pdf_data[:50]}")
                
                # Проверяем, что это PDF
                if not pdf_data.startswith(b'%PDF'):
                    logger.warning("⚠️ [ALGORITHM_10] CDP результат не является PDF")
                    logger.warning(f"⚠️ [ALGORITHM_10] Начало файла: {pdf_data[:100]}")
                    return []
                
                # Сохраняем
                import hashlib
                data_hash = hashlib.md5(pdf_data).hexdigest()[:8]
                filename = f"ALGORITHM_10_print_{data_hash}.pdf"
                filepath = os.path.join(self.files_dir, filename)
                
                with open(filepath, 'wb') as f:
                    f.write(pdf_data)
                
                logger.info(f"✅ [ALGORITHM_10] PDF через CDP: {filename} ({len(pdf_data)} байт)")
                return [filepath]
                
            except Exception as cdp_error:
                logger.error(f"❌ [ALGORITHM_10] Ошибка CDP: {cdp_error}")
                return []
            
        except Exception as e:
            logger.error(f"❌ Ошибка в АЛГОРИТМЕ 10: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return []
    
    def download_via_ctrl_s_dialog(self, page_url):
        """
        Алгоритм 11: Ctrl+S + автоматизация диалога Windows
        Упрощенный алгоритм с конкретными путями
        """
        logger.info("🔍 АЛГОРИТМ 11: Ctrl+S + автоматизация диалога")
        logger.info("=" * 80)
        
        try:
            if not self.driver:
                logger.warning("⚠️ WebDriver не инициализирован")
                return []
            
            # Логируем текущую страницу
            try:
                current_url = self.driver.current_url
                logger.info(f"📍 [CTRL+S] Текущая страница: {current_url}")
            except:
                logger.info(f"📍 [CTRL+S] Целевая страница: {page_url}")
            
            # Конкретные пути
            downloads_dir = r"D:\DOWNLOADS"
            target_dir = r"D:\CODE\sinichka_python\github_pages\darkus079.github.io\backend\files"
            
            logger.info(f"📁 [CTRL+S] Папка для скачивания: {downloads_dir}")
            logger.info(f"📁 [CTRL+S] Целевая папка: {target_dir}")
            
            # Создаем папки если их нет
            os.makedirs(downloads_dir, exist_ok=True)
            os.makedirs(target_dir, exist_ok=True)
            
            # Проверяем доступность PyAutoGUI
            try:
                import pyautogui
                logger.info("✅ [CTRL+S] PyAutoGUI доступен")
            except ImportError:
                logger.warning("⚠️ [CTRL+S] PyAutoGUI не установлен")
                logger.info("💡 Установите: pip install pyautogui>=0.9.54")
                return []
            
            # Получаем список файлов ДО сохранения
            before_files = set(os.listdir(downloads_dir))
            logger.info(f"📊 [CTRL+S] Файлов в D:\\DOWNLOADS ДО: {len(before_files)}")
            
            # ШАГ 1: Нажимаем Ctrl+S
            logger.info("=" * 80)
            logger.info("ШАГ 1: Нажатие Ctrl+S")
            logger.info("=" * 80)
            
            try:
                # Пробуем через Selenium
                from selenium.webdriver.common.keys import Keys
                from selenium.webdriver.common.action_chains import ActionChains
                
                self.driver.switch_to.window(self.driver.current_window_handle)
                actions = ActionChains(self.driver)
                actions.key_down(Keys.CONTROL).send_keys('s').key_up(Keys.CONTROL).perform()
                
                logger.info("✅ [CTRL+S] Ctrl+S нажат через Selenium")
                
            except Exception as e:
                logger.warning(f"⚠️ [CTRL+S] Selenium не сработал: {e}")
                logger.info("🔄 [CTRL+S] Пробуем PyAutoGUI...")
                
                pyautogui.hotkey('ctrl', 's')
                logger.info("✅ [CTRL+S] Ctrl+S нажат через PyAutoGUI")
            
            # ШАГ 2: Ждем 1 секунду
            logger.info("=" * 80)
            logger.info("ШАГ 2: Ожидание диалогового окна (1 сек)")
            logger.info("=" * 80)
            time.sleep(1)
            logger.info("✅ [CTRL+S] Диалоговое окно должно появиться")
            
            # ШАГ 3: Нажимаем Enter для сохранения
            logger.info("=" * 80)
            logger.info("ШАГ 3: Нажатие Enter для сохранения")
            logger.info("=" * 80)
            
            logger.info("⌨️ [CTRL+S] Нажимаем Enter...")
            pyautogui.press('enter')
            logger.info("✅ [CTRL+S] Enter нажат")
            
            # ШАГ 4: Пауза для загрузки документа
            logger.info("=" * 80)
            logger.info("ШАГ 4: Пауза для загрузки документа")
            logger.info("=" * 80)
            
            pause_duration = 10  # 10 секунд на скачивание
            logger.info(f"⏳ [CTRL+S] Ожидание скачивания файла ({pause_duration} сек)...")
            time.sleep(pause_duration)
            logger.info("✅ [CTRL+S] Ожидание завершено")
            
            # ШАГ 5: Поиск файла в D:\DOWNLOADS и перемещение
            logger.info("=" * 80)
            logger.info("ШАГ 5: Поиск и перемещение файла")
            logger.info("=" * 80)
            
            logger.info(f"🔍 [CTRL+S] Проверяем папку: {downloads_dir}")
            
            if not os.path.exists(downloads_dir):
                logger.error(f"❌ [CTRL+S] Папка не существует: {downloads_dir}")
                return []
            
            # Получаем новые файлы
            current_files = set(os.listdir(downloads_dir))
            new_files = current_files - before_files
            
            logger.info(f"📊 [CTRL+S] Файлов в D:\\DOWNLOADS ПОСЛЕ: {len(current_files)}")
            logger.info(f"📊 [CTRL+S] Новых файлов: {len(new_files)}")
            
            if new_files:
                logger.info(f"📄 [CTRL+S] Список новых файлов:")
                for idx, fname in enumerate(new_files, 1):
                    logger.info(f"   {idx}. {fname}")
            else:
                logger.warning("⚠️ [CTRL+S] Новых файлов не найдено")
            
            # Ищем PDF файлы
            downloaded_files = []
            
            for filename in new_files:
                logger.info(f"🔍 [CTRL+S] Проверяем файл: {filename}")
                
                # Проверяем расширение
                if not filename.endswith('.pdf'):
                    logger.debug(f"⏭️ [CTRL+S] Не PDF, пропускаем: {filename}")
                    continue
                
                # Проверяем, что это не временный файл
                if filename.endswith('.crdownload') or filename.endswith('.tmp'):
                    logger.debug(f"⏭️ [CTRL+S] Временный файл, пропускаем: {filename}")
                    continue
                
                source_path = os.path.join(downloads_dir, filename)
                logger.info(f"📂 [CTRL+S] Исходный путь: {source_path}")
                
                # Проверяем размер файла
                try:
                    file_size = os.path.getsize(source_path)
                    logger.info(f"📏 [CTRL+S] Размер файла: {file_size} байт")
                    
                    if file_size < 1000:  # Минимум 1KB
                        logger.warning(f"⚠️ [CTRL+S] Файл слишком мал ({file_size} байт), пропускаем")
                        continue
                    
                    logger.info(f"✅ [CTRL+S] Размер файла корректный: {file_size} байт")
                    
                except Exception as e:
                    logger.error(f"❌ [CTRL+S] Ошибка проверки размера: {e}")
                    continue
                
                # Генерируем имя для целевого файла
                import hashlib
                file_hash = hashlib.md5(filename.encode()).hexdigest()[:8]
                target_filename = f"ALGORITHM_11_ctrl_s_{file_hash}.pdf"
                target_path = os.path.join(target_dir, target_filename)
                
                logger.info(f"📂 [CTRL+S] Целевой путь: {target_path}")
                
                # Перемещаем файл
                try:
                    logger.info(f"🚚 [CTRL+S] Перемещение файла...")
                    logger.info(f"   ИЗ: {source_path}")
                    logger.info(f"   В:  {target_path}")
                    
                    import shutil
                    shutil.move(source_path, target_path)
                    
                    logger.info(f"✅ [CTRL+S] Файл успешно перемещен!")
                    
                    # Проверяем, что файл действительно в целевой папке
                    if os.path.exists(target_path):
                        final_size = os.path.getsize(target_path)
                        logger.info(f"✅ [CTRL+S] Файл существует в целевой папке: {target_filename}")
                        logger.info(f"📏 [CTRL+S] Финальный размер: {final_size} байт")
                        logger.info(f"📍 [URL LOG] Сохранено с URL: {page_url}")
                        
                        downloaded_files.append(target_path)
                    else:
                        logger.error(f"❌ [CTRL+S] Файл не найден в целевой папке!")
                    
                except Exception as e:
                    logger.error(f"❌ [CTRL+S] Ошибка перемещения файла: {e}")
                    continue
            
            if downloaded_files:
                logger.info("=" * 80)
                logger.info(f"🎉 [CTRL+S] Успешно скачано {len(downloaded_files)} файлов:")
                for idx, fpath in enumerate(downloaded_files, 1):
                    logger.info(f"   {idx}. {os.path.basename(fpath)}")
                logger.info("=" * 80)
                return downloaded_files
            else:
                logger.warning("=" * 80)
                logger.warning(f"⚠️ [CTRL+S] Файлы не найдены в D:\\DOWNLOADS")
                logger.warning(f"📊 [CTRL+S] Проверено: {len(new_files)} новых файлов")
                logger.warning("=" * 80)
                return []
            
        except Exception as e:
            logger.error("=" * 80)
            logger.error(f"❌ [CTRL+S] Критическая ошибка в АЛГОРИТМЕ 11: {e}")
            import traceback
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            logger.error("=" * 80)
            return []
    
    def download_via_autokad_methods(self, page_url):
        """
        Алгоритм 12: Методы из autoKad.py
        Основан на проверенных методах извлечения текста и обработки документов
        """
        logger.info("🔍 АЛГОРИТМ 12: Методы из autoKad.py")
        logger.info("=" * 80)
        
        try:
            if not self.driver:
                logger.warning("⚠️ WebDriver не инициализирован")
                return []
            
            # Логируем текущую страницу
            try:
                current_url = self.driver.current_url
                logger.info(f"📍 [AUTOKAD] Текущая страница: {current_url}")
            except:
                logger.info(f"📍 [AUTOKAD] Целевая страница: {page_url}")
            
            downloaded_files = []
            
            # Метод 1: Извлечение через document.querySelector
            logger.info("🔄 [AUTOKAD] Метод 1: Поиск через document.querySelector")
            
            try:
                # JavaScript для поиска PDF элементов (как в autoKad)
                js_find_pdf_elements = """
                const elements = document.querySelectorAll('a[href*=".pdf"], a[href*="document"], a[href*="Document"]');
                const links = [];
                
                elements.forEach(element => {
                    const href = element.getAttribute('href');
                    const text = element.textContent.trim();
                    if (href && text) {
                        const fullUrl = href.startsWith('http') ? href : 
                                       (href.startsWith('/') ? 'https://kad.arbitr.ru' + href : 
                                        window.location.href + '/' + href);
                        links.push({
                            url: fullUrl,
                            text: text
                        });
                    }
                });
                
                return links;
                """
                
                pdf_links = self.driver.execute_script(js_find_pdf_elements)
                
                if pdf_links:
                    logger.info(f"✅ [AUTOKAD] Найдено {len(pdf_links)} PDF элементов")
                    
                    for i, link_info in enumerate(pdf_links):
                        url = link_info['url']
                        text = link_info['text']
                        
                        logger.info(f"📄 [AUTOKAD] Элемент {i+1}: {text}")
                        logger.info(f"🔗 [AUTOKAD] URL: {url}")
                        
                        # Проверка черного списка
                        if self._is_blacklisted_url(url):
                            logger.warning(f"🚫 [AUTOKAD] URL в черном списке, пропускаем")
                            continue
                        
                        # Проверка документа дела
                        if not self._is_case_document_url(url):
                            logger.debug(f"⚠️ [AUTOKAD] Не документ дела, пропускаем")
                            continue
                        
                        # Скачиваем через POST
                        files = self._download_pdf_via_post(url, f"autokad_querySelector_{i+1}", "ALGORITHM_12")
                        if files:
                            downloaded_files.extend(files)
                            logger.info(f"✅ [AUTOKAD] Элемент {i+1} скачан")
                else:
                    logger.warning("⚠️ [AUTOKAD] PDF элементы не найдены через querySelector")
                    
            except Exception as e:
                logger.warning(f"⚠️ [AUTOKAD] Ошибка метода querySelector: {e}")
            
            # Метод 2: Извлечение текста из div.text (как в autoKad)
            logger.info("🔄 [AUTOKAD] Метод 2: Извлечение через div.text")
            
            try:
                # JavaScript для извлечения текстового содержимого
                js_extract_text = """
                const textDiv = document.querySelector('div.text');
                if (textDiv) {
                    return {
                        found: true,
                        text: textDiv.textContent || textDiv.innerText,
                        length: (textDiv.textContent || textDiv.innerText).length
                    };
                }
                return { found: false };
                """
                
                text_result = self.driver.execute_script(js_extract_text)
                
                if text_result.get('found'):
                    logger.info(f"✅ [AUTOKAD] Найден div.text с контентом: {text_result['length']} символов")
                    
                    # Если нашли текст, значит это страница документа
                    # Попробуем найти PDF на этой странице
                    logger.info("🔍 [AUTOKAD] Поиск PDF на странице с текстом...")
                    
                    # Ищем все ссылки и элементы с PDF
                    js_find_pdf_on_text_page = """
                    const pdfElements = [];
                    
                    // Поиск в ссылках
                    document.querySelectorAll('a').forEach(a => {
                        const href = a.getAttribute('href');
                        if (href && (href.includes('.pdf') || href.includes('Document') || href.includes('Pdf'))) {
                            pdfElements.push({
                                type: 'link',
                                url: href.startsWith('http') ? href : 
                                     (href.startsWith('/') ? 'https://kad.arbitr.ru' + href : window.location.href),
                                text: a.textContent.trim()
                            });
                        }
                    });
                    
                    // Поиск в embed элементах
                    document.querySelectorAll('embed[type*="pdf"]').forEach(embed => {
                        const src = embed.getAttribute('src');
                        if (src) {
                            pdfElements.push({
                                type: 'embed',
                                url: src,
                                text: 'PDF Embed'
                            });
                        }
                    });
                    
                    // Поиск в object элементах
                    document.querySelectorAll('object[type*="pdf"]').forEach(obj => {
                        const data = obj.getAttribute('data');
                        if (data) {
                            pdfElements.push({
                                type: 'object',
                                url: data,
                                text: 'PDF Object'
                            });
                        }
                    });
                    
                    return pdfElements;
                    """
                    
                    pdf_elements = self.driver.execute_script(js_find_pdf_on_text_page)
                    
                    if pdf_elements:
                        logger.info(f"✅ [AUTOKAD] Найдено {len(pdf_elements)} PDF элементов на странице с текстом")
                        
                        for i, elem in enumerate(pdf_elements):
                            url = elem['url']
                            elem_type = elem['type']
                            
                            logger.info(f"📄 [AUTOKAD] Элемент {i+1} ({elem_type}): {url}")
                            
                            # Проверки
                            if self._is_blacklisted_url(url):
                                continue
                            if not self._is_case_document_url(url):
                                continue
                            
                            # Скачиваем через POST
                            files = self._download_pdf_via_post(url, f"autokad_text_page_{i+1}", "ALGORITHM_12")
                            if files:
                                downloaded_files.extend(files)
                                
                else:
                    logger.info("ℹ️ [AUTOKAD] div.text не найден на странице")
                    
            except Exception as e:
                logger.warning(f"⚠️ [AUTOKAD] Ошибка метода div.text: {e}")
            
            # Метод 3: Прямое скачивание текущего URL (если это PDF страница)
            logger.info("🔄 [AUTOKAD] Метод 3: Прямое скачивание текущего URL")
            
            try:
                current_url = self.driver.current_url
                
                # Если текущий URL - это PDF документ
                if '/Document/Pdf/' in current_url or current_url.endswith('.pdf'):
                    logger.info(f"✅ [AUTOKAD] Текущий URL является PDF документом")
                    logger.info(f"🔗 [AUTOKAD] URL: {current_url}")
                    
                    # Проверки
                    if not self._is_blacklisted_url(current_url):
                        if self._is_case_document_url(current_url):
                            # Скачиваем через POST
                            files = self._download_pdf_via_post(current_url, "autokad_current_url", "ALGORITHM_12")
                            if files:
                                downloaded_files.extend(files)
                                logger.info(f"✅ [AUTOKAD] Текущий URL скачан")
                        else:
                            logger.debug("⚠️ [AUTOKAD] Текущий URL не является документом дела")
                    else:
                        logger.warning("🚫 [AUTOKAD] Текущий URL в черном списке")
                else:
                    logger.debug("ℹ️ [AUTOKAD] Текущий URL не является PDF страницей")
                    
            except Exception as e:
                logger.warning(f"⚠️ [AUTOKAD] Ошибка метода текущего URL: {e}")
            
            # Метод 4: Использование window.open для обхода блокировок
            logger.info("🔄 [AUTOKAD] Метод 4: window.open (обход блокировок)")
            
            try:
                # Сохраняем текущее окно
                original_window = self.driver.current_window_handle
                
                # Открываем новое окно (метод из autoKad для обхода блокировок)
                logger.info("🪟 [AUTOKAD] Открываем новое окно...")
                self.driver.execute_script("window.open('');")
                
                # Переключаемся на новое окно
                new_window = self.driver.window_handles[-1]
                self.driver.switch_to.window(new_window)
                logger.info("✅ [AUTOKAD] Переключились на новое окно")
                
                # Загружаем страницу в новом окне
                logger.info(f"🌐 [AUTOKAD] Загружаем страницу в новом окне: {page_url}")
                self.driver.get(page_url)
                time.sleep(5)
                
                # Пробуем найти PDF на этой странице
                new_window_url = self.driver.current_url
                logger.info(f"📍 [AUTOKAD] URL в новом окне: {new_window_url}")
                
                if '/Document/Pdf/' in new_window_url or new_window_url.endswith('.pdf'):
                    # Проверки и скачивание
                    if not self._is_blacklisted_url(new_window_url):
                        if self._is_case_document_url(new_window_url):
                            files = self._download_pdf_via_post(new_window_url, "autokad_new_window", "ALGORITHM_12")
                            if files:
                                downloaded_files.extend(files)
                                logger.info(f"✅ [AUTOKAD] Скачано через новое окно")
                
                # Закрываем новое окно и возвращаемся к оригинальному
                logger.info("🔙 [AUTOKAD] Закрываем новое окно и возвращаемся...")
                self.driver.close()
                self.driver.switch_to.window(original_window)
                logger.info("✅ [AUTOKAD] Вернулись в оригинальное окно")
                
            except Exception as e:
                logger.warning(f"⚠️ [AUTOKAD] Ошибка метода window.open: {e}")
                # Пытаемся вернуться в оригинальное окно
                try:
                    if len(self.driver.window_handles) > 1:
                        self.driver.switch_to.window(self.driver.window_handles[0])
                except:
                    pass
            
            # Итоговая статистика
            if downloaded_files:
                logger.info("=" * 80)
                logger.info(f"🎉 [AUTOKAD] Успешно скачано {len(downloaded_files)} файлов:")
                for idx, fpath in enumerate(downloaded_files, 1):
                    logger.info(f"   {idx}. {os.path.basename(fpath)}")
                logger.info("=" * 80)
                return downloaded_files
            else:
                logger.warning("=" * 80)
                logger.warning("⚠️ [AUTOKAD] Файлы не найдены")
                logger.warning("=" * 80)
                return []
            
        except Exception as e:
            logger.error("=" * 80)
            logger.error(f"❌ [AUTOKAD] Критическая ошибка в АЛГОРИТМЕ 12: {e}")
            import traceback
            logger.error(f"Traceback:\n{traceback.format_exc()}")
            logger.error("=" * 80)
            return []
