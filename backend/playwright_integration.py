"""
Интеграция с Playwright для продвинутых стратегий PDF извлечения
"""

import os
import asyncio
import logging
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright, Browser, Page, BrowserContext

logger = logging.getLogger(__name__)

class PlaywrightPDFExtractor:
    """
    PDF экстрактор на основе Playwright
    """
    
    def __init__(self, files_dir: str):
        self.files_dir = files_dir
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
    
    async def initialize(self, headless: bool = True):
        """
        Инициализирует Playwright браузер
        
        Args:
            headless: Запускать в headless режиме
        """
        try:
            logger.info("🎭 Инициализация Playwright")
            
            self.playwright = await async_playwright().start()
            
            # Настройки браузера
            browser_args = [
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--window-size=1920,1080'
            ]
            
            # Запускаем браузер
            self.browser = await self.playwright.chromium.launch(
                headless=headless,
                args=browser_args
            )
            
            # Создаем контекст с реалистичными настройками
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.6843.82 Safari/537.36',
                locale='ru-RU',
                timezone_id='Europe/Moscow',
                permissions=['geolocation'],
                extra_http_headers={
                    'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1'
                }
            )
            
            # Создаем страницу
            self.page = await self.context.new_page()
            
            # Настраиваем перехват запросов
            await self._setup_request_interception()
            
            logger.info("✅ Playwright инициализирован")
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации Playwright: {e}")
            raise
    
    async def _setup_request_interception(self):
        """Настраивает перехват сетевых запросов"""
        if not self.page:
            return
        
        logger.info("🕸️ Настройка перехвата запросов")
        
        # Список для хранения перехваченных PDF запросов
        self.pdf_requests = []
        
        async def handle_request(request):
            """Обработчик перехваченных запросов"""
            url = request.url
            
            # Проверяем, является ли запрос PDF
            if self._is_pdf_request(request):
                logger.info(f"🎯 Перехвачен PDF запрос: {url}")
                self.pdf_requests.append({
                    'url': url,
                    'method': request.method,
                    'headers': request.headers,
                    'timestamp': asyncio.get_event_loop().time()
                })
        
        # Настраиваем перехват
        self.page.on('request', handle_request)
    
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
            'getpdf',
            'document/getpdf'
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
    
    async def navigate_to_case(self, case_url: str) -> bool:
        """
        Переходит на страницу дела
        
        Args:
            case_url: URL страницы дела
            
        Returns:
            True если переход успешен
        """
        try:
            if not self.page:
                logger.error("❌ Страница не инициализирована")
                return False
            
            logger.info(f"🌐 Переход на страницу: {case_url}")
            
            # Переходим на страницу
            await self.page.goto(case_url, wait_until='networkidle', timeout=30000)
            
            # Ждем загрузки контента
            await self.page.wait_for_timeout(3000)
            
            logger.info("✅ Страница загружена")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка перехода на страницу: {e}")
            return False
    
    async def get_page_content(self) -> tuple[str, List[Dict[str, Any]]]:
        """
        Получает содержимое страницы и cookies
        
        Returns:
            Tuple (HTML содержимое, список cookies)
        """
        try:
            if not self.page:
                return "", []
            
            # Получаем HTML содержимое
            html_content = await self.page.content()
            
            # Получаем cookies
            cookies = await self.context.cookies()
            
            logger.info(f"📄 Получено содержимое: {len(html_content)} символов, {len(cookies)} cookies")
            
            return html_content, cookies
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения содержимого: {e}")
            return "", []
    
    async def wait_for_pdf_requests(self, timeout: int = 30) -> List[Dict[str, Any]]:
        """
        Ждет появления PDF запросов
        
        Args:
            timeout: Таймаут ожидания в секундах
            
        Returns:
            Список перехваченных PDF запросов
        """
        logger.info(f"⏳ Ожидание PDF запросов ({timeout}с)...")
        
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            if self.pdf_requests:
                logger.info(f"✅ Найдено {len(self.pdf_requests)} PDF запросов")
                break
            await asyncio.sleep(1)
        
        return self.pdf_requests.copy()
    
    async def download_intercepted_pdfs(self) -> List[str]:
        """
        Скачивает перехваченные PDF файлы
        
        Returns:
            Список путей к скачанным файлам
        """
        if not self.pdf_requests:
            logger.warning("⚠️ Нет перехваченных PDF запросов")
            return []
        
        downloaded_files = []
        
        for i, req_info in enumerate(self.pdf_requests):
            try:
                logger.info(f"📥 Скачивание PDF {i+1}: {req_info['url']}")
                
                # Выполняем запрос
                response = await self.page.request.get(req_info['url'])
                
                if response.status == 200:
                    content = await response.body()
                    
                    # Проверяем, что это PDF
                    if content.startswith(b'%PDF'):
                        # Генерируем имя файла
                        import hashlib
                        url_hash = hashlib.md5(req_info['url'].encode()).hexdigest()[:8]
                        filename = f"playwright_{url_hash}.pdf"
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
    
    async def close(self):
        """Закрывает браузер и освобождает ресурсы"""
        try:
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
            
            logger.info("✅ Playwright закрыт")
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка закрытия Playwright: {e}")
    
    async def __aenter__(self):
        """Async context manager entry"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()


# Синхронная обертка для совместимости с существующим кодом
class PlaywrightPDFExtractorSync:
    """
    Синхронная обертка для PlaywrightPDFExtractor
    """
    
    def __init__(self, files_dir: str):
        self.files_dir = files_dir
        self.extractor = None
    
    def extract_pdfs(self, case_url: str, timeout: int = 30) -> List[str]:
        """
        Синхронный метод извлечения PDF файлов
        
        Args:
            case_url: URL страницы дела
            timeout: Таймаут ожидания в секундах
            
        Returns:
            Список путей к скачанным файлам
        """
        async def _extract():
            async with PlaywrightPDFExtractor(self.files_dir) as extractor:
                # Переходим на страницу
                if not await extractor.navigate_to_case(case_url):
                    return []
                
                # Ждем PDF запросов
                await extractor.wait_for_pdf_requests(timeout)
                
                # Скачиваем PDF файлы
                return await extractor.download_intercepted_pdfs()
        
        try:
            return asyncio.run(_extract())
        except Exception as e:
            logger.error(f"❌ Ошибка синхронного извлечения: {e}")
            return []
