"""from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import os
import time

# Папка для сохранения
download_dir = os.path.expanduser("/Users/barbatos/work/kad_arbitr_parser/test")
os.makedirs(download_dir, exist_ok=True)

# Настройки Chrome
chrome_options = Options()
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_experimental_option("useAutomationExtension", False)
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])

prefs = {
    "download.default_directory": download_dir,
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "safebrowsing.enabled": True,
    "plugins.always_open_pdf_externally": True,
}
chrome_options.add_experimental_option("prefs", prefs)

driver = webdriver.Chrome(options=chrome_options)
# Маскируем Selenium
driver.execute_script("delete navigator.__proto__.webdriver")

try:
    # ✅ Правильный URL — карточка дела
    case_url = "https://kad.arbitr.ru/Card/67f6384a-144d-4102-8831-e5c9a1a4c7bc"
    driver.get(case_url)

    print("Текущий URL:", driver.current_url)
    print("Заголовок страницы:", driver.title)

    # Ждём немного, чтобы документы подгрузились
    time.sleep(6)

    driver.click()
    # Ищем ссылки на PDF-документы (реальные)
    pdf_links = driver.find_elements(By.XPATH, "//a[contains(@href, '/Kad/PdfDocument/')]")
    print(f"Найдено PDF-ссылок: {len(pdf_links)}")

    if not pdf_links:
        print("❌ Не найдено ссылок на PDF. Сохраняю HTML для отладки.")
        with open("debug.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
    else:
        # Скачиваем первый документ (или все)
        for i, link in enumerate(pdf_links[:1]):  # ограничим 1 файлом для теста
            href = link.get_attribute("href")
            text = link.text.strip() or f"doc_{i+1}"
            print(f"📄 Кликаем по: {text}")
            link.click()
            time.sleep(8)  # ждём загрузку

        print(f"✅ Готово! Файлы должны быть в: {download_dir}")

except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
finally:
    driver.quit()"""

"""from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
import time
import zipfile

# Папка для сохранения
download_dir = os.path.expanduser("/Users/barbatos/work/kad_arbitr_parser/test")
os.makedirs(download_dir, exist_ok=True)

# Настройки Chrome
chrome_options = Options()
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_experimental_option("useAutomationExtension", False)
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])

prefs = {
    "download.default_directory": download_dir,
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "safebrowsing.enabled": True,
    "plugins.always_open_pdf_externally": True,
    "profile.default_content_setting_values.automatic_downloads": 1
}
chrome_options.add_experimental_option("prefs", prefs)

driver = webdriver.Chrome(options=chrome_options)
driver.execute_script("delete navigator.__proto__.webdriver")

# Директория для скачивания архива
case_number = driver.find_element(By.ID, "caseName").get_attribute("value")
archive_path = os.path.join(output_dir, f"{case_number}.zip")

try:
    case_id = "67f6384a-144d-4102-8831-e5c9a1a4c7bc"
    driver.get(f"https://kad.arbitr.ru/Card/{case_id}")

    print("✅ Страница карточки загружена")
    time.sleep(3)

    WebDriverWait(driver, 10).until(
    EC.presence_of_element_located((By.CLASS_NAME, "b-case-chrono-button")))
    # Шаг 1: Находим и кликаем по вкладке "Электронное дело"
    # Обычно это ссылка с текстом "Электронное дело" или data-tab="edoc"
    edoc_tab = driver.find_element(
    By.XPATH,
    "//div[contains(@class, 'b-case-chrono-button-text') and contains(., 'Электронное дело')]")
    print("📄 Кликаем по вкладке 'Электронное дело'...")
    edoc_tab.click()
    
    # Шаг 2: Ждём, пока подгрузится содержимое (ищем контейнер документов)
    print("⏳ Ожидание загрузки документов...")
    time.sleep(8)  # можно заменить на WebDriverWait по элементу

    # Шаг 3: Ищем PDF-ссылки ТОЛЬКО внутри раздела "Электронное дело"
    # Обычно документы лежат в контейнере с классом вроде "b-case-edoc" или "edoc-content"
    pdf_links = driver.find_elements(
        By.XPATH,
        "//div[@id='chrono_ed_content']//a[contains(@href, '/Kad/PdfDocument/')]"
    )
    print(f"Найдено PDF-файлов в 'Электронное дело': {len(pdf_links)}")

    if not pdf_links:
        print("❌ PDF не найдены. Сохраняю страницу для отладки.")
        with open("debug_edoc.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
    else:
        # Скачиваем все найденные PDF
        for i, link in enumerate(pdf_links):
            text = link.text.strip() or f"doc_{i+1}"
            href = link.get_attribute("href")
            print(href, text)
            print(f"⬇️ Скачиваем: {text}")
            link.click()
            time.sleep(5)  # достаточно для большинства PDF

        print(f"✅ Все файлы сохранены в: {download_dir}")

        # 📦 Создаём ZIP-архив
        print("📦 Создаём архив...")
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for filename in os.listdir(download_dir):
                if filename.endswith(".pdf"):
                    file_path = os.path.join(download_dir, filename)
                    # Добавляем файл в архив с именем без полного пути
                    zipf.write(file_path, arcname=filename)

        print(f"✅ Архив создан: {archive_path}")

except Exception as e:
    print(f"❌ Ошибка: {e}")
    import traceback
    traceback.print_exc()
finally:
    driver.quit()"""

import os
import time
import zipfile
import tempfile
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By


def download_case_documents(case_id: str, output_dir: str):
    """
    Скачивает все PDF из раздела 'Электронное дело' для одного дела и архивирует их.
    """
    # Временная папка для скачивания
    temp_dir = tempfile.mkdtemp()
    print(f"📁 Временная папка: {temp_dir}")

    # Настройка Chrome
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

    archive_path = os.path.join(output_dir, f"{case_id}.zip")
    try:
        print(f"🔍 Обработка дела: {case_id}")
        driver.get(f"https://kad.arbitr.ru/Card/{case_id}")
        time.sleep(3)

        # Клик по вкладке "Электронное дело"
        edoc_tab = driver.find_element(
            By.XPATH,
            "//div[contains(@class, 'b-case-chrono-button-text') and contains(., 'Электронное дело')]"
        )
        print("📄 Переключаемся во вкладку 'Электронное дело'...")
        edoc_tab.click()
        time.sleep(6)

        # Найти все PDF-ссылки в этом разделе
        pdf_links = driver.find_elements(
            By.XPATH,
            "//div[@id='chrono_ed_content']//a[contains(@href, '/Kad/PdfDocument/')]"
        )
        print(f"Найдено PDF: {len(pdf_links)}")

        if not pdf_links:
            print(f"⚠️ Нет документов в деле {case_id}")
            return

        # Скачиваем каждый PDF
        for i, link in enumerate(pdf_links):
            text = link.text.strip() or f"doc_{i+1}"
            print(f"⬇️ Скачиваем: {text}")
            link.click()
            time.sleep(5)  # ждём загрузку

        # Упаковка в ZIP
        os.makedirs(output_dir, exist_ok=True)
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for filename in os.listdir(temp_dir):
                if filename.endswith(".pdf"):
                    full_path = os.path.join(temp_dir, filename)
                    zipf.write(full_path, arcname=filename)
        print(f"✅ Архив сохранён: {archive_path}")

    except Exception as e:
        print(f"❌ Ошибка при обработке дела {case_id}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        driver.quit()
        # Удаляем временные файлы
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


# === ОСНОВНАЯ ЧАСТЬ ===
if __name__ == "__main__":
    # Список UUID дел (замени на нужные)
    case_ids = [
        "67f6384a-144d-4102-8831-e5c9a1a4c7bc",
        # "another-uuid-here...",
        # "and-another-one..."
    ]

    # Папка, куда сохранять архивы
    output_dir = "/Users/barbatos/work/kad_arbitr_parser/test/case_archives"

    for case_id in case_ids:
        print("\n" + "="*60)
        download_case_documents(case_id, output_dir)

    print("\n🎉 Все дела обработаны!")