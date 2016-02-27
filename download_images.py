import csv
import os
import os.path
import requests

CRAWLER_OUTPUT = 'data/yeg_city_archive.csv'
OUTPUT_DIRECTORY = 'data/imgs'

def download_image(record):
    print 'Downloading %s . . .' % (record['image_number'])

    try:
        img_request = requests.get(record['image_url'])

        with open(os.path.join(OUTPUT_DIRECTORY, record['image_number'] + '.jpeg'), 'wb') as img_file:
            img_file.write(img_request.content)
    except Exception:
        print '*** Unable to download file %s' % record['image_number']


def main():
    if not(os.path.isfile(CRAWLER_OUTPUT)):
        print 'Please run the crawler first before trying to download the images...'
        return

    with open(CRAWLER_OUTPUT, 'rb') as csvfile:
        archive_reader = csv.DictReader(csvfile)

        if not(os.path.exists(OUTPUT_DIRECTORY)):
            os.makedirs(OUTPUT_DIRECTORY)

        for record in archive_reader:
            download_image(record)

if __name__ == "__main__":
    main()
