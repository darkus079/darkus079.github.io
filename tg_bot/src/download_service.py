import os
import tempfile
import zipfile
import time
import logging
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoAlertPresentException, TimeoutException, NoSuchElementException
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
        chrome_options.add_argument("--disable-notifications")
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

        self._close_initial_popups(driver)

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

            # === НОВАЯ ЛОГИКА: ПРОХОД ПО СТРАНИЦАМ С УТОЧНЕНИЕМ КОНТЕЙНЕРА ===
            current_page = 1
            total_docs = 0

            while True:
                # Уточняем, что ищем PDF только внутри #chrono_ed_content
                pdf_links = driver.find_elements(
                    By.XPATH,
                    "//div[@id='chrono_ed_content']//a[contains(@href, '/Kad/PdfDocument/')]"
                )
                logger.info(f"Найдено PDF на странице {current_page}: {len(pdf_links)}")

                if not pdf_links:
                    logger.info(f"⚠️ Нет документов на странице {current_page}, пропускаем.")
                else:
                    # Скачиваем каждый PDF
                    for i, link in enumerate(pdf_links):
                        text = link.text.strip() or f"doc_{total_docs + i + 1}"
                        logger.info(f"⬇️ Скачиваем: {text} (страница {current_page})")
                        link.click()
                        time.sleep(7)  # ждём загрузку
                    total_docs += len(pdf_links)

                # Уточняем, что ищем пагинацию только внутри #chrono_ed_content или рядом с ним
                # Найти div.b-chrono-pagination, который НЕ содержит input с placeholder 'Поиск участника...'
                # и который находится внутри #chrono_ed_content
                try:
                    pagination_container = driver.find_element(
                        By.XPATH,
                        "//div[@id='chrono_ed_content']//div[contains(@class, 'b-chrono-pagination') and contains(@class, 'js-chrono-pagination') and not(.//input[@placeholder='Поиск участника...'])]"
                    )
                except NoSuchElementException:
                    logger.info("⚠️ Пагинация не найдена внутри #chrono_ed_content. Возможно, закончились страницы.")
                    break # Если пагинации нет, выходим

                # Теперь ищем кнопку "next" *внутри найденного* контейнера пагинации
            # Теперь ищем кнопку "next" *внутри найденного* контейнера пагинации
            # Теперь ищем кнопку "next" *внутри найденного* контейнера пагинации
                try:
                    next_button = pagination_container.find_element(
                        By.XPATH,
                        ".//li[contains(@class, 'js-chrono-pagination-pager-item--arrow') and contains(@class, 'next')]"
                    )

                    # Проверяем, есть ли элемент следующей страницы *внутри этого же контейнера*
                    next_page_num_element = pagination_container.find_elements(
                        By.XPATH,
                        f".//li[contains(@class, 'js-chrono-pagination-pager-item') and @data-page_num='{current_page + 1}']"
                    )

                    if not next_page_num_element:
                        # Если элемента следующей страницы нет в *этом* контейнере пагинации
                        logger.info(f"✅ Больше нет страниц в текущем контейнере пагинации. Текущая страница {current_page} - последняя.")
                        break

                    # --- ЗАПОМИНАЕМ ТЕКУЩУЮ АКТИВНУЮ СТРАНИЦУ ---
                    old_active_page_num = current_page
                    logger.debug(f"DEBUG: Попытка перехода с {old_active_page_num} на {old_active_page_num + 1}")

                    # Если элемент следующей страницы есть, кликаем по кнопке next
                    logger.info(f"➡️ Переход на следующую страницу ({current_page + 1})...")
                    next_button.click()

                    # --- ЖДЁМ, ЧТО DOM ОБНОВИТСЯ ---
                    # Повторно ищем контейнер пагинации, ожидая, что он обновится
                    try:
                        WebDriverWait(driver, 10).until(
                            EC.staleness_of(pagination_container) # Ждём, что старый элемент станет "старым"
                        )
                        logger.debug("DEBUG: Старый контейнер пагинации стал stale.")
                    except:
                        logger.debug("DEBUG: Старый контейнер пагинации не стал stale, но возможно обновился.")

                    # --- ПОВТОРНО ИЩЕМ КОНТЕЙНЕР ПАГИНАЦИИ ---
                    try:
                        pagination_container = driver.find_element(
                            By.XPATH,
                            "//div[@id='chrono_ed_content']//div[contains(@class, 'b-chrono-pagination') and contains(@class, 'js-chrono-pagination') and not(.//input[@placeholder='Поиск участника...'])]"
                        )
                    except NoSuchElementException:
                        logger.info("⚠️ Контейнер пагинации не найден после перехода на следующую страницу. Возможно, закончились страницы.")
                        break # Если пагинации нет, выходим

                    # --- ЖДЁМ, ЧТО АКТИВНАЯ СТРАНИЦА ОБНОВИТСЯ ---
                    # Ищем элемент с data-page_num, равным ожидаемому
                    expected_page_element = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located(
                            (By.XPATH, f".//li[@data-page_num='{old_active_page_num + 1}' and contains(@class, 'b-chrono-pagination-pager-item--active')]")
                        ),
                        message=f"Active page element for {old_active_page_num + 1} not found after click"
                    )

                    # Проверяем номер новой активной страницы
                    new_active_page_num = int(expected_page_element.get_attribute("data-page_num"))

                    logger.debug(f"DEBUG: Новая активная страница: {new_active_page_num}, ожидалась: {old_active_page_num + 1}")

                    if new_active_page_num == old_active_page_num:
                        # Клик не привёл к переходу, значит, больше страниц нет или кнопка неактивна
                        logger.info(f"✅ Больше нет страниц. Текущая страница {old_active_page_num} - последняя.")
                        break

                    current_page = new_active_page_num

                except NoSuchElementException:
                    # Если кнопка "next" не найдена в *этом* контейнере пагинации
                    logger.info(f"✅ Кнопка 'next' не найдена в контейнере пагинации. Текущая страница {current_page} - последняя.")
                    break
                except Exception as e:
                    # Перехватываем любые другие ошибки в этом блоке (например, TimeoutException от WebDriverWait)
                    logger.error(f"❌ Ошибка при обработке пагинации: {e}")
                    # Возможно, стоит выйти из цикла, если не можем обработать переход
                    break

            if total_docs == 0:
                logger.info(f"⚠️ Нет документов в деле {case_uuid}")
                return None

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

    def _close_initial_popups(self, driver):
        """Закрывает все всплывающие окна при запуске браузера"""
        try:
            # Даем время на появление окон
            time.sleep(3)
            
            # 1. Ваше новое всплывающее окно (с вашим CSS-селектором)
            try:
                close_button = driver.find_element(
                    By.CSS_SELECTOR,
                    "a.b-promo_notification-popup-close.js-promo_notification-popup-close"
                )
                close_button.click()
                logger.info("✅ Основное всплывающее окно закрыто")
                time.sleep(1)
            except Exception as e:
                logger.debug(f"Основное всплывающее окно не найдено: {e}")
            
            # 2. Окно "Устаревшая версия браузера" (если есть)
            try:
                close_button = driver.find_element(
                    By.XPATH, 
                    "//div[@class='b-browsers-popup-close']"
                )
                close_button.click()
                logger.debug("✅ Окно устаревшего браузера закрыто")
                time.sleep(0.5)
            except Exception as e:
                logger.debug(f"Окно устаревшего браузера не найдено: {e}")
                
        except Exception as e:
            logger.warning(f"Ошибка при закрытии всплывающих окон: {e}")