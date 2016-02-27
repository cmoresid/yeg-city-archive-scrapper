from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from io import BytesIO

import time
import logging
import pickle
import unicodecsv as csv
import argparse

label_mappings = {
    'Image Number': 'image_number',
    'Fonds Title': 'fonds_title',
    'Image Title': 'image_title',
    'Dates of Creation': 'creation_date',
    'Description': 'description',
    'Photographer/Creator': 'creator',
    'Subjects': 'subjects',
    'Names': 'names',
    'Source of Title': 'src_title',
    'Database Type': 'db_type'
}

archive_url = "https://archivesphotos.edmonton.ca/Presto/search/SearchResults.aspx?q=KFN0cmVldCBBdmVudWUp&qcf=YTA5ZDY0NTMtYTg5Ni00MGJjLTgxYWEtYWI4MmYzMTJmZDIx"


def create_new_entry():
    """

    :return:
    """
    return dict(image_number='', fonds_title='', image_title='', creation_date='', description='', creator='',
                subjects='', names='', image_url='', src_title='', db_type='')


def create_logger():
    """

    :return:
    """
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    fh = logging.FileHandler('crawler.log')
    fh.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.ERROR)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    ch.setFormatter(formatter)

    logger.addHandler(fh)
    logger.addHandler(ch)

    return logger


def dump_current_crawler_state(current_crawler, log):
    """

    :param current_crawler:
    :param log:
    :return:
    """
    current_entries = current_crawler.get_entries()

    if len(current_entries) > 0:
        log.debug('Writing %d entries to entries.p' % (len(current_entries),))

        pickle.dump(crawler.get_checkpoint(), open('checkpoint.p', 'wb'))
        pickle.dump(current_entries, open('entries.p', 'wb'))


class CrawlerException(Exception):
    """

    """
    pass


class Crawler:
    """

    """
    def __init__(self, logger):
        """

        :param logger:
        :return:
        """
        self.browser = webdriver.Firefox()
        self.entries = []
        self.current_page = 1
        self.current_item = 0
        self.logger = logger

        self.browser.get(archive_url)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.browser.quit()

    def write_results(self):
        with open('yeg_city_archive.csv', 'w') as csvfile:
            fields = label_mappings.values()
            fields.append('image_url')

            f = BytesIO()
            csv_writer = csv.DictWriter(f, fieldnames=fields)

            csv_writer.writeheader()

            for entry in self.entries:
                csv_writer.writerow(entry)

            csvfile.write(f.getvalue())

    def get_entries(self):
        """

        :return:
        """
        return self.entries

    def set_entries(self, e):
        """

        :param e:
        :return:
        """
        self.entries = e

    def get_checkpoint(self):
        """

        :return:
        """
        return dict(page=self.current_page, item=self.current_item)

    def crawl(self, start_page=None, start_item=None):
        """

        :param start_page:
        :param start_item:
        :return:
        """
        if start_page is not None:
            self.__move_to_page(start_page)

        try:
            wait = WebDriverWait(self.browser, 10)
            next_button = wait.until(EC.presence_of_element_located((By.XPATH, "//button[@title='Next Page']")))
        except TimeoutException as e:
            self.logger.error('Unable to find next button on page', exc_info=True)
            raise CrawlerException(dict(error='Unable to find next button on page', page_number=self.current_page))

        while next_button.get_attribute('aria-disabled') != u'true':
            self.logger.info('Begin scrapping page %d' % (self.current_page,))
            time.sleep(5)

            search_results = self.browser.find_elements_by_xpath("//td[contains(@id, 'data-container')]")
            self.logger.debug('Found %d items on page' % (len(search_results),))

            if start_item is not None:
                search_results = search_results[start_item:]

            for i, result in enumerate(search_results):
                self.current_item = i
                self.logger.debug('Scrapping Page %d, Item %d' % (self.current_page, self.current_item))

                result_details_link = result.find_element_by_tag_name('a').get_attribute('href')

                self.__open_link_in_new_tab(result_details_link)

                # Add entry to entries
                entry_or_none = self.__scrape_result()

                if entry_or_none is not None:
                    self.entries.append(entry_or_none)

                # Close current tab and go back to search results
                self.__close_current_tab()

            # Move to the next page now
            time.sleep(2)
            next_button.click()
            time.sleep(5)

            next_button = self.browser.find_element_by_xpath("//button[@title='Next Page']")

            self.current_page += 1

        return self.entries

    def __open_link_in_new_tab(self, result_details_link):
        self.browser.find_element_by_tag_name('body').send_keys(Keys.COMMAND + 't')
        self.browser.get(result_details_link)

    def __close_current_tab(self):
        self.browser.find_element_by_tag_name('body').send_keys(Keys.COMMAND + 'w')
        self.browser.switch_to_window(self.browser.window_handles[0])

    def __move_to_page(self, start_page):
        time.sleep(5)

        while self.current_page <= start_page:
            next_button = self.browser.find_element_by_xpath("//button[@title='Next Page']")
            next_button.click()

            self.current_page += 1

    def __scrape_result(self):
        entry = create_new_entry()

        try:
            wait = WebDriverWait(self.browser, 10)
            img_tag = wait.until(EC.presence_of_element_located((By.XPATH, "//img[contains(@src, 'GetImage.axd')]")))
        except TimeoutException as ex:
            self.logger.error('Unable to corresponding image for item %d on page %d' %
                              (self.current_item, self.current_page), exc_info=True)
            return None

        rows = self.browser.find_elements_by_xpath("//table[../@id = 'divFocalScroll']/tbody/tr")
        rows = rows[1:]

        for row in rows:
            columns = row.find_elements_by_xpath('./td')

            row_label = columns[0].text.strip()
            row_value = columns[1].text.strip()

            try:
                entry[label_mappings[row_label]] = entry[label_mappings[row_label]] + ", " + row_value
            except KeyError:
                self.logger.error('Unable to find key in label_mappings: %s. item %d, page %d' % (row_label, item_index, self.current_page))

        for (key, value) in entry.iteritems():
            if len(value) > 0:
                entry[key] = value[2:]

        if img_tag is not None:
            entry['image_url'] = img_tag.get_attribute('src')

        return entry


if __name__ == "__main__":
    crawler_logger = create_logger()

    parser = argparse.ArgumentParser(description="Crawl the City of Edmonton Archive photo library.")
    parser.add_argument("-r", "--restart", help="restart where crawler stopped.",
                        action="store_true")
    args = parser.parse_args()

    if args.restart:
        checkpoint = pickle.load(open('checkpoint.p', 'rb'))
        entries = pickle.load(open('entries.p', 'rb'))

    try:
        with Crawler(crawler_logger) as crawler:
            if args.restart:
                crawler.set_entries(entries)
                crawler.crawl(checkpoint['page'], checkpoint['item'])
            else:
                crawler.crawl()

            crawler.write_results()

    except CrawlerException as ex:
        crawler_logger.error('A crawler exception as occurred', exc_info=True)
        dump_current_crawler_state(crawler, crawler_logger)
    except Exception as ex:
        crawler_logger.error('An exception as occurred', exc_info=True)
        dump_current_crawler_state(crawler, crawler_logger)
