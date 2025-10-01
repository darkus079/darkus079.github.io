#!/usr/bin/env python3

import time
import random
from tqdm import tqdm
from selenium import webdriver
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium_stealth import stealth
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import ElementClickInterceptedException

import os

import subprocess


class AutoKad:
    """
    Bot for parsing kad.arbitr.ru
    Works under chromedriver with Selenium library support.
    """
    def __init__(self, driver_path=os.path.join(
        os.path.expanduser('~'), 'chromedriver'
    )):

        self.url_is_running = False  # whether the main page of ras.arbitr.ru is opened or not
        self.driver_path = driver_path
        self.url = 'https://ras.arbitr.ru/'
        self.driver = self.start_driver()

    @property
    def vpn_is_running(self):
        """
        Checks whether the vpn service is running or not.
        """
        vpn_status = subprocess.check_output(
            ["scutil", "--nc", "status", "Kaspersky VPN"]  # replace with your vpn util
        ).decode('utf-8')
        if vpn_status.startswith('Connected'):
            return True
        elif vpn_status.startswith('Disconnected'):
            return False
        else:
            raise ValueError('Unknown VPN status')

    @staticmethod
    def sleep(time_=None):
        """
        Sleep method for reconnecting
        """
        if time_ is not None:
            time.sleep(time_)
        else:
            time.sleep(random.uniform(a=1, b=3.5))

    def start_driver(self):
        """
        Starting the chrome driver
        """
        options = webdriver.ChromeOptions()

        # some configurations to escape bot detection
        options.add_argument("start-maximized")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        # next option will break the bypassing of bot detection
        # is created for automatic download of pdfs
        # options.add_experimental_option("prefs",
        #                                           {
        #                                               "plugins.always_open_pdf_externally": True
        #                                           })

        driver = webdriver.Chrome(options=options, executable_path=self.driver_path)

        stealth(driver,
                languages=["en-US", "en"],
                vendor="Google Inc.",
                platform="Win32",
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL Engine",
                fix_hairline=True,
                )

        return driver

    def start_url(self):
        """ Starting the main page"""
        self.driver.get(self.url)

        self.sleep()

        try:  # closing the pop-up window if there is one
            pop_up_window_button = (
                WebDriverWait(self.driver, 2.5).until(
                    ec.element_to_be_clickable(
                        (By.CSS_SELECTOR,
                         "a[class ='b-promo_notification-popup-close js-promo_notification-popup-close']")
                    )
                )
            )

            pop_up_window_button.click()
        except TimeoutException:
            pass

        self.url_is_running = True

    def start_url_routine(self):
        """This wrapper is made to escape some bot detection routine"""
        self.start_url()
        self.find_find_button().click()
        self.open_new_window()
        self.start_url()
        self.find_find_button().click()
        self.close_old_window()

    def catch_unable_to_load(self):
        duration = 5  # if is unable to load more than $duration seconds

        start_time = time.time()
        while self.please_wait_message_is_available():
            if (time.time() - start_time) > duration:
                return True
        return False

    def please_wait_message_is_available(self):
        descriptions = self.driver.find_elements(By.CSS_SELECTOR, "div[class='descr']")
        for descr in descriptions:
            if descr.text == 'Пожалуйста, подождите':
                return True
        return False

    def catch_429_error(self):
        """Catching 429 Too Many Requests Error"""
        try:
            banner = WebDriverWait(self.driver, 3).until(
                ec.presence_of_element_located(
                    (By.CSS_SELECTOR, "div[id='message']")
                )
            )
            banner_text = banner.find_element(By.TAG_NAME, 'h2').text
            if banner_text == 'Доступ к сервису ограничен!':
                return True
        except TimeoutException:
            pass

        return False

    def open_category_page(self, dispute_category):
        """Opening dispute category page with documents"""

        if not self.url_is_running:
            self.start_url_routine()

        arrows_list = self.find_drop_down_list_arrows()  # the left menu arrows for drop-down lists

        assert len(arrows_list) == 3, f'Three arrow objects are expected instead of {len(arrows_list)}.' \
                                      f'For dispute_type, dispute_category, and court_type arrows.'

        (dispute_type_arrow, dispute_category_arrow, court_type_arrow) = arrows_list

        # dispute_category_arrow.click()   # opening space of possible categories
        self.click_button(dispute_category_arrow)

        # dispute_category_cell = self.find_dispute_category_cell()
        # dispute_category_cell.clear()
        # dispute_category_cell.send_keys(dispute_category)

        dispute_category_pointer = self.find_from_drop_down_list(dispute_category)

        assert dispute_category_pointer is not None, f'The dispute_category {dispute_category} is not found.' \
                                                     f'Check out spelling.'

        dispute_category_pointer.click()

        find_button = self.find_find_button()
        self.click_button(find_button)  # using wrapper function for click to catch 429 error
        # if not self.url_is_running:  # if 429 is caught, url will be closed and bot will go to sleep for one hour
        #     self.open_category_page(dispute_category)

    def find_find_button(self):
        """
        Search for find button to open up the category
        """
        find_button = WebDriverWait(self.driver, 10).until(ec.element_to_be_clickable((
            By.CSS_SELECTOR,
            "button[alt='Найти']"
        )
        )
        )
        return find_button

    def find_dispute_category_cell(self):
        """
        Searching for the dispute categories drop-down window
        """

        dispute_category_cell = WebDriverWait(self.driver, 10).until(
            ec.element_to_be_clickable((By.CSS_SELECTOR,
                                        "input[type='text'][placeholder='категория спора']")))
        return dispute_category_cell

    def find_drop_down_list_arrows(self):
        """
        Searching for the drop-down list arrow
        """
        arrows_list = self.driver.find_elements(
            By.CSS_SELECTOR,
            "span[class='down-button js-down-button']")
        return arrows_list

    def find_from_drop_down_list(self, query):
        """
        Choosing category from the drop down list
        """
        list_elements = self.driver.find_elements(By.TAG_NAME, "li")
        for el in list_elements:
            if el.text == query:
                return el
        return None

    def find_next_page_button(self):
        """
        Search for the next page button
        """
        list_elements = self.driver.find_elements(By.TAG_NAME, "a")
        for next_button_candidate in list_elements:
            if next_button_candidate.text == "Ctrl→":
                return next_button_candidate
        return None

    def find_page_button(self, page_number):
        """
        Search for concrete page button
        """
        page_button = WebDriverWait(self.driver, 10).until(
            ec.element_to_be_clickable((By.CSS_SELECTOR, f"a[href='#page{page_number}']"))
        )
        return page_button

    def find_close_button(self):
        """
        Finding the button to go back to the list of documents
        :return: close_button
        """
        close_button = WebDriverWait(self.driver, 10).until(
            ec.element_to_be_clickable((By.CSS_SELECTOR, "span[class='close']"))
        )
        return close_button

    def find_info_on_docs(self):
        """Extracting courts and dates info of docs on some dispute category page"""
        elements = self.driver.find_elements(
            By.CSS_SELECTOR, "div[class='doc']"
        )
        doc_courts = []
        doc_dates = []
        for el in elements:
            court_plus_date = el.find_element(By.CSS_SELECTOR, "h2[class='info']")
            court = court_plus_date.find_element(By.CSS_SELECTOR, "span[class='court']").text
            date = court_plus_date.find_element(By.CSS_SELECTOR, "span[class='date']").text
            doc_courts.append(court)
            doc_dates.append(date)

        return doc_courts, doc_dates

    def find_links_to_docs(self):
        """Extracting links to docs on some dispute category page"""
        elements = self.driver.find_elements(
            By.CSS_SELECTOR, "div[class='doc-text']"
        )
        doc_links = []
        for el in elements:
            doc_links.append(el.find_element(By.TAG_NAME, 'a'))

        return doc_links

    def extract_text_from_doc(self):
        text = self.driver.find_element(By.CSS_SELECTOR, "div[class='text']").text
        return text

    def find_number_of_docs(self):
        """Extracting overall number of docs for some dispute category"""
        text = self.driver.find_element(By.CSS_SELECTOR, "span[class='b-found']").text  # Найдено х документов
        if len(text.split()) != 3:  # ["Найдено", "x", "документов"]
            return 0
        n = int(text.split()[1])
        return n

    def click_button(self, button):
        """Wrapper function for selenium button.click() to catch 429 error"""
        try:
            button.click()
        except ElementClickInterceptedException:
            print('Click ElementClickInterceptedException')
            self.url_is_running = False
            return

        if self.catch_429_error():
            print('Click 429')
            if self.vpn_is_running:
                action = 'stop'
                print('Stopping VPN')
            else:
                action = 'start'
                print('Starting VPN')

            subprocess.call(["scutil", "--nc", action, "Kaspersky VPN"])

            print('Sleeping')
            for _ in tqdm(range(60)):
                time.sleep(1)
            self.url_is_running = False
        elif self.catch_unable_to_load():
            print('Click Unable Loading')
            self.url_is_running = False

    def open_new_window(self):
        """Open up new window and close the old banned one"""
        self.driver.execute_script("window.open('');")
        new_window = self.driver.window_handles[-1]
        self.driver.switch_to.window(new_window)  # switching to the new window

    def close_old_window(self):
        old_window, new_window = self.driver.window_handles
        self.driver.switch_to.window(old_window)
        self.driver.close()
        self.driver.switch_to.window(new_window)

    # def find_captcha_button(self):
    #     try:
    #         captcha_button = self.driver.find_element(By.CSS_SELECTOR,
    #     "a[href='#'][class='b-pravocaptcha-close js-pravocaptcha-close']"
    #         )
    #         return captcha_button
    #     except selenium.common.exceptions.NoSuchElementException:
    #         return None

