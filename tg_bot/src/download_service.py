import os
import tempfile
import zipfile
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
import shutil

logger = logging.getLogger(__name__)

class DownloadService:
    def __init__(self):
        self.temp_dir = tempfile.gettempdir()
    
    def download_case_documents(self, case_uuid: str, output_dir: str = None):
        """
        Скачивает все PDF из раздела 'Электронное дело' для одного дела и архивирует их.
        Возвращает путь к созданному ZIP-архиву.
        """
        if output_dir is None:
            output_dir = self.temp_dir
        
        # Временная папка для скачивания
        temp_dir = tempfile.mkdtemp()
        logger.info(f"📁 Временная папка: {temp_dir}")

        # НАСТРОЙКИ КАК В ВАШЕМ РАБОЧЕМ СКРИПТЕ (БЕЗ HEADLESS!)
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("useAutomationExtension", False)
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])

        prefs = {
            "download.default_directory": temp_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
            "plugins.always_open_pdf_externally": True,
            "profile.default_content_setting_values.automatic_downloads": 1
        }
        chrome_options.add_experimental_option("prefs", prefs)

        driver = webdriver.Chrome(options=chrome_options)
        driver.execute_script("delete navigator.__proto__.webdriver")

        archive_path = os.path.join(output_dir, f"{case_uuid}.zip")
        
        try:
            logger.info(f"🔍 Обработка дела: {case_uuid}")
            driver.get(f"https://kad.arbitr.ru/Card/{case_uuid}")
            time.sleep(3)

            # Клик по вкладке "Электронное дело" - ТОЧНО КАК В ВАШЕМ СКРИПТЕ
            edoc_tab = driver.find_element(
                By.XPATH,
                "//div[contains(@class, 'b-case-chrono-button-text') and contains(., 'Электронное дело')]"
            )
            logger.info("📄 Переключаемся во вкладку 'Электронное дело'...")
            edoc_tab.click()
            time.sleep(6)

            # Найти все PDF-ссылки в этом разделе - ТОЧНО КАК В ВАШЕМ СКРИПТЕ
            pdf_links = driver.find_elements(
                By.XPATH,
                "//div[@id='chrono_ed_content']//a[contains(@href, '/Kad/PdfDocument/')]"
            )
            logger.info(f"Найдено PDF: {len(pdf_links)}")

            if not pdf_links:
                logger.info(f"⚠️ Нет документов в деле {case_uuid}")
                return None

            # Скачиваем каждый PDF - ТОЧНО КАК В ВАШЕМ СКРИПТЕ
            for i, link in enumerate(pdf_links):
                text = link.text.strip() or f"doc_{i+1}"
                logger.info(f"⬇️ Скачиваем: {text}")
                link.click()
                time.sleep(5)  # ждём загрузку

            # Упаковка в ZIP
            os.makedirs(output_dir, exist_ok=True)
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for filename in os.listdir(temp_dir):
                    if filename.endswith(".pdf"):
                        full_path = os.path.join(temp_dir, filename)
                        zipf.write(full_path, arcname=filename)
            logger.info(f"✅ Архив сохранён: {archive_path}")
            
            return archive_path

        except Exception as e:
            logger.error(f"❌ Ошибка при обработке дела {case_uuid}: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            driver.quit()
            # Удаляем временные файлы
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def cleanup_archive(self, archive_path: str):
        """Очищает временный архив после отправки"""
        try:
            if os.path.exists(archive_path):
                os.remove(archive_path)
                logger.info(f"🗑️ Удален временный архив: {archive_path}")
        except Exception as e:
            logger.warning(f"⚠️ Ошибка удаления архива: {e}")