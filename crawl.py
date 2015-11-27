from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
import time
import unicodecsv as csv
from io import BytesIO

browser = webdriver.Firefox()
browser.get("https://archivesphotos.edmonton.ca/Presto/search/SearchResults.aspx?q=KFN0cmVldCBBdmVudWUp&qcf=YTA5ZDY0NTMtYTg5Ni00MGJjLTgxYWEtYWI4MmYzMTJmZDIx")

time.sleep(15)
entries = []

page_count = 1

label_mappings = {
    'Image Number:' : 'image_number',
    'Fonds Title' : 'fonds_title',
    'Image Title:' : 'image_title',
    'Dates of Creation:' : 'creation_date',
    'Description' : 'description',
    'Photographer / Creator:' : 'creator',
    'Subjects:' : 'subjects',
    'Names' : 'names'
}

while browser.find_element_by_xpath("//button[@title='Next Page']").get_attribute('aria-disabled') != u'true':
    print 'Scrapping page %s ...' % (page_count,)

    search_results = browser.find_elements_by_xpath("//td[contains(@id, 'data-container')]")
    
    for result in search_results:
        meta_data = result.text
        meta_data_split = meta_data.split("\n")

        img_tag = None

        try:
            img_tag = result.find_element_by_tag_name('img')
        except NoSuchElementException:
            print 'Unable to find img...'
        
        entry = {
            'image_number': '',
            'fonds_title': '',
            'image_title': '',
            'creation_date': '',
            'description': '',
            'creator': '',
            'subjects': '',
            'names': '',
            'image_url': ''
        }

        for potential_label in label_mappings.keys():
            for meta_data in meta_data_split:
                index = meta_data.find(potential_label)

                if index != -1:
                    entry[label_mappings[potential_label]] = meta_data[len(potential_label):].strip()

        if img_tag != None:
            entry['image_url'] = img_tag.get_attribute('src')

        entries.append(entry)

    # Remember to click the next button
    browser.find_element_by_xpath("//button[@title='Next Page']").click()
    time.sleep(5)
    page_count = page_count + 1

browser.quit()

with open('yeg_city_archive.csv', 'w') as csvfile:
    fields = label_mappings.values()
    fields.append('image_url')

    f = BytesIO()
    csv_writer = DictWriter(f, fieldnames=fields)

    csv_writer.writeheader()

    for entry in entries:
        csv_writer.writerow(entry)

    csvfile.write(f.getvalue())
