# Apartments.com Scraper

Note: you can use this to create a CSV to (eventually, when I finish the code) import into the Compare App ([ideal-engine](https://github.com/adinutzyc21/ideal-engine), instance running [here](ideal-engine.herokuapp.com)).

In particular, this parses an [apartments.com](apartments.com) search result based on some criteria that are present in the page. This is current as of January 1, 2019.

It's a web scraper for the result listing and produces a CSV that has all the entries nicely parsed. 

These are the criteria I'm using:
`'Option Name', 'Contact', 'Address', 'Size', 'Rent', 'Monthly Fees', 'One Time Fees', 'Pet Policy', 'Distance', 'Duration', 'Parking', 'Gym', 'Kitchen', 'Amenities', 'Features', 'Living Space', 'Lease Info', 'Services', 'Property Info', 'Indoor Info', 'Outdoor Info'` and they come from the entries that apartments.com shows on the page as well as from the Google Maps API (given an address to commute to, I am getting the approximate transit distance and duration to a destination address).

### Google Maps API Change Note:

Since Google Maps now requires billing to be enabled in order to use the API, I have added made it default to skip calculating the distance and duration. Turn `useGoogleMaps` to `true` in `config.ini` if you do have a Google Maps key. The code might not work since I haven't felt comfortable with turning billing on, so I haven't been able to test. Feel free to submit a PR if you check and something is broken.

### How to use:

Please note that this assumes you have Python installed. It works with Python 2.7 and Python 3.5+.
You can install Python from [here](https://www.python.org/downloads/). 
You also need to install 
* beautifulsoup4 from [here](https://www.crummy.com/software/BeautifulSoup/bs4/doc/) and you'll probably need `pip` to do that (`python -m pip install beautifulsoup4` on Windows should do it).
* requests either through pip ('python -m pip install requests') or directions for your setup found [here](http://docs.python-guide.org/en/latest/starting/installation/)

In order to generate the CSV file:

1. Rename config_example.ini to config.ini.
1. Search for apartments on apartments.com. Use your own criteria using the app. Copy the URL.
    - Replace the parenthesis after "apartmentsURL:" in config.ini with the copied URL.
1. Get an API key from [Google Maps API](https://developers.google.com/maps/documentation/distance-matrix/get-api-key) (this is for calculating distances / times using Google Maps).
    - Replace the parenthesis after "mapsAPIKey:" in config.ini with the key.
1. Search for the address you want to commute to on [Google Maps](https://www.google.com/maps). Copy the Google formatted address. For example, for the Empire State building, that address looks like "350 5th Ave New York, NY 10118".
    - Replace the parenthesis after "targetAddress:" in config.ini with the copied address.
1. If you want to change the units between metric and imperial, change the "mapsUnits:" field.
1. If you want directions with a specific mode of transportation, alter "mapsMode:". See more options on [Google's API site](https://developers.google.com/maps/documentation/distance-matrix/).
    - If the maps mode is transit, you might want to also fill out the "mapsTransitRouting:" field (alternatives are fewer_transfers and less_walking; they may only be available to paying Maps API customers). 
1. If you want, change the morning and evening commute times. The morning one is the time you want to arrive at destination and the evening one is the time you want to leave (work). The Google API search is for tomorrow (next day) at these times. You can replace these times but keep the format HH:mm AM / PM.
1. You can also change the "printScores:" field to true, which will also print default scores for all options/criteria. This is mostly for my testing purposes for compareApp. Please note that compareApp works even if this is set to false and no scores are present.
1. If you want your output file to be named something other than output.csv, change the name of the file (output) after the "fname:" field.
1. Run `python parse_apartments.py` to generate the CSV file that you can then import.

You can then import that CSV file into the compareApp.
