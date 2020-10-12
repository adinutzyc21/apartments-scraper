"""Parse an apartments.com search result page and export to CSV."""
import csv
import json
import re
import sys
import datetime
import requests
import os
import time
import platform
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.firefox.options import Options

# Config parser was renamed in Python 3
try:
    import configparser
except ImportError:
    import ConfigParser as configparser

def create_csv(search_urls, map_info, fname, pscores):
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
        header = ['Option Name', 'Contact', 'Address', 'Size',
                  'Rent', 'Monthly Fees', 'One Time Fees',
                  'Pet Policy', 'Distance', 'Duration',
                  'Parking', 'Gym', 'Kitchen',
                  'Amenities', 'Features', 'Living Space',
                  'Lease Info', 'Services',
                  'Property Info', 'Indoor Info', 'Outdoor Info',
                  'Images', 'Description']
        # add the score fields if necessary
        if pscores:
            for i in xrange(len(header), 0, -1):
                header.insert(i, 5)
            # flag that we're importing with scores
            header[1] = 'score'
            header.append('modifier')
        # write the header
        writer.writerow(header)

        # parse current entire apartment list including pagination for all search urls
        for url in search_urls:
            print ("Now getting apartments from: %s" % url)
            write_parsed_to_csv(url, map_info, writer, pscores)

    finally:
        csv_file.close()


def write_parsed_to_csv(page_url, map_info, writer, pscores, page_number = 2, web_driver = None):
    """Given the current page URL, extract the information from each apartment in the list"""

    # We start on page_number = 2, since we will already be parsing page_number 1

    # if we are loading the page for the first time, we want to initailize the web driver
    if(web_driver != None):
        driver = web_driver
    else:
        options = Options()
        options.headless = True
        if ('debian' in platform.platform()):
            driver = webdriver.Firefox(firefox_binary='/usr/bin/firefox-esr', options=options)
        else:
            driver = webdriver.Firefox(options=options)
        driver.get(page_url)

    # read the current page
    soup = BeautifulSoup(driver.page_source, 'html.parser')
 
    # soupify the current page
    soup.prettify()
    # only look in this region
    soup = soup.find('div', class_='placardContainer')

    # append the current apartments to the list
    for item in soup.find_all('article', class_='placard'):
        url = ''
        rent = ''
        contact = ''

        if item.find('a', class_='placardTitle') is None: continue
        url = item.find('a', class_='placardTitle').get('href')

        # get the rent and parse it to unicode
        obj = item.find('span', class_='altRentDisplay')
        if obj is not None:
            rent = obj.getText().strip()

        # get the phone number and parse it to unicode
        obj = item.find('div', class_='phone')
        if obj is not None:
            contact = obj.getText().strip()

        # get the other fields to write to the CSV
        fields = parse_apartment_information(url, map_info)

        # make this wiki markup
        fields['name'] = '[' + str(fields['name']) + '](' + url + ')'
        fields['address'] = '[' + fields['address'] + '](' + fields['map'] + ')'

        # fill out the CSV file
        row = [fields['name'], contact,
               fields['address'], fields['size'],
               rent, fields['monthFees'], fields['onceFees'],
               fields['petPolicy'], fields['distance'], fields['duration'],
               fields['parking'], fields['gym'], fields['kitchen'],
               fields['amenities'], fields['features'], fields['space'],
               fields['lease'], fields['services'],
               fields['info'], fields['indoor'], fields['outdoor'],
               fields['img'], fields['description']]
        # add the score fields if necessary
        if pscores:
            for i in xrange(len(row), 0, -1):
                row.insert(i, '5')
            row.append('0')
        # write the row
        writer.writerow(row)

    page_number_str = str(page_number)
    
    # check for our next page number
    try:
        page_number_element = driver.find_element_by_xpath("//a[@data-page='" + page_number_str + "']")
        page_number_element.click()
        time.sleep(1)
    # we will get a no element found exception, meaning our search has come to an end
    except:
        driver.quit()
        return

    # recurse until the last page
    write_parsed_to_csv("none", map_info, writer, pscores, page_number + 1, driver)


def parse_apartment_information(url, map_info):
    """For every apartment page, populate the required fields to be written to CSV"""

    # read the current page
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'}
    page = requests.get(url, headers=headers)

    # soupify the current page
    soup = BeautifulSoup(page.content, 'html.parser')
    soup.prettify()

    # the information we need to return as a dict
    fields = {}

    # get the name of the property
    get_property_name(soup, fields)

    # get the address of the property
    get_property_address(soup, fields)

    # get the size of the property
    get_property_size(soup, fields)

    # get the one time and monthly fees
    get_fees(soup, fields)

    # get the images as a list
    get_images(soup, fields)

    # get the description section
    get_description(soup, fields)

    # only look in this section (other sections are for example for printing)
    soup = soup.find('section', class_='specGroup js-specGroup')

    # get the pet policy of the property
    get_pet_policy(soup, fields)

    # get parking information
    get_parking_info(soup, fields)

    # get the amenities description
    get_field_based_on_class(soup, 'amenities', 'featuresIcon', fields)

    # get the 'interior information'
    get_field_based_on_class(soup, 'indoor', 'interiorIcon', fields)

    # get the 'outdoor information'
    get_field_based_on_class(soup, 'outdoor', 'parksIcon', fields)

    # get the 'gym information'
    get_field_based_on_class(soup, 'gym', 'fitnessIcon', fields)

    # get the 'kitchen information'
    get_field_based_on_class(soup, 'kitchen', 'kitchenIcon', fields)

    # get the 'services information'
    get_field_based_on_class(soup, 'services', 'servicesIcon', fields)

    # get the 'living space information'
    get_field_based_on_class(soup, 'space', 'sofaIcon', fields)

    # get the lease length
    get_field_based_on_class(soup, 'lease', 'leaseIcon', fields)

    # get the 'property information'
    get_features_and_info(soup, fields)

    # get the link to open in maps
    fields['map'] = 'https://www.google.com/maps/dir/' \
                    + map_info['target_address'].replace(' ', '+') + '/' \
                    + fields['address'].replace(' ', '+') + '/data=!4m2!4m1!3e2'

    fields['distance'] = ''
    fields['duration'] = ''
    if map_info['use_google_maps']:
        # get the distance and duration to the target address using the Google API
        get_distance_duration(map_info, fields)

    return fields

def prettify_text(data):
    """Given a string, replace unicode chars and make it prettier"""

    # format it nicely: replace multiple spaces with just one
    data = re.sub(' +', ' ', data)
    # format it nicely: replace multiple new lines with just one
    data = re.sub('(\r?\n *)+', '\n', data)
    # format it nicely: replace bullet with *
    data = re.sub(u'\u2022', '* ', data)
    # format it nicely: replace registered symbol with (R)
    data = re.sub(u'\xae', ' (R) ', data)
    # format it nicely: remove trailing spaces
    data = data.strip()
    # format it nicely: encode it, removing special symbols
    data = data.encode('utf8', 'ignore')

    return str(data).encode('utf-8')


def get_images(soup, fields):
    """Get the images of the apartment"""

    fields['img'] = ''

    if soup is None: return

    # find ul with id fullCarouselCollection
    soup = soup.find('ul', {'id': 'fullCarouselCollection'})
    if soup is not None:
        for img in soup.find_all('img'):
            fields['img'] += '![' + img['alt'] + '](' + img['src'] + ') '

def get_description(soup, fields):
    """Get the description for the apartment"""

    fields['description'] = ''

    if soup is None: return

    # find p with itemprop description
    obj = soup.find('p', {'itemprop': 'description'})

    if obj is not None:
        fields['description'] = prettify_text(obj.getText())

def get_property_size(soup, fields):
    """Given a beautifulSoup parsed page, extract the property size of the first one bedroom"""
    #note: this might be wrong if there are multiple matches!!!

    fields['size'] = ''

    if soup is None: return
    
    obj = soup.find('tr', {'data-beds': '1'})
    if obj is not None:
        data = obj.find('td', class_='sqft').getText()
        data = prettify_text(data)
        fields['size'] = data


def get_features_and_info(soup, fields):
    """Given a beautifulSoup parsed page, extract the features and property information"""

    fields['features'] = ''
    fields['info'] = ''

    if soup is None: return
    
    obj = soup.find('i', class_='propertyIcon')

    if obj is not None:
        for obj in soup.find_all('i', class_='propertyIcon'):
            data = obj.parent.findNext('ul').getText()
            data = prettify_text(data)

            if obj.parent.findNext('h3').getText().strip() == 'Features':
                # format it nicely: remove trailing spaces
                fields['features'] = data
            if obj.parent.findNext('h3').getText() == 'Property Information':
                # format it nicely: remove trailing spaces
                fields['info'] = data


def get_field_based_on_class(soup, field, icon, fields):
    """Given a beautifulSoup parsed page, extract the specified field based on the icon"""

    fields[field] = ''

    if soup is None: return
    
    obj = soup.find('i', class_=icon)
    if obj is not None:
        data = obj.parent.findNext('ul').getText()
        data = prettify_text(data)

        fields[field] = data


def get_parking_info(soup, fields):
    """Given a beautifulSoup parsed page, extract the parking details"""

    fields['parking'] = ''

    if soup is None: return
    
    obj = soup.find('div', class_='parkingDetails')
    if obj is not None:
        data = obj.getText()
        data = prettify_text(data)

        # format it nicely: remove trailing spaces
        fields['parking'] = data


def get_pet_policy(soup, fields):
    """Given a beautifulSoup parsed page, extract the pet policy details"""
    if soup is None:
        fields['petPolicy'] = ''
        return
    
    # the pet policy
    data = soup.find('div', class_='petPolicyDetails')
    if data is None:
        data = ''
    else:
        data = data.getText()
        data = prettify_text(data)

    # format it nicely: remove the trailing whitespace
    fields['petPolicy'] = data


def get_fees(soup, fields):
    """Given a beautifulSoup parsed page, extract the one time and monthly fees"""

    fields['monthFees'] = ''
    fields['onceFees'] = ''

    if soup is None: return

    obj = soup.find('div', class_='monthlyFees')
    if obj is not None:
        for expense in obj.find_all('div', class_='fee'):
            description = expense.find(
                'div', class_='descriptionWrapper').getText()
            description = prettify_text(description)

            price = expense.find('div', class_='priceWrapper').getText()
            price = prettify_text(price)

            fields['monthFees'] += '* ' + description + ': ' + price + '\n'

    # get one time fees
    obj = soup.find('div', class_='oneTimeFees')
    if obj is not None:
        for expense in obj.find_all('div', class_='fee'):
            description = expense.find(
                'div', class_='descriptionWrapper').getText()
            description = prettify_text(description)

            price = expense.find('div', class_='priceWrapper').getText()
            price = prettify_text(price)

            fields['onceFees'] += '* ' + description + ': ' + price + '\n'

    # remove ending \n
    fields['monthFees'] = fields['monthFees'].strip()
    fields['onceFees'] = fields['onceFees'].strip()


def get_distance_duration(map_info, fields):
    """Use google API to return the distance and time to the target address"""

    fields['distance'] = ''
    fields['duration'] = ''

    # get the distance and the time from google
    # getting to work in the morning
    origin = map_info['target_address'].replace(' ', '+')
    destination = fields['address'].replace(' ', '+')
    map_url = map_info['maps_url'] + '&origins=' + origin + '&destinations=' + \
        destination + '&arrival_time=' + map_info['morning']

    # populate the distance / duration fields for morning
    travel_morning = get_travel_time(map_url)
    
    # coming back from work in the evening
    origin = fields['address'].replace(' ', '+')
    destination = map_info['target_address'].replace(' ', '+')
    map_url = map_info['maps_url'] + '&origins=' + origin + '&destinations=' + \
        destination + '&departure_time=' + map_info['evening']

    # populate the distance / duration fields for evening
    travel_evening = get_travel_time(map_url)

    # take the average
    fields['distance'] = average_field(travel_morning, travel_evening, 'distance')
    fields['duration'] = average_field(travel_morning, travel_evening, 'duration')

def average_field(obj1, obj2, field):
    """Take the average given two objects that have field values followed by (same) unit"""
    val1 = float(prettify_text(obj1[field]).split()[0])
    val2 = float(prettify_text(obj2[field]).split()[0])
    unit = ' ' + prettify_text(obj1[field]).split()[1]

    avg = 0.5 * (val1 + val2)
    if field == 'duration':
        avg = int(avg)

    return str(avg) + unit

def get_travel_time(map_url):
    """Get the travel distance & time from Google Maps distance matrix app given a URL"""

    # the travel info dict
    travel = {}

    # read and parse the google maps distance / duration from the api
    response = requests.get(map_url).json()
    
    # the status might not be OK, ignore this in that case
    if response['status'] == 'OK':
        response = response['rows'][0]['elements'][0]
        # extract the distance and duration
        if response['status'] == 'OK':
            # get the info
            travel['distance'] = response['distance']['text']
            travel['duration'] = response['duration']['text']

    # return the travel info
    return travel


def get_property_name(soup, fields):
    """Given a beautifulSoup parsed page, extract the name of the property"""
    fields['name'] = ''

    # get the name of the property
    obj = soup.find('h1', class_='propertyName')
    if obj is not None:
        name = obj.getText()
        name = prettify_text(name)
        fields['name'] = name

def find_addr(script, tag):
    """Given a script and a tag, use python find to find the text after tag"""

    tag = tag + ": \'"
    start = script.find(tag)+len(tag)
    end = script.find("\',", start)
    return script[start : end]

def get_property_address(soup, fields):
    """Given a beautifulSoup parsed page, extract the full address of the property"""

    address = ""

    # They changed how this works so I need to grab the script
    script = soup.findAll('script', type='text/javascript')[2].text
    
    # The address is everything in quotes after listingAddress
    address = find_addr(script, "listingAddress")

    # City
    address += ", " + find_addr(script, "listingCity")

    # State
    address += ", " + find_addr(script, "listingState")

    # Zip Code
    address += " " + find_addr(script, "listingZip")

    fields['address'] = address


def parse_config_times(given_time):
    """Convert the tomorrow at given_time New York time to seconds since epoch"""

    # tomorrow's date
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    # tomorrow's date/time string based on time given
    date_string = str(tomorrow) + ' ' + given_time
    # tomorrow's datetime object
    format_ = '%Y-%m-%d %I:%M %p'
    date_time = datetime.datetime.strptime(date_string, format_)

    # the epoch
    epoch = datetime.datetime.utcfromtimestamp(0)

    # return time since epoch in seconds, string without decimals
    time_since_epoch = (date_time - epoch).total_seconds()
    return str(int(time_since_epoch))

def main():
    """Read from the config file and get the Google maps info optionally"""

    conf = configparser.ConfigParser()
    config_file = os.path.join(os.path.dirname(__file__), "config.ini")
    conf.read(config_file)

    # get the apartments.com search URL(s)
    apartments_url_config = conf.get('all', 'apartmentsURL')
    urls = apartments_url_config.replace(" ", "").split(",")

    # get the name of the output file
    fname = conf.get('all', 'fname') + '.csv'

    # should this also print the scores
    pscores = (conf.get('all', 'printScores') in ['T', 't', '1', 'True', 'true'])

    # create a dict to pass in all of the Google Maps info to have fewer params
    map_info = {}

    # get the target address for Maps URL / calculations
    map_info['target_address'] = conf.get('all', 'targetAddress')

    # get the Google Maps information

    # should use Google Maps? 
    # maybe not since you have to provide credit card info, the URL will still work
    map_info['use_google_maps'] = conf.get('all', 'useGoogleMaps') in ['T', 't', '1', 'True', 'true']

    if map_info['use_google_maps']:
        # get the URL to Google Maps
        map_info['maps_url'] = conf.get('all', 'mapsURL')
        # get the times for going to / coming back from work
        # and convert these to seconds since epoch, EST tomorrow
        map_info['morning'] = parse_config_times(conf.get('all', 'morning'))
        map_info['evening'] = parse_config_times(conf.get('all', 'evening'))
        # create the maps URL
        units = conf.get('all', 'mapsUnits')
        mode = conf.get('all', 'mapsMode')
        routing = conf.get('all', 'mapsTransitRouting')
        google_api_key = conf.get('all', 'mapsAPIKey')
        map_info['maps_url'] += 'units=' + units + '&mode=' + mode + \
            '&transit_routing_preference=' + routing + '&key=' + google_api_key

    create_csv(urls, map_info, fname, pscores)


if __name__ == '__main__':
    main()
