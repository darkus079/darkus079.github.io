#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Альтернативные алгоритмы для извлечения PDF файлов
"""

import os
import time
import logging
import requests
import json
import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import tempfile
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

logger = logging.getLogger(__name__)

class PDFExtractionAlgorithms:
    """Класс с альтернативными алгоритмами извлечения PDF"""
    
    def __init__(self, driver, files_dir):
        self.driver = driver
        self.files_dir = files_dir
        self.downloaded_files = []
    
    def extract_pdfs_algorithm_1_direct_links(self, case_number):
        """Алгоритм 1: Прямые ссылки на PDF через data-атрибуты"""
        logger.info("🔍 Алгоритм 1: Поиск прямых ссылок на PDF")
        
        try:
            # Ищем элементы с data-атрибутами, содержащими ссылки на PDF
            pdf_elements = self.driver.find_elements(By.CSS_SELECTOR, 
                '[data-pdf], [data-file], [data-document], [data-url]')
            
            pdf_links = []
            for element in pdf_elements:
                for attr in ['data-pdf', 'data-file', 'data-document', 'data-url']:
                    if element.get_attribute(attr):
                        pdf_links.append(element.get_attribute(attr))
            
            # Также ищем скрытые ссылки
            hidden_links = self.driver.find_elements(By.CSS_SELECTOR, 
                'a[href*=".pdf"]:not([style*="display: none"])')
            
            for link in hidden_links:
                href = link.get_attribute('href')
                if href and href not in pdf_links:
                    pdf_links.append(href)
            
            logger.info(f"📄 Найдено {len(pdf_links)} прямых ссылок на PDF")
            return self._download_files(pdf_links, "algorithm_1")
            
        except Exception as e:
            logger.error(f"❌ Ошибка в алгоритме 1: {e}")
            return []
    
    def extract_pdfs_algorithm_2_javascript_links(self, case_number):
        """Алгоритм 2: Извлечение ссылок через JavaScript"""
        logger.info("🔍 Алгоритм 2: Извлечение ссылок через JavaScript")
        
        try:
            # Выполняем JavaScript для поиска PDF ссылок
            js_code = """
            var pdfLinks = [];
            
            // Поиск в data-атрибутах
            var elements = document.querySelectorAll('[data-pdf], [data-file], [data-document]');
            elements.forEach(function(el) {
                ['data-pdf', 'data-file', 'data-document'].forEach(function(attr) {
                    var value = el.getAttribute(attr);
                    if (value && value.includes('.pdf')) {
                        pdfLinks.push(value);
                    }
                });
            });
            
            // Поиск в onclick событиях
            var onclickElements = document.querySelectorAll('[onclick*="pdf"], [onclick*="download"]');
            onclickElements.forEach(function(el) {
                var onclick = el.getAttribute('onclick');
                var match = onclick.match(/['"]([^'"]*\.pdf[^'"]*)['"]/);
                if (match) {
                    pdfLinks.push(match[1]);
                }
            });
            
            // Поиск в скрытых формах
            var forms = document.querySelectorAll('form');
            forms.forEach(function(form) {
                var inputs = form.querySelectorAll('input[type="hidden"]');
                inputs.forEach(function(input) {
                    var value = input.value;
                    if (value && value.includes('.pdf')) {
                        pdfLinks.push(value);
                    }
                });
            });
            
            return pdfLinks;
            """
            
            pdf_links = self.driver.execute_script(js_code)
            logger.info(f"📄 Найдено {len(pdf_links)} ссылок через JavaScript")
            return self._download_files(pdf_links, "algorithm_2")
            
        except Exception as e:
            logger.error(f"❌ Ошибка в алгоритме 2: {e}")
            return []
    
    def extract_pdfs_algorithm_3_api_calls(self, case_number):
        """Алгоритм 3: Поиск API вызовов для получения PDF"""
        logger.info("🔍 Алгоритм 3: Поиск API вызовов")
        
        try:
            # Перехватываем сетевые запросы
            self.driver.execute_cdp_cmd('Network.enable', {})
            
            # Ищем элементы, которые могут вызывать API
            api_elements = self.driver.find_elements(By.CSS_SELECTOR, 
                '[onclick*="ajax"], [onclick*="fetch"], [onclick*="XMLHttpRequest"]')
            
            pdf_links = []
            for element in api_elements:
                try:
                    # Кликаем и ждем ответа
                    element.click()
                    time.sleep(2)
                    
                    # Получаем логи сети
                    logs = self.driver.get_log('performance')
                    for log in logs:
                        message = json.loads(log['message'])
                        if message['message']['method'] == 'Network.responseReceived':
                            url = message['message']['params']['response']['url']
                            if '.pdf' in url.lower():
                                pdf_links.append(url)
                                
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка при обработке API элемента: {e}")
                    continue
            
            logger.info(f"📄 Найдено {len(pdf_links)} ссылок через API")
            return self._download_files(pdf_links, "algorithm_3")
            
        except Exception as e:
            logger.error(f"❌ Ошибка в алгоритме 3: {e}")
            return []
    
    def extract_pdfs_algorithm_4_dynamic_content(self, case_number):
        """Алгоритм 4: Поиск динамически загружаемого контента"""
        logger.info("🔍 Алгоритм 4: Поиск динамического контента")
        
        try:
            # Ждем загрузки динамического контента
            time.sleep(3)
            
            # Прокручиваем страницу для загрузки ленивого контента
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            # Ищем элементы с lazy loading
            lazy_elements = self.driver.find_elements(By.CSS_SELECTOR, 
                '[data-src*=".pdf"], [data-lazy*=".pdf"], [loading="lazy"]')
            
            pdf_links = []
            for element in lazy_elements:
                # Прокручиваем к элементу
                self.driver.execute_script("arguments[0].scrollIntoView();", element)
                time.sleep(1)
                
                # Получаем src после загрузки
                src = element.get_attribute('src') or element.get_attribute('data-src')
                if src and '.pdf' in src.lower():
                    pdf_links.append(src)
            
            # Также ищем в iframe
            iframes = self.driver.find_elements(By.TAG_NAME, 'iframe')
            for iframe in iframes:
                try:
                    self.driver.switch_to.frame(iframe)
                    iframe_links = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*=".pdf"]')
                    for link in iframe_links:
                        href = link.get_attribute('href')
                        if href:
                            pdf_links.append(href)
                    self.driver.switch_to.default_content()
                except Exception as e:
                    self.driver.switch_to.default_content()
                    continue
            
            logger.info(f"📄 Найдено {len(pdf_links)} ссылок в динамическом контенте")
            return self._download_files(pdf_links, "algorithm_4")
            
        except Exception as e:
            logger.error(f"❌ Ошибка в алгоритме 4: {e}")
            return []
    
    def extract_pdfs_algorithm_5_form_submission(self, case_number):
        """Алгоритм 5: Отправка форм для получения PDF"""
        logger.info("🔍 Алгоритм 5: Отправка форм")
        
        try:
            pdf_links = []
            
            # Ищем формы с PDF
            forms = self.driver.find_elements(By.TAG_NAME, 'form')
            for form in forms:
                try:
                    # Ищем скрытые поля с PDF ссылками
                    hidden_inputs = form.find_elements(By.CSS_SELECTOR, 'input[type="hidden"]')
                    for input_elem in hidden_inputs:
                        value = input_elem.get_attribute('value')
                        if value and '.pdf' in value.lower():
                            pdf_links.append(value)
                    
                    # Пробуем отправить форму
                    submit_btn = form.find_element(By.CSS_SELECTOR, 'input[type="submit"], button[type="submit"]')
                    if submit_btn:
                        submit_btn.click()
                        time.sleep(3)
                        
                        # Ищем новые PDF ссылки после отправки формы
                        new_links = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*=".pdf"]')
                        for link in new_links:
                            href = link.get_attribute('href')
                            if href and href not in pdf_links:
                                pdf_links.append(href)
                                
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка при обработке формы: {e}")
                    continue
            
            logger.info(f"📄 Найдено {len(pdf_links)} ссылок через формы")
            return self._download_files(pdf_links, "algorithm_5")
            
        except Exception as e:
            logger.error(f"❌ Ошибка в алгоритме 5: {e}")
            return []
    
    def extract_pdfs_algorithm_6_network_analysis(self, case_number):
        """Алгоритм 6: Анализ сетевого трафика"""
        logger.info("🔍 Алгоритм 6: Анализ сетевого трафика")
        
        try:
            # Включаем перехват сетевых запросов
            self.driver.execute_cdp_cmd('Network.enable', {})
            
            # Выполняем действия, которые могут вызвать загрузку PDF
            actions = [
                "window.scrollTo(0, document.body.scrollHeight);",
                "document.querySelectorAll('a').forEach(a => a.click());",
                "document.querySelectorAll('button').forEach(b => b.click());"
            ]
            
            pdf_links = []
            for action in actions:
                try:
                    self.driver.execute_script(action)
                    time.sleep(2)
                    
                    # Анализируем сетевые запросы
                    logs = self.driver.get_log('performance')
                    for log in logs:
                        try:
                            message = json.loads(log['message'])
                            if message['message']['method'] == 'Network.responseReceived':
                                url = message['message']['params']['response']['url']
                                if '.pdf' in url.lower():
                                    pdf_links.append(url)
                        except:
                            continue
                            
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка при выполнении действия: {e}")
                    continue
            
            logger.info(f"📄 Найдено {len(pdf_links)} ссылок через анализ сети")
            return self._download_files(pdf_links, "algorithm_6")
            
        except Exception as e:
            logger.error(f"❌ Ошибка в алгоритме 6: {e}")
            return []
    
    def extract_pdfs_algorithm_7_content_parsing(self, case_number):
        """Алгоритм 7: Парсинг HTML контента"""
        logger.info("🔍 Алгоритм 7: Парсинг HTML контента")
        
        try:
            # Получаем HTML контент
            html_content = self.driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')
            
            pdf_links = []
            
            # Ищем все ссылки с PDF
            links = soup.find_all('a', href=re.compile(r'\.pdf', re.IGNORECASE))
            for link in links:
                href = link.get('href')
                if href:
                    pdf_links.append(href)
            
            # Ищем в data-атрибутах
            elements_with_data = soup.find_all(attrs={'data-pdf': True})
            for element in elements_with_data:
                data_pdf = element.get('data-pdf')
                if data_pdf:
                    pdf_links.append(data_pdf)
            
            # Ищем в JavaScript коде
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string:
                    js_matches = re.findall(r'["\']([^"\']*\.pdf[^"\']*)["\']', script.string)
                    pdf_links.extend(js_matches)
            
            # Ищем в комментариях HTML
            comments = soup.find_all(string=lambda text: isinstance(text, str) and '.pdf' in text)
            for comment in comments:
                matches = re.findall(r'https?://[^\s]+\.pdf', comment)
                pdf_links.extend(matches)
            
            logger.info(f"📄 Найдено {len(pdf_links)} ссылок через парсинг HTML")
            return self._download_files(pdf_links, "algorithm_7")
            
        except Exception as e:
            logger.error(f"❌ Ошибка в алгоритме 7: {e}")
            return []
    
    def extract_pdfs_algorithm_8_advanced_selenium(self, case_number):
        """Алгоритм 8: Продвинутые методы Selenium"""
        logger.info("🔍 Алгоритм 8: Продвинутые методы Selenium")
        
        try:
            pdf_links = []
            
            # Используем ActionChains для сложных взаимодействий
            from selenium.webdriver.common.action_chains import ActionChains
            actions = ActionChains(self.driver)
            
            # Ищем элементы с hover эффектами
            hover_elements = self.driver.find_elements(By.CSS_SELECTOR, 
                '[onmouseover], [onmouseenter], .hover, .tooltip')
            
            for element in hover_elements:
                try:
                    actions.move_to_element(element).perform()
                    time.sleep(1)
                    
                    # Ищем появившиеся PDF ссылки
                    new_links = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*=".pdf"]')
                    for link in new_links:
                        href = link.get_attribute('href')
                        if href and href not in pdf_links:
                            pdf_links.append(href)
                            
                except Exception as e:
                    continue
            
            # Ищем элементы с двойным кликом
            double_click_elements = self.driver.find_elements(By.CSS_SELECTOR, 
                '[ondblclick], .double-click')
            
            for element in double_click_elements:
                try:
                    actions.double_click(element).perform()
                    time.sleep(2)
                    
                    # Ищем новые PDF ссылки
                    new_links = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*=".pdf"]')
                    for link in new_links:
                        href = link.get_attribute('href')
                        if href and href not in pdf_links:
                            pdf_links.append(href)
                            
                except Exception as e:
                    continue
            
            # Ищем элементы с правым кликом
            right_click_elements = self.driver.find_elements(By.CSS_SELECTOR, 
                '[oncontextmenu], .context-menu')
            
            for element in right_click_elements:
                try:
                    actions.context_click(element).perform()
                    time.sleep(1)
                    
                    # Ищем в контекстном меню
                    context_links = self.driver.find_elements(By.CSS_SELECTOR, 
                        '.context-menu a[href*=".pdf"], .dropdown a[href*=".pdf"]')
                    for link in context_links:
                        href = link.get_attribute('href')
                        if href and href not in pdf_links:
                            pdf_links.append(href)
                            
                except Exception as e:
                    continue
            
            logger.info(f"📄 Найдено {len(pdf_links)} ссылок через продвинутые методы")
            return self._download_files(pdf_links, "algorithm_8")
            
        except Exception as e:
            logger.error(f"❌ Ошибка в алгоритме 8: {e}")
            return []
    
    def _download_files(self, pdf_links, algorithm_name):
        """Скачивание найденных PDF файлов"""
        downloaded_files = []
        
        for i, link in enumerate(pdf_links):
            try:
                # Очищаем ссылку
                if link.startswith('//'):
                    link = 'https:' + link
                elif link.startswith('/'):
                    link = self.driver.current_url.split('/')[0] + '//' + self.driver.current_url.split('/')[2] + link
                elif not link.startswith('http'):
                    link = urljoin(self.driver.current_url, link)
                
                # Генерируем имя файла
                filename = f"{algorithm_name}_file_{i+1}.pdf"
                filepath = os.path.join(self.files_dir, filename)
                
                # Скачиваем файл
                response = requests.get(link, timeout=30)
                if response.status_code == 200 and response.content:
                    with open(filepath, 'wb') as f:
                        f.write(response.content)
                    
                    # Проверяем, что файл действительно PDF
                    if filepath.endswith('.pdf') and len(response.content) > 1000:
                        downloaded_files.append(filepath)
                        logger.info(f"✅ Скачан: {filename} ({len(response.content)} байт)")
                    else:
                        os.remove(filepath)
                        logger.warning(f"⚠️ Файл {filename} не является PDF или слишком мал")
                else:
                    logger.warning(f"⚠️ Не удалось скачать {link}: HTTP {response.status_code}")
                    
            except Exception as e:
                logger.error(f"❌ Ошибка при скачивании {link}: {e}")
                continue
        
        return downloaded_files
    
    def run_all_algorithms(self, case_number):
        """Запуск всех алгоритмов извлечения PDF"""
        logger.info("🚀 Запуск всех алгоритмов извлечения PDF")
        
        all_downloaded_files = []
        algorithms = [
            self.extract_pdfs_algorithm_1_direct_links,
            self.extract_pdfs_algorithm_2_javascript_links,
            self.extract_pdfs_algorithm_3_api_calls,
            self.extract_pdfs_algorithm_4_dynamic_content,
            self.extract_pdfs_algorithm_5_form_submission,
            self.extract_pdfs_algorithm_6_network_analysis,
            self.extract_pdfs_algorithm_7_content_parsing,
            self.extract_pdfs_algorithm_8_advanced_selenium
        ]
        
        for i, algorithm in enumerate(algorithms, 1):
            try:
                logger.info(f"🔄 Запуск алгоритма {i}/8")
                files = algorithm(case_number)
                all_downloaded_files.extend(files)
                logger.info(f"✅ Алгоритм {i} завершен: найдено {len(files)} файлов")
            except Exception as e:
                logger.error(f"❌ Ошибка в алгоритме {i}: {e}")
                continue
        
        # Удаляем дубликаты
        unique_files = list(set(all_downloaded_files))
        logger.info(f"🎉 Всего найдено уникальных файлов: {len(unique_files)}")
        
        return unique_files
