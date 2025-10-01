"""
Продвинутые стратегии скачивания PDF файлов
1. Стратегия Управляемого Запроса (Controlled HTTP Requests)
2. Стратегия Перехвата Сетевого Трафика (Network Interception)
"""

import os
import time
import logging
import requests
import hashlib
import re
from urllib.parse import urljoin, urlparse
from typing import List, Optional, Dict, Any

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

def is_blacklisted_url(url):
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
            logger.warning(f"🚫 [BLACKLIST] URL заблокирован: {url}")
            logger.warning(f"🚫 [BLACKLIST] Причина: содержит '{blacklisted}'")
            return True
    
    return False

def is_case_document_url(url):
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
            logger.info(f"✅ [CASE DOC] Документ дела: {url} (индикатор: {indicator})")
            return True
    
    # Если нет явных индикаторов, но есть GUID-подобные структуры
    guid_pattern = r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'
    if re.search(guid_pattern, url_lower, re.IGNORECASE):
        logger.info(f"✅ [CASE DOC] Документ с GUID: {url}")
        return True
    
    logger.debug(f"⚠️ [NOT CASE] Не похоже на документ дела: {url}")
    return False

class ControlledHTTPStrategy:
    """
    Стратегия Управляемого Запроса (Controlled HTTP Requests)
    Использует requests для прямого скачивания PDF файлов
    """
    
    def __init__(self, files_dir: str):
        self.files_dir = files_dir
        os.makedirs(files_dir, exist_ok=True)
        self.session = requests.Session()
        
        # Настройка сессии с реалистичными заголовками
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.6843.82 Safari/537.36',
            'Accept': 'application/pdf,application/octet-stream,*/*',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'DNT': '1'
        })
    
    def set_referer(self, referer_url: str):
        """Устанавливает Referer для имитации перехода с страницы дела"""
        self.session.headers['Referer'] = referer_url
        logger.info(f"🔗 Установлен Referer: {referer_url}")
    
    def set_cookies_from_browser(self, cookies: List[Dict[str, Any]]):
        """Устанавливает cookies из браузера"""
        for cookie in cookies:
            try:
                self.session.cookies.set(
                    name=cookie['name'],
                    value=cookie['value'],
                    domain=cookie.get('domain', ''),
                    path=cookie.get('path', '/')
                )
            except Exception as e:
                logger.debug(f"Ошибка установки cookie {cookie.get('name', 'unknown')}: {e}")
        
        logger.info(f"🍪 Установлено {len(cookies)} cookies")
    
    def download_pdf(self, pdf_url: str, case_url: str, filename_prefix: str = "controlled") -> Optional[str]:
        """
        Скачивает PDF файл с использованием управляемого HTTP запроса
        
        Args:
            pdf_url: URL PDF файла
            case_url: URL страницы дела (для Referer)
            filename_prefix: Префикс для имени файла
            
        Returns:
            Путь к скачанному файлу или None при ошибке
        """
        try:
            # ПРОВЕРКА ЧЕРНОГО СПИСКА
            if is_blacklisted_url(pdf_url):
                logger.error(f"❌ [BLOCKED] Попытка скачать URL из черного списка: {pdf_url}")
                return None
            
            # ПРОВЕРКА: Документ дела или служебный
            if not is_case_document_url(pdf_url):
                logger.warning(f"⚠️ [NOT CASE] Попытка скачать не-документ дела: {pdf_url}")
                return None
            
            # Устанавливаем Referer
            self.set_referer(case_url)
            
            logger.info(f"📥 [DOWNLOAD] Управляемый запрос: {pdf_url}")
            
            # Выполняем запрос с потоковым скачиванием
            response = self.session.get(pdf_url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Проверяем Content-Type
            content_type = response.headers.get('content-type', '').lower()
            if 'pdf' not in content_type:
                logger.warning(f"⚠️ Неожиданный Content-Type: {content_type}")
                # Проверяем содержимое файла
                first_chunk = next(response.iter_content(1024), b'')
                if not first_chunk.startswith(b'%PDF'):
                    logger.warning(f"⚠️ Файл не является PDF: {pdf_url}")
                    return None
            
            # Генерируем имя файла
            url_hash = hashlib.md5(pdf_url.encode()).hexdigest()[:8]
            filename = f"{filename_prefix}_{url_hash}.pdf"
            filepath = os.path.join(self.files_dir, filename)
            
            # Проверяем существование файла
            if os.path.exists(filepath):
                existing_size = os.path.getsize(filepath)
                if existing_size == int(response.headers.get('content-length', 0)):
                    logger.info(f"ℹ️ Файл уже существует: {filename}")
                    return filepath
            
            # Скачиваем файл
            total_size = 0
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        total_size += len(chunk)
            
            # Проверяем размер файла
            if total_size < 1000:  # Минимум 1KB
                logger.warning(f"⚠️ Файл слишком мал: {total_size} байт")
                os.remove(filepath)
                return None
            
            logger.info(f"✅ PDF скачан: {filename} ({total_size} байт)")
            return filepath
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Ошибка HTTP запроса: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Ошибка скачивания: {e}")
            return None
    
    def find_pdf_urls_in_html(self, html_content: str, base_url: str) -> List[str]:
        """
        Ищет PDF URL в HTML содержимом
        
        Args:
            html_content: HTML содержимое страницы
            base_url: Базовый URL для преобразования относительных ссылок
            
        Returns:
            Список найденных PDF URL
        """
        pdf_urls = []
        blocked_count = 0
        
        # Паттерны для поиска PDF URL
        patterns = [
            r'href=["\']([^"\']*\.pdf[^"\']*)["\']',
            r'src=["\']([^"\']*\.pdf[^"\']*)["\']',
            r'url["\']?:\s*["\']([^"\']+\.pdf[^"\']*)["\']',
            r'file["\']?:\s*["\']([^"\']+\.pdf[^"\']*)["\']',
            r'data-pdf=["\']([^"\']*\.pdf[^"\']*)["\']',
            r'data-file=["\']([^"\']*\.pdf[^"\']*)["\']',
            r'data-url=["\']([^"\']*\.pdf[^"\']*)["\']',
            # Специфичные для kad.arbitr.ru
            r'Document/Pdf[^"\']*',
            r'Kad/PdfDocument[^"\']*',
            r'PdfDocument[^"\']*',
            r'Document/GetPdf[^"\']*',
            r'GetPdf[^"\']*'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0] if match[0] else match[1]
                
                url = match.strip()
                if url and len(url) > 5:
                    # Преобразуем относительные URL в абсолютные
                    if not url.startswith('http'):
                        if url.startswith('/'):
                            url = urljoin(base_url, url)
                        else:
                            url = urljoin(base_url + '/', url)
                    
                    # ПРОВЕРКА ЧЕРНОГО СПИСКА
                    if is_blacklisted_url(url):
                        blocked_count += 1
                        continue
                    
                    # ПРОВЕРКА: Документ дела или служебный
                    if not is_case_document_url(url):
                        logger.debug(f"⚠️ Пропущен URL (не документ дела): {url}")
                        continue
                    
                    if url not in pdf_urls:
                        pdf_urls.append(url)
                        logger.info(f"✅ [FOUND] Найден PDF URL: {url}")
        
        if blocked_count > 0:
            logger.warning(f"🚫 [BLOCKED] Заблокировано {blocked_count} URL из черного списка")
        
        return pdf_urls


class NetworkInterceptionStrategy:
    """
    Стратегия Перехвата Сетевого Трафика (Network Interception)
    Использует Playwright для перехвата сетевых запросов
    """
    
    def __init__(self, files_dir: str):
        self.files_dir = files_dir
        os.makedirs(files_dir, exist_ok=True)
        self.intercepted_requests = []
    
    def setup_interception(self, page):
        """
        Настраивает перехват сетевых запросов
        
        Args:
            page: Playwright page объект
        """
        logger.info("🕸️ Настройка перехвата сетевых запросов")
        
        def handle_route(route):
            """Обработчик перехваченных запросов"""
            request = route.request
            url = request.url
            
            # Проверяем, является ли запрос PDF
            if self._is_pdf_request(request):
                logger.info(f"🎯 Перехвачен PDF запрос: {url}")
                self.intercepted_requests.append({
                    'url': url,
                    'method': request.method,
                    'headers': request.headers,
                    'timestamp': time.time()
                })
            
            # Продолжаем запрос
            route.continue_()
        
        # Настраиваем перехват всех запросов
        page.route("**/*", handle_route)
        
        # Дополнительно перехватываем только PDF запросы
        page.route("**/*.pdf", handle_route)
        page.route("**/*Document*", handle_route)
        page.route("**/*Pdf*", handle_route)
    
    def _is_pdf_request(self, request) -> bool:
        """
        Проверяет, является ли запрос PDF файлом
        
        Args:
            request: Playwright request объект
            
        Returns:
            True если это PDF запрос
        """
        url = request.url.lower()
        headers = request.headers
        
        # Проверяем URL
        url_indicators = [
            '.pdf',
            'document/pdf',
            'kad/pdfdocument',
            'pdfdocument',
            'getpdf'
        ]
        
        url_match = any(indicator in url for indicator in url_indicators)
        
        # Проверяем заголовки
        accept_header = headers.get('accept', '').lower()
        content_type = headers.get('content-type', '').lower()
        
        header_match = (
            'application/pdf' in accept_header or
            'application/pdf' in content_type or
            'application/octet-stream' in accept_header
        )
        
        return url_match or header_match
    
    async def intercept_pdf_downloads(self, page, case_url: str, timeout: int = 30) -> List[str]:
        """
        Перехватывает PDF загрузки на странице
        
        Args:
            page: Playwright page объект
            case_url: URL страницы дела
            timeout: Таймаут ожидания в секундах
            
        Returns:
            Список путей к скачанным файлам
        """
        logger.info(f"🌐 Загружаем страницу: {case_url}")
        
        # Настраиваем перехват
        self.setup_interception(page)
        
        # Загружаем страницу
        await page.goto(case_url, wait_until='networkidle')
        
        # Ждем загрузки PDF
        logger.info(f"⏳ Ожидание PDF загрузок ({timeout}с)...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if self.intercepted_requests:
                break
            await page.wait_for_timeout(1000)  # Ждем 1 секунду
        
        downloaded_files = []
        
        # Скачиваем перехваченные PDF
        for i, req_info in enumerate(self.intercepted_requests):
            try:
                logger.info(f"📥 Скачивание PDF {i+1}: {req_info['url']}")
                
                # Выполняем запрос с теми же заголовками
                response = await page.request.get(req_info['url'])
                
                if response.status == 200:
                    content = await response.body()
                    
                    # Проверяем, что это PDF
                    if content.startswith(b'%PDF'):
                        # Генерируем имя файла
                        url_hash = hashlib.md5(req_info['url'].encode()).hexdigest()[:8]
                        filename = f"intercepted_{url_hash}.pdf"
                        filepath = os.path.join(self.files_dir, filename)
                        
                        # Сохраняем файл
                        with open(filepath, 'wb') as f:
                            f.write(content)
                        
                        downloaded_files.append(filepath)
                        logger.info(f"✅ PDF сохранен: {filename} ({len(content)} байт)")
                    else:
                        logger.warning(f"⚠️ Не PDF содержимое: {req_info['url']}")
                else:
                    logger.warning(f"⚠️ HTTP {response.status}: {req_info['url']}")
                    
            except Exception as e:
                logger.error(f"❌ Ошибка скачивания PDF {i+1}: {e}")
                continue
        
        return downloaded_files
    
    def get_intercepted_requests(self) -> List[Dict[str, Any]]:
        """Возвращает список перехваченных запросов"""
        return self.intercepted_requests.copy()


class AdvancedPDFExtractor:
    """
    Комбинированный экстрактор PDF файлов
    Использует обе стратегии для максимальной эффективности
    """
    
    def __init__(self, files_dir: str):
        self.files_dir = files_dir
        self.http_strategy = ControlledHTTPStrategy(files_dir)
        self.interception_strategy = NetworkInterceptionStrategy(files_dir)
    
    def extract_with_controlled_http(self, case_url: str, html_content: str, cookies: List[Dict[str, Any]]) -> List[str]:
        """
        Извлекает PDF используя управляемые HTTP запросы
        
        Args:
            case_url: URL страницы дела
            html_content: HTML содержимое страницы
            cookies: Cookies из браузера
            
        Returns:
            Список путей к скачанным файлам
        """
        logger.info("🚀 Стратегия 1: Управляемые HTTP запросы")
        
        # Устанавливаем cookies
        self.http_strategy.set_cookies_from_browser(cookies)
        
        # Ищем PDF URL в HTML
        logger.info("🔍 Поиск PDF URL в HTML...")
        pdf_urls = self.http_strategy.find_pdf_urls_in_html(html_content, case_url)
        
        if not pdf_urls:
            logger.warning("⚠️ [NO URLS] PDF URL не найдены в HTML (после фильтрации)")
            return []
        
        logger.info(f"📋 [FOUND] Найдено {len(pdf_urls)} валидных PDF URL (после фильтрации)")
        
        downloaded_files = []
        blocked_count = 0
        success_count = 0
        failed_count = 0
        
        # Скачиваем каждый найденный PDF
        for i, pdf_url in enumerate(pdf_urls):
            try:
                logger.info(f"📥 [{i+1}/{len(pdf_urls)}] Попытка скачивания: {pdf_url}")
                
                filepath = self.http_strategy.download_pdf(
                    pdf_url, 
                    case_url, 
                    f"controlled_{i+1}"
                )
                
                if filepath:
                    downloaded_files.append(filepath)
                    success_count += 1
                    logger.info(f"✅ [{i+1}/{len(pdf_urls)}] PDF успешно скачан: {os.path.basename(filepath)}")
                else:
                    failed_count += 1
                    logger.warning(f"❌ [{i+1}/{len(pdf_urls)}] PDF не удалось скачать")
                    
            except Exception as e:
                failed_count += 1
                logger.error(f"❌ [{i+1}/{len(pdf_urls)}] Ошибка скачивания: {e}")
                continue
        
        # Итоговая статистика
        logger.info(f"📊 [STATS] HTTP стратегия:")
        logger.info(f"   ✅ Успешно: {success_count}")
        logger.info(f"   ❌ Ошибки: {failed_count}")
        logger.info(f"   📁 Всего файлов: {len(downloaded_files)}")
        
        return downloaded_files
    
    async def extract_with_network_interception(self, page, case_url: str) -> List[str]:
        """
        Извлекает PDF используя перехват сетевого трафика
        
        Args:
            page: Playwright page объект
            case_url: URL страницы дела
            
        Returns:
            Список путей к скачанным файлам
        """
        logger.info("🚀 Стратегия 2: Перехват сетевого трафика")
        
        try:
            downloaded_files = await self.interception_strategy.intercept_pdf_downloads(
                page, case_url, timeout=30
            )
            
            if downloaded_files:
                logger.info(f"✅ Перехвачено {len(downloaded_files)} PDF файлов")
            else:
                logger.warning("⚠️ PDF файлы не перехвачены")
            
            return downloaded_files
            
        except Exception as e:
            logger.error(f"❌ Ошибка перехвата: {e}")
            return []
    
    async def extract_with_both_strategies(self, page, case_url: str, html_content: str, cookies: List[Dict[str, Any]]) -> List[str]:
        """
        Извлекает PDF используя обе стратегии
        
        Args:
            page: Playwright page объект
            case_url: URL страницы дела
            html_content: HTML содержимое страницы
            cookies: Cookies из браузера
            
        Returns:
            Список путей к скачанным файлам
        """
        logger.info("🚀 Комбинированная стратегия: HTTP + Перехват")
        
        all_files = []
        
        # Стратегия 1: Управляемые HTTP запросы
        try:
            http_files = self.extract_with_controlled_http(case_url, html_content, cookies)
            all_files.extend(http_files)
            logger.info(f"📄 HTTP стратегия: {len(http_files)} файлов")
        except Exception as e:
            logger.error(f"❌ Ошибка HTTP стратегии: {e}")
        
        # Стратегия 2: Перехват сетевого трафика
        try:
            interception_files = await self.extract_with_network_interception(page, case_url)
            all_files.extend(interception_files)
            logger.info(f"📄 Перехват стратегия: {len(interception_files)} файлов")
        except Exception as e:
            logger.error(f"❌ Ошибка перехвата: {e}")
        
        # Убираем дубликаты
        unique_files = list(set(all_files))
        logger.info(f"🎉 Всего уникальных файлов: {len(unique_files)}")
        
        return unique_files
