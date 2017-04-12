# Apartments.com Scraper

Note: you can use this to create a CSV to (eventually, when I finish the code) import into the Compare App ([ideal-engine](https://github.com/adinutzyc21/ideal-engine), instance running [here](ideal-engine.herokuapp.com)).

In particular, this parses an [apartments.com](apartments.com) search result based on some criteria that are present in the page. This is current as of April 11, 2017.

It's a web scraper for the result listing and produces a CSV that has all the entries nicely parsed. 

These are the criteria I'm using:
`'Option Name', 'URL', 'Contact', 'Address', 'Distance', 'Duration', 'Map', 'Pet Policy', 'Parking', 'Gym', 'Kitchen', 'Amenities', 'Features', 'Living Space', 'Rent', 'Monthly Fees', 'One Time Fees', 'Lease Info', 'Services', 'Property Info', 'Indoor Info', 'Outdoor Info'` and they come from the entries that apartments.com shows on the page as well as from the Google Maps API (given an address to commute to, I am getting the approximate transit distance and time).

### How to use:

Please note that this assumes you have python installed. I am using Python 2.7 but it should work with Python 3+ too.
You can install Python from [here](https://www.python.org/downloads/). 
You also need to install beautifulsoup4 from [here](https://www.crummy.com/software/BeautifulSoup/bs4/doc/) and you'll probably need `pip` to do that (`python -m pip install beautifulsoup4` on Windows should do it).

In order to generate the CSV file:

1. Rename config_example.ini to config.ini.
2. Search for apartments on apartments.com. Use your own criteria using the app. Copy the URL.
    - Replace the parenthesis after "fullURL:" in config.ini with the copied URL.
3. Get an API key from [Google Maps API](https://developers.google.com/maps/documentation/distance-matrix/get-api-key) (this is for calculating distances / times using Google Maps).
    - Replace the parenthesis after "mapsAPIKey:" in config.ini with the key.
4. Search for the address you want to commute to on [Google Maps](https://www.google.com/maps). Copy the Google formatted address. For example, for the Empire State building, that address looks like "350 5th Ave New York, NY 10118".
    - Replace the parenthesis after "targetAddress:" in config.ini with the copied address.
5. If you want your output file to be named something output.csv, change the name of the file (output) after "fname:" in config.ini.
7. If you want, change the morning and evening commute time. The morning one is the time you want to arrive at destination and the evening one is the time you want to leave. The Google API search is for tomorrow at these times. You can replace these times but keep the format HH:mm AM / PM
6. Run `python parse_apartments.py` to generate the CSV file that you can then import.

You can then import that CSV file into the compareApp.
