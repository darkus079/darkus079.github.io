import asyncio
import logging
import os
from kafka import KafkaConsumer
from aiogram import Bot
from src.config import settings
from tg_bot.src.download_service import DownloadService
import json

logger = logging.getLogger(__name__)

class ParsingWorker:
    def __init__(self, worker_id: str = "worker-1"):
        self.worker_id = worker_id
        self.bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        self.download_service = DownloadService()
        self.consumer = None
        self.is_running = False
    
    async def start(self):
        """Запускает worker"""
        logger.info(f"👷 Запуск {self.worker_id}...")
        
        try:
            self.consumer = KafkaConsumer(
                'parsing-tasks',
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
                group_id='parsing-workers',
                value_deserializer=lambda v: json.loads(v.decode('utf-8')),
                auto_offset_reset='earliest',
                enable_auto_commit=True,
                max_poll_interval_ms=700000
            )
            logger.info("✅ Kafka Consumer подключен")
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к Kafka: {e}")
            return
        
        self.is_running = True
        await self._process_messages()
    
    async def _process_messages(self):
        """Обрабатывает сообщения из Kafka"""
        logger.info(f"🔄 {self.worker_id} начал обработку сообщений...")
        
        for message in self.consumer:
            if not self.is_running:
                break
                
            try:
                task_data = message.value
                await self._process_task(task_data)
            except Exception as e:
                logger.error(f"❌ {self.worker_id} ошибка обработки сообщения: {e}")
    
    async def _process_task(self, task_data: dict):
        """Обрабатывает одну задачу со скачиванием файлов"""
        case_number = task_data['case_number']
        user_id = task_data['user_id']
        chat_id = task_data['chat_id']
        
        logger.info(f"📥 {self.worker_id} получил задачу: {case_number}")
        
        try:
            # Уведомляем о начале обработки
            await self.bot.send_message(
                chat_id=chat_id,
                text=f"🔍 Обработка дела: {case_number}\n⏳ Поиск UUID и скачивание документов... Это займет 1-2 минуты"
            )
            
            # Автоматически получаем UUID по номеру дела
            case_uuid = await self._get_case_uuid(case_number)
            
            if not case_uuid:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ Не удалось найти дело с номером: {case_number}\nПроверьте правильность номера дела."
                )
                return
            
            # Скачиваем документы
            logger.info(f"🔄 Скачивание документов для UUID: {case_uuid}")
            archive_path = self.download_service.download_case_documents(case_uuid)
            
            if archive_path:
                # Отправляем архив
                await self._send_archive(chat_id, case_number, archive_path)
                logger.info(f"✅ {self.worker_id} завершил задачу: {case_number}")
            else:
                await self.bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ Не удалось скачать документы для дела: {case_number}\nВозможно, в деле нет доступных документов."
                )
            
        except Exception as e:
            logger.error(f"❌ {self.worker_id} ошибка обработки задачи {case_number}: {e}")
            await self._send_error(chat_id, case_number, str(e))

    def _normalize_case_number(self, case_number: str) -> list[str]:
        """Возвращает возможные варианты написания номера дела (с 2- и 4-значным годом)."""
        import re
        case_number = case_number.strip().upper()
        match = re.search(r'/(\d{2,4})$', case_number)
        if not match:
            return [case_number]
        
        year_part = match.group(1)
        prefix = case_number[:match.start()]
        variants = {case_number}
        
        if len(year_part) == 2:
            full_year = "20" + year_part if 0 <= int(year_part) <= 99 else year_part
            variants.add(f"{prefix}/{full_year}")
        elif len(year_part) == 4 and year_part.startswith("20"):
            short_year = year_part[2:]
            variants.add(f"{prefix}/{short_year}")
        
        return list(variants)


    def _case_numbers_match(self, query: str, text: str) -> bool:
        """Проверяет, содержится ли номер дела в тексте (без учёта пробелов и спецсимволов)."""
        import re
        clean_query = re.sub(r'[^А-ЯA-Z0-9/]', '', query.upper())
        clean_text = re.sub(r'[^А-ЯA-Z0-9/]', '', text.upper())
        return clean_query in clean_text

    # Оставил для тестов, чтобы в случае чего пофиксить
    # async def _get_case_uuid(self, case_number: str) -> str:
    #     """Получает UUID дела по его номеру"""
        
    #     # Известные UUID для тестирования (только проверенные)
    #     known_uuids = {
    #         "А50-5568/08": "67f6384a-144d-4102-8831-e5c9a1a4c7bc",
    #     }
        
    #     if case_number in known_uuids:
    #         logger.info(f"✅ Используем проверенный UUID: {known_uuids[case_number]}")
    #         return known_uuids[case_number]
        
    #     # Для новых дел используем улучшенный поиск с проверкой
    #     uuid = await self._get_case_uuid_improved(case_number)
    #     if uuid:
    #         logger.info(f"✅ Найден и проверен UUID для дела {case_number}: {uuid}")
    #         return uuid
        
    #     logger.warning(f"⚠️ Не удалось найти UUID для дела {case_number}")
    #     return None

    async def _get_case_uuid(self, case_number: str) -> str | None:
        """Получает UUID дела по его номеру — только через улучшенный поиск."""
        uuid = await self._get_case_uuid_improved(case_number)
        if uuid:
            logger.info(f"✅ Найден UUID для дела {case_number}: {uuid}")
            return uuid

        logger.warning(f"⚠️ Не удалось найти UUID для дела {case_number}")
        return None
    
    async def _get_case_uuid_improved(self, case_number: str) -> str | None:
        """Ищет UUID дела по номеру, пробуя несколько форматов года."""
        variants = self._normalize_case_number(case_number)
        logger.info(f"🔍 Пробуем варианты: {variants}")
        
        for variant in variants:
            uuid = await self._search_case_by_number(variant)
            if uuid:
                return uuid
        return None
    
    async def _search_case_by_number(self, case_number: str) -> str | None:
        """Ищет UUID дела по номеру через Selenium (ввод в форму)."""
        from selenium import webdriver
        from selenium.webdriver.common.by import By
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium.common.exceptions import TimeoutException, NoSuchElementException
        import time

        chrome_options = Options()
        # Убран --headless — kad.arbitr.ru блокирует headless
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.6778.86 Safari/537.36")  # ← Актуальная версия!
        chrome_options.add_argument("--disable-web-security")
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--disable-features=IsolateOrigins,site-per-process")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)

        driver = webdriver.Chrome(options=chrome_options)
        driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
            """
        })
        wait = WebDriverWait(driver, 20)

        try:
            logger.info(f"🌐 Открываем kad.arbitr.ru для поиска: {case_number}")
            driver.get("https://kad.arbitr.ru/")
            time.sleep(3)

            try:
                close_button = driver.find_element(
                    By.CSS_SELECTOR,
                    "a.b-promo_notification-popup-close.js-promo_notification-popup-close"
                )
                close_button.click()
                logger.debug("✅ Основное всплывающее окно закрыто")
                time.sleep(1)
            except Exception as e:
                logger.debug(f"Основное всплывающее окно не найдено: {e}")

            # Закрыть всплывающее окно "Устаревшая версия браузера"
            try:
                close_button = driver.find_element(By.XPATH, "//div[@class='b-browsers-popup-close']")
                driver.execute_script("arguments[0].click();", close_button)
                logger.debug("✅ Всплывающее окно закрыто")
            except Exception as e:
                logger.warning(f"⚠️ Не удалось закрыть всплывающее окно: {e}")

            # === Ввод номера дела ===
            try:
                case_field = wait.until(
                    EC.presence_of_element_located((By.XPATH, "//input[@placeholder='например, А50-5568/08']"))
                )
                case_field.clear()
                case_field.send_keys(case_number.strip())
                logger.debug("✅ Поле ввода найдено и заполнено")
            except TimeoutException:
                logger.error("❌ Поле ввода не найдено")
                return None

            # === Клик по кнопке "Найти" ===
            try:
                search_btn = wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//button[@alt='Найти']"))
                )
                search_btn.click()
                logger.debug("✅ Кнопка 'Найти' нажата")
            except Exception as e:
                logger.warning(f"⚠️ Не удалось нажать 'Найти': {e}")
                return None

            # === Ожидание результатов ===
            try:
                wait.until(
                    EC.any_of(
                        EC.presence_of_element_located((By.XPATH, "//a[@class='num_case' and contains(@href, '/Card/')]")),
                        EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "Нет результатов")
                    )
                )
            except TimeoutException:
                logger.warning("⚠️ Таймаут ожидания результатов")
                return None

            # === Проверка "Нет результатов" ===
            if "Нет результатов" in driver.find_element(By.TAG_NAME, "body").text:
                logger.info(f"🚫 Дело {case_number} не найдено")
                return None

            # === Поиск ссылки на карточку дела ===
            try:
                card_link = wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//a[@class='num_case' and contains(@href, '/Card/')]"))
                )
                href = card_link.get_attribute("href")
                uuid = href.split("/Card/")[-1].split("?")[0]
                if len(uuid) == 36:
                    logger.info(f"✅ Найден UUID: {uuid} для {case_number}")
                    return uuid
                else:
                    logger.warning(f"⚠️ UUID некорректной длины: {uuid}")
            except Exception as e:
                logger.warning(f"⚠️ Ошибка при извлечении UUID: {e}")

            logger.warning(f"⚠️ Не удалось найти ссылку на дело {case_number}")
            return None

        except Exception as e:
            logger.error(f"❌ Ошибка при поиске {case_number}: {e}")
            return None
        finally:
            driver.quit()

    async def _verify_case_number(self, driver, expected_case_number: str) -> bool:
        """Проверяет, что на текущей странице отображается правильный номер дела"""
        try:
            # Ищем номер дела на странице разными способами
            case_number_selectors = [
                "//*[contains(@class, 'b-case__number')]",
                "//*[contains(@class, 'case-number')]",
                "//*[contains(text(), '№ {}')]".format(expected_case_number),
                "//*[contains(text(), '{}')]".format(expected_case_number),
                "//h1[contains(text(), '{}')]".format(expected_case_number),
                "//title[contains(text(), '{}')]".format(expected_case_number)
            ]
            
            for selector in case_number_selectors:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    for element in elements:
                        element_text = element.text.strip()
                        if expected_case_number in element_text:
                            logger.info(f"✅ Подтвержден номер дела: {expected_case_number}")
                            return True
                except NoSuchElementException:
                    continue
            
            # Также проверяем заголовок страницы
            page_title = driver.title
            if expected_case_number in page_title:
                logger.info(f"✅ Номер дела подтвержден в заголовке: {page_title}")
                return True
                
            logger.warning(f"⚠️ На странице не найден номер дела: {expected_case_number}")
            return False
            
        except Exception as e:
            logger.warning(f"⚠️ Ошибка при проверке номера дела: {e}")
            return False
    
    async def _send_archive(self, chat_id: int, case_number: str, archive_path: str):
        """Отправляет ZIP-архив пользователю"""
        if not archive_path or not os.path.exists(archive_path):
            await self.bot.send_message(
                chat_id=chat_id,
                text=f"❌ Не удалось скачать документы для дела: {case_number}"
            )
            return
        
        try:
            # Читаем файл в память и создаем BufferedInputFile
            with open(archive_path, 'rb') as f:
                file_data = f.read()
            
            from aiogram.types import BufferedInputFile
            
            filename = f"documents_{case_number.replace('/', '_')}.zip"
            document = BufferedInputFile(file_data, filename=filename)
            
            # Отправляем архив
            await self.bot.send_document(
                chat_id=chat_id,
                document=document,
                caption=f"📦 Документы по делу: {case_number}"
            )
            
            # Уведомляем об успехе
            await self.bot.send_message(
                chat_id=chat_id,
                text=f"✅ Документы по делу {case_number} успешно скачаны и отправлены!"
            )
            
            # Очищаем временный архив
            self.download_service.cleanup_archive(archive_path)
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки архива: {e}")
            await self.bot.send_message(
                chat_id=chat_id,
                text=f"❌ Ошибка отправки документов: {e}"
            )
    
    async def _send_error(self, chat_id: int, case_number: str, error: str):
        """Отправляет сообщение об ошибке"""
        error_message = (
            f"❌ Ошибка при обработке дела {case_number}\n\n"
            f"Ошибка: {error}\n\n"
            f"Попробуйте позже или проверьте правильность номера дела."
        )
        await self.bot.send_message(chat_id=chat_id, text=error_message)
    
    async def stop(self):
        """Останавливает worker"""
        self.is_running = False
        if self.consumer:
            self.consumer.close()
        await self.bot.close()
        logger.info(f"🛑 {self.worker_id} остановлен")