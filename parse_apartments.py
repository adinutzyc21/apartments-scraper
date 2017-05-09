"""Parse an apartments.com search result page and export to CSV."""
import urllib2
import csv
import json
import ConfigParser
import re
import sys
import datetime
from bs4 import BeautifulSoup


def create_csv(page_url, map_info, fname, pscores):
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

        # parse current entire apartment list including pagination
        write_parsed_to_csv(page_url, map_info, writer, pscores)
    finally:
        csv_file.close()


def write_parsed_to_csv(page_url, map_info, writer, pscores):
    """Given the current page URL, extract the information from each apartment in the list"""

    # read the current page
    page = urllib2.urlopen(page_url).read()
    # soupify the current page
    soup = BeautifulSoup(page, 'html.parser')
    soup.prettify()

    # only look in this region
    soup = soup.find('div', class_='placardContainer')

    # append the current apartments to the list
    for item in soup.find_all('article', class_='placard'):
        url = ''
        rent = ''
        contact = ''

        # get the URL href
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
        fields['name'] = '[' + fields['name'] + '](' + url + ')'
        fields['address'] = '[' + fields['address'] + \
            '](' + fields['map'] + ')'

        # fill out the CSV file
        row = [fields['name'], contact,
               fields['address'], fields['size'],
               rent, fields['monthFees'], fields['onceFees'],
               fields['petPolicy'], fields['distance'], fields['duration'],
               fields['parking'], fields['gym'], fields['kitchen'],
               fields['amenities'], fields['features'], fields['space'],
               fields['lease'], fields['services'],
               fields['info'], fields['indoor'], fields['outdoor'],
               fields['img'], fields['desc']]
        # add the score fields if necessary
        if pscores:
            for i in xrange(len(row), 0, -1):
                row.insert(i, '5')
            row.append('0')
        # write the row
        writer.writerow(row)

    # get the next page URL for pagination
    next_url = soup.find('a', class_='next')
    # if there's only one page this will actually be none
    if next_url is None:
        return

    # get the actual next URL address
    next_url = next_url.get('href')

    # recurse until the last page
    if next_url is not None and next_url != 'javascript:void(0)':
        write_parsed_to_csv(next_url, map_info, writer, pscores)


def parse_apartment_information(url, map_info):
    """For every apartment page, populate the required fields to be written to CSV"""

    # read the current page
    page = urllib2.urlopen(url).read()

    # soupify the current page
    soup = BeautifulSoup(page, 'html.parser')
    soup.prettify()

    # the information we need to return as a dict
    fields = {}

    # get the name of the property
    get_property_name(soup, fields)

    # get the address of the property
    get_property_address(soup, fields)

    # get the size of the property
    get_property_size(soup, fields)

    # get the link to open in maps
    fields['map'] = 'https://www.google.com/maps/dir/' \
                    + map_info['target_address'].replace(' ', '+') \
                    + '/' + \
        fields['address'].replace(' ', '+') + '/data=!4m2!4m1!3e2'

    # get the distance and duration to the target address using the Google API
    get_distance_duration(map_info, fields)

    # get the one time and monthly fees
    get_fees(soup, fields)

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

    # get the images as a list

    # get the description section

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

    return data


def get_property_size(soup, fields):
    """Given a beautifulSoup parsed page, extract the property size of the first one bedroom"""
    #note: this might be wrong if there are multiple matches!!!

    fields['size'] = ''
    obj = soup.find('tr', {'data-beds': '1'})
    if obj is not None:
        data = obj.find('td', class_='sqft').getText()
        data = prettify_text(data)
        fields['size'] = data


def get_features_and_info(soup, fields):
    """Given a beautifulSoup parsed page, extract the features and property information"""

    fields['features'] = ''
    fields['info'] = ''
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
    obj = soup.find('i', class_=icon)
    if obj is not None:
        data = obj.parent.findNext('ul').getText()
        data = prettify_text(data)

        fields[field] = data


def get_parking_info(soup, fields):
    """Given a beautifulSoup parsed page, extract the parking details"""

    fields['parking'] = ''
    obj = soup.find('div', class_='parkingDetails')
    if obj is not None:
        data = obj.getText()
        data = prettify_text(data)

        # format it nicely: remove trailing spaces
        fields['parking'] = data


def get_pet_policy(soup, fields):
    """Given a beautifulSoup parsed page, extract the pet policy details"""

    # the pet policy
    data = soup.find('div', class_='petPolicyDetails').getText()
    data = prettify_text(data)

    # format it nicely: remove the trailing whitespace
    fields['petPolicy'] = data


def get_fees(soup, fields):
    """Given a beautifulSoup parsed page, extract the one time and monthly fees"""

    fields['monthFees'] = ''
    fields['onceFees'] = ''

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
    if(field == 'duration'):
        avg = int(avg)
    
    return str(avg) + unit

def get_travel_time(map_url):
    """Get the travel distance & time from Google Maps distance matrix app given a URL"""

    # the travel info dict
    travel = {}

    try:
        # read and parse the google maps distance / duration from the api
        search_response = urllib2.urlopen(map_url).read()

        # get the distance from google maps
        obj = json.loads(search_response)
        # the status might not be OK, ignore this in that case
        if obj['status'] == 'OK':
            obj = obj['rows'][0]['elements'][0]
            # extract the distance and duration
            if obj['status'] == 'OK':
                # get the info
                travel['distance'] = obj['distance']['text']
                travel['duration'] = obj['duration']['text']

    # ignore the errors, worst case they will be empty
    except (urllib2.HTTPError, urllib2.URLError):
        pass

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


def get_property_address(soup, fields):
    """Given a beautifulSoup parsed page, extract the full address of the property"""

    # create the address from parts connected by comma (except zip code)
    address = []

    # this can be either inside the tags or as a value for "content"
    obj = soup.find(itemprop='streetAddress')
    text = obj.get('content')
    if text is None:
        text = obj.getText()
    text = prettify_text(text)
    address.append(text)

    obj = soup.find(itemprop='addressLocality')
    text = obj.get('content')
    if text is None:
        text = obj.getText()
    text = prettify_text(text)
    address.append(text)

    obj = soup.find(itemprop='addressRegion')
    text = obj.get('content')
    if text is None:
        text = obj.getText()
    text = prettify_text(text)
    address.append(text)

    # join the addresses on comma before getting the zip
    address = ', '.join(address)

    obj = soup.find(itemprop='postalCode')
    text = obj.get('content')
    if text is None:
        text = obj.getText()
    text = prettify_text(text)
    # put the zip with a space before it
    address += ' ' + text

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
    """Read from the config file"""

    conf = ConfigParser.ConfigParser()
    conf.read('config.ini')

    # get the apartments.com search URL
    apartments_url = conf.get('all', 'apartmentsURL')

    # get the name of the output file
    fname = conf.get('all', 'fname') + '.csv'

    # should this also print the scores
    pscores = (conf.get('all', 'printScores') in [
               'T', 't', '1', 'True', 'true'])

    # create a dict to pass in all of the Google Maps info to have fewer params
    map_info = {}

    # get the Google Maps information
    map_info['maps_url'] = conf.get('all', 'mapsURL')
    units = conf.get('all', 'mapsUnits')
    mode = conf.get('all', 'mapsMode')
    routing = conf.get('all', 'mapsTransitRouting')
    api_key = conf.get('all', 'mapsAPIKey')
    map_info['target_address'] = conf.get('all', 'targetAddress')

    # get the times for going to / coming back from work
    # and convert these to seconds since epoch, EST tomorrow
    map_info['morning'] = parse_config_times(conf.get('all', 'morning'))
    map_info['evening'] = parse_config_times(conf.get('all', 'evening'))

    # create the maps URL so we don't pass all the parameters
    map_info['maps_url'] += 'units=' + units + '&mode=' + mode + \
        '&transit_routing_preference=' + routing + '&key=' + api_key

    create_csv(apartments_url, map_info, fname, pscores)


if __name__ == '__main__':
    main()
