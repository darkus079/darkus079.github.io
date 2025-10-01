#!/usr/bin/env python3

"""
This script is used to utilize kad.arbitr parser from AutoKad
"""

from autoKad import AutoKad
import json
from tqdm import tqdm

N_DOCS_PER_PAGE = 25  # page configuration

N_DOCS_PER_CAT = 100  # number of documents to collect per one dispute category


def __open(file_name):
    with open(f'{file_name}.json', 'r') as f:
        return json.load(f)


# opening data (create this files using mentioned above data structures if not available)
data = __open('data')  # data = {disp_cat : [list of collected documents]}
links_dict = __open('links_collected')  # links_dict is list of collected document urls
pages_dict = __open('pages_collected')  # pages_dict = {disp_cat : [list of collected page numbers]}
n_docs_dict = __open('n_docs')  # n_docs_dict = {disp_cat : int}, int is # of documents available on kad.arbitr
# n_docs_dict should be parsed separately if needed
dispute_categories = __open('dispute_categories')  # list of dispute_categories

ak = AutoKad()


def parse(disp_cat):
    """
    Parses specific dispute category using AutoKad
    """

    n_collected = len(set(links_dict[disp_cat]))
    N_DOCS_PER_CAT_local = N_DOCS_PER_CAT - n_collected
    if N_DOCS_PER_CAT_local < 0:
        # continue
        return

    max_pages = (
            n_docs_dict[disp_cat] // N_DOCS_PER_PAGE +
            int((n_docs_dict[disp_cat] % N_DOCS_PER_PAGE) != 0)
    )

    available_pages = [i for i in range(1, max_pages + 1) if i not in pages_dict[disp_cat]]

    n_pages_required = (
            N_DOCS_PER_CAT_local // N_DOCS_PER_PAGE +
            int((N_DOCS_PER_CAT_local % N_DOCS_PER_PAGE) != 0)
    )

    n_pages = min(n_pages_required, len(available_pages))

    if n_pages == 0:
        # continue
        return

    pages = available_pages[:n_pages]

    ak.sleep(2)
    ak.open_category_page(disp_cat)
    ak.sleep(2)
    if not ak.url_is_running:
        ak.driver.close()
        ak.driver = ak.start_driver()
        ak.start_url_routine()
        return parse(disp_cat)

    # ak.sleep()
    for page_id in pages:
        if page_id != 1:
            page_button = ak.find_page_button(page_id)
            ak.click_button(page_button)
            if not ak.url_is_running:
                ak.driver.close()
                ak.driver = ak.start_driver()
                ak.start_url_routine()
                return parse(disp_cat)
            # ak.sleep()

        doc_links = ak.find_links_to_docs()
        doc_courts, doc_dates = ak.find_info_on_docs()
        for i in range(len(doc_links)):
            link, court, date = doc_links[i], doc_courts[i], doc_dates[i]
            link_href = link.get_property('href')
            if link_href in links_dict[disp_cat]:
                continue

            ak.click_button(link)
            if not ak.url_is_running:
                ak.driver.close()
                ak.driver = ak.start_driver()
                ak.start_url_routine()
                return parse(disp_cat)
            # ak.sleep(timeout)
            text = ak.extract_text_from_doc()
            close_button = ak.find_close_button()

            ak.click_button(close_button)
            if not ak.url_is_running:
                ak.driver.close()
                ak.driver = ak.start_driver()
                ak.start_url_routine()
                return parse(disp_cat)
            # ak.sleep(timeout)

            data[disp_cat].append((date, court, text))

            if link_href not in links_dict[disp_cat]:
                links_dict[disp_cat].append(link_href)

            # with open('data.json', 'w') as f:
            #     json.dump(data, f, indent='\t', ensure_ascii=False)
            # with open('links_collected.json', 'w') as f:
            #     json.dump(links_dict, f, indent='\t', ensure_ascii=False)

        if page_id not in pages_dict[disp_cat]:
            pages_dict[disp_cat].append(page_id)
        # with open('pages_collected.json', 'w') as f:
        #     json.dump(pages_dict, f, indent='\t', ensure_ascii=False)
    save_files()


def save_files():
    with open('pages_collected.json', 'w') as f:
        json.dump(pages_dict, f, indent='\t', ensure_ascii=False)

    with open('data.json', 'w') as f:
        json.dump(data, f, indent='\t', ensure_ascii=False)

    with open('links_collected.json', 'w') as f:
        json.dump(links_dict, f, indent='\t', ensure_ascii=False)


if __name__ == '__main__':
    # example of usage (categories may be processed in a loop of course)
    parse(dispute_categories[235])
    save_files()
