# Clicklist Manager

This is a utility meant to make it much easier to build shopping lists with Kroger/Fred Meyer ClickList.

The idea is to have a Google Docs spreadsheet containing all items ever purchased with useful categorization and filtering.  You can then just update the quantity of the items you want to purchase, and the clicklist manager will update the ClickList cart with the appropriate items and quantity.  It works seemlessly with manually adding items to the cart for things it isn't aware of.  The clicklist-manager also includes the ability to build the initial spreadsheet as well as to keep it updated with items manually added to the cart.

The code supports both a web-server frontend (which can be used to update Clicklist from the spreadsheet directly) as well as a cmdline interface.

## Running
To start the webserver:
```
uwsgi --enable-threads --http :8084 --wsgi-file wsgi.py
```

To use the cmdline interface:
python -m clicklist_manager <options>

## Installation

The code uses selenium to scrape the Clicklist website.  It does not work with PhantomJS, and using headless-chrome is unreliable (GUI chrome seems to work better for some reason).  I have had the best success with using Firefox with selenium, as it is the most reliable, and works properly both with the browser visible and headless.

The code has 2 different interfaces for accessing the GoogleDocs spreadsheet:
1. Using openpyxl: Used to updae ClickList
   The sheet must have been shared, and added to config.py

2. Using oauth2client and google-api-python-client
   This method is used to update the GoogleDocs spreadsheet

### Requirements:
```
pip install google-api-python-client oauth2client openpyxl selenium requests
```
If you want to use the webserver:
```
pip install wsgi
```

### Install the latest firefox gecko-driver for selenium from https://github.com/mozilla/geckodriver/releases

Further information can be found here: https://www.seleniumhq.org/download/

### Create a  GoogleDocs sheet

Start from the template: https://docs.google.com/spreadsheets/d/1cP5kxqIlaFky0qJvS8CaF1-ofATcfNt7q4BDmtARxhc/edit?usp=sharing
You must then share the sheet (and copy the share link into config.py below)

The only requirement is that the 1st 4 columns must be:
1. Count
2. Item name/ hyperlink
3. User supplies (I use this for categorization)
4. Unit Price

The template contains links to update and empty the cart.  These would need to be customized for your needs

It is probably easiest to make a copy of my You can make a copy of my Grocery templatewith the following headers in Row 1:

### Create a config.py file
copy the config.py.example to config.py and update all fields

### Enable Google Sheets API v4 (needed to enable spreadsheet updating)
Follow Google's instructions for enabling the API: https://developers.google.com/sheets/api/quickstart/python

