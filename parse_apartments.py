"""Parse an apartments.com search result page and export to CSV."""
import csv
import re
import sys
import datetime
import requests
import os
import platform
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
import urllib.parse
import configparser

def create_csv(base_url, urls, web_driver, fname):
    """Create a CSV file with information that can be imported into ideal-engine"""

    # avoid the issue on Windows where there's an extra space every other line
    if sys.version_info[0] == 2:  # Not named on 2.6
        access = 'wb'
        kwargs = {}
    else:
        access = 'wt'
        kwargs = {'newline': ''}
    # open file for writing
    csv_file = open(fname, access, **kwargs)

    # write to CSV
    try:
        writer = csv.writer(csv_file)
        # this is the header (make sure it matches with the fields in
        # write_parsed_to_csv)
        header = ['Title', 'Location', 'Size', 'Beds', 'Floor & Elevator', 'Parking', 'Price', 'Description', 'URL']
        
        # write the header
        writer.writerow(header)

        # parse current entire apartment list including pagination for all search urls
        for url in urls:
            print (f"Now getting apartments from: {url}")
            write_parsed_to_csv(base_url, url, web_driver, writer)

    finally:
        csv_file.close()

def write_parsed_to_csv(base_url, page_url, web_driver, writer, page_number = 2):
    """Given the current page URL, extract the information from each apartment in the list"""

    # We start on page_number = 2, since we will already be parsing page_number 1
    web_driver.get(page_url)

    # read the current page
    soup = BeautifulSoup(web_driver.page_source, 'html.parser')
 
    # soupify the current page
    soup.prettify()

    # append the current apartments to the list
    for item in soup.find_all('div', class_='item-info-container'):
        url = item.find('a', class_='item-link')
        if url is None: continue

        url = url.get('href')
        if url is None: continue

        url = urllib.parse.urljoin(base_url, url)

        # get the other fields to write to the CSV
        fields = parse_apartment_information(url, web_driver)

        # fill out the CSV file: ['Title', 'Location', 'Size', 'Beds', 'Floor & Elevator', 'Parking', 'Price', 'Description', 'URL']
        row = [fields['title'], fields['location'], fields['size'], fields['beds'],
                fields['floor-elev'], fields['parking'], fields['price'], fields['description'], url]
        # write the row
        writer.writerow(row)

    # page_number_str = str(page_number)
    
    # # check for our next page number
    # try:
    #     page_number_element = driver.find_element_by_xpath("//a[@data-page='" + page_number_str + "']")
    #     page_number_element.click()
    #     time.sleep(1)
    # # we will get a no element found exception, meaning our search has come to an end
    # except:
    #     driver.quit()
    #     return

    # # recurse until the last page
    # write_parsed_to_csv("none", writer, page_number + 1, driver)


def parse_apartment_information(url, web_driver):
    """
    For every apartment page, populate the required fields to be written to CSV
    'Title', 'Location', 'Size', 'Beds', 'Floor & Elevator', 'Parking', 'Price', 'Description', 'URL'
    """
    print(f"Parsing {url}")
    web_driver.get(url)

    # read the current page
    soup = BeautifulSoup(web_driver.page_source, 'html.parser')
 
    # soupify the current page
    soup.prettify()

    # the information we need to return as a dict
    fields = {}

    # get the name of the property
    fields['title'] = ''

    # get the name of the property
    obj = soup.find('h2', class_='txt-body')
    if obj is not None:
        fields['title']  = prettify_text(obj.getText())

    # get the location of the property
    locs = soup.find_all('li', class_='header-map-list')
    loc = ''
    if len(locs) == 1:
        loc = prettify_text(locs[0].getText()) 
    if len(locs) >= 2:
        locs = [prettify_text(locs[0].getText()), prettify_text(locs[1].getText())]
        loc =  ', '.join(filter(None, locs))
    fields['location'] = loc

    # get the size of the property (size, beds, floor & elevator, parking)
    fields['size'] = ''
    fields['beds'] = ''
    fields['floor-elev'] = ''
    fields['parking'] = ''
    obj = soup.find('div', class_='info-features')
    if obj is not None:
        features = obj.find_all("span")
        fields['size']  = prettify_text(features[0].getText())
        fields['beds']  = prettify_text(features[1].getText())
        fields['floor-elev']  = prettify_text(features[2].getText())
        if len(features) > 3:
            fields['parking']  = prettify_text(features[3].getText())

    # get the one time and monthly fees
    fields['price'] = ''
    obj = soup.find('strong', class_='price')
    if obj is not None:
        fields['price']  = prettify_text(obj.getText())

    # get the description section
    fields['description'] = ''
    obj = soup.find('div', class_='commentsContainer')
    if obj is not None:
        obj = obj.find('p')
        if obj is not None:
            fields['description'] = prettify_text(obj.getText())

    return fields

def prettify_text(data):
    """Given a string, replace unicode chars and make it prettier"""

    # format it nicely: replace multiple new lines with a space
    data = re.sub('(\r?\n *)+', ' ', data)
    # format it nicely: replace multiple spaces with just one
    data = re.sub(' +', ' ', data)
    # format it nicely: replace bullet with *
    data = re.sub(u'\u2022', '* ', data)
    # format it nicely: replace registered symbol with (R)
    data = re.sub(u'\xae', ' (R) ', data)
    # format it nicely: remove trailing spaces
    data = data.strip()
    # format it nicely: encode it, removing special symbols
    data = data.encode('utf8', 'ignore')

    return data.decode('utf8')


def main():
    """Read from the config file and get the Google maps info optionally"""

    conf = configparser.ConfigParser()
    config_file = os.path.join(os.path.dirname(__file__), "config.ini")
    conf.read(config_file)

    # get the apartments.com search URL
    base_url = conf.get('all', 'baseURL')
    # get the config data, can be multiple URLs separated by ,,,
    urls = conf.get('all', 'criteriaSuffixURL')
    # convert to a list
    urls = urls.replace(" ", "").split(",,,")
    # prepend the base url to get a fully formed url
    urls = [urllib.parse.urljoin(base_url, url) for url in urls]

    # get the name of the output file
    fname = conf.get('all', 'fname') + '.csv'

    options = Options()
    options.headless = True
    web_driver = webdriver.Firefox(options=options)

    create_csv(base_url, urls, web_driver, fname)


if __name__ == '__main__':
    main()
