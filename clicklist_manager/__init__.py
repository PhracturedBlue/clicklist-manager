#!/usr/bin/env python3

import os
import re
import time
import requests
import logging
import config
import uuid
import clicklist_manager.excel
import clicklist_manager.sheet

from io import (BytesIO, StringIO)
from clicklist_manager.cache import (load_cache, save_cache)

import selenium
from selenium import webdriver
from selenium.common.exceptions import (ElementNotVisibleException,
                                        WebDriverException,
                                        NoSuchElementException)


BASEURL = config.BASEURL
username = config.username
password = config.password
xls_link = config.xls_link
try:
    browser_type = config.browser_type
except:
    browser_type = "Firefox"

def download(link):
    """Downlaod file into variable for requested link"""
    session = requests.Session()
    response = session.get(link)
    return response.content

def wait_for(element, elemtype, query, max_count=60):
    """Wait for requested element on dymanically loading pages"""
    count = 0
    while count < max_count:
        try:    
            if elemtype == "id":
                found = element.find_element_by_id(query)
            elif elemtype == "class":
                found = element.find_element_by_class_name(query)
            else:
                logging.error("Unknown type: {}".format(elemtype))
                break
            return found
        except NoSuchElementException:
            logging.debug("Waiting for %s = %s (Count: %d)",
                          elemtype, query, count)
            time.sleep(1)
            count += 1
    url = "/tmp/clicklist.{}.png".format(uuid.uuid4().hex)
    logging.error("Failed to locate {}:{}.  Taking screenshot at {}".format(elemtype, query, url))
    try:
        browser = element.parent
    except:
        browser = element

    try:
        browser.save_screenshot(url)
    except:
        try:
            browser.get_screenshot_as_file(url)
        except:
            logging.error("Failed to take screenshot for debugging")
    raise TimeoutError

def get_web_driver(type=browser_type):
    if type.lower() == "chrome":
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        #options.add_argument('--window-size=1920x1080')
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36")
        browser = webdriver.Chrome(chrome_options=options)
        #browser.get(BASEURL + 'favicon.ico')
        #browser.add_cookie({'name': 'bypassUnsupportedBrowser', 'value':'true'})
    elif type.lower() == "firefox":
        os.environ['MOZ_HEADLESS'] = '1'
        browser = webdriver.Firefox()
    elif type.lower() == "phantomjs":
        browser = webdriver.PhantomJS()
    else:
        raise Exception("No webdriver specified")
    return browser
    
def login(browser=None):
    # but browser can be replaced with browser = webdriver.FireFox(),
    # which is good for debugging.
    if not browser:
        browser = get_web_driver()
    URL = BASEURL + 'signin?redirectUrl=/'
    browser.get(URL)
    #try:
    #   unsupported = browser.find_element_by_class_name("unsupported-continue-link")
    #   unsupported.click()
    #   time.sleep(1)
    #   browser.get(URL)
    #except NoSuchElementException:
    #   pass
    user_elem = wait_for(browser, 'id', "SignIn-emailInput")
    pass_elem = browser.find_element_by_id("SignIn-passwordInput")
    submit_elem = browser.find_element_by_id("SignIn-submitButton")
    user_elem.clear()
    user_elem.send_keys(username)
    pass_elem.clear()
    pass_elem.send_keys(password)
    submit_elem.click()
    wait_for(browser, 'class', 'NextAvailableTimeSlot')
    return browser

def get_purchase_list(browser):
    browser.get(BASEURL + 'mypurchases/')
    links = browser.find_elements_by_class_name("ReceiptList-receiptDateLink")
    res = {}
    #divs = browser.find_elements_by_class_name("ReceiptList-line")
    for link in links:
        res[link.text] = link
    return res

def get_purchases(browser, date):
    purchases = get_purchase_list(browser)
    if not purchases.get(date):
        return
    purchases[date].click()
    wait_for(browser, 'class', 'ReceiptDetail-totalPricePaidFooter')
    items = browser.find_elements_by_class_name("ReceiptDetail-rowContainer")
    order = []
    for item in items:
        name_elem = item.find_element_by_class_name('ReceiptDetail-itemName')
        name = name_elem.text
        link = name_elem.get_attribute('href')
        count = item.find_element_by_class_name('ReceiptDetail-itemQuantity').text
        unit_price = item.find_element_by_class_name('ReceiptDetail-itemUnitPrice').text
        order.append({'name': name, 'link': link, 'count': count, 'unit_price': unit_price})
    return order

def add_item_to_cart(browser, item):
    link = item['link']
    count = int(item['count'])
    name = item['name']
    browser.get(link)
    wanted_upc = get_upc(link)
    upc = ''
    retry = 10
    
    div = wait_for(browser, 'class', 'Page-content')
    try :
        div.find_element_by_class_name("ProductDetailsServiceError")
        logging.error("Item not currently avaialable: {} ({})".format(name, link))
        return
    except:
        pass
        
    while True:
        try:
            upc = div.find_element_by_class_name('ProductDetails-upc').text
            upc = upc[upc.rindex(' ')+1:]
            if upc == wanted_upc:
                break
        except:
            pass
        retry -= 1
        if retry == 0:
            logging.error("Couldn't open {} ({})".format(name, link))
            return
        time.sleep(0.5)
    try:
        btn = div.find_element_by_class_name("AddItem-btn")
        btn.click()
        count_elem = wait_for(div, "class", 'Quantity-input')
    except:
        pass
    try:
        count_elem = div.find_element_by_class_name('Quantity-input')
    except:
        logging.error("Item cannot be added to cart: {} ({})".format(name, link))
        return

    cur_count = int(count_elem.get_attribute('value'))
    name_elem = div.find_element_by_class_name('ProductDetails-header')
    incBtn = div.find_element_by_id("incrementBtn")
    decBtn = div.find_element_by_id("decrementBtn")
    #while cur_count < count:
    #    incBtn.click()
    #    cur_count += 1
    #while cur_count > count:
    #    decBtn.click()
    #    cur_count -= 1
    count_elem.clear()
    count_elem.send_keys("{}".format(count))
    count_elem.send_keys("\n")
    logging.info("Added {} of '{}' ({})".format(count, name_elem.text, link))

def create_order(browser, items):
    for link, item in items.items():
        add_item_to_cart(browser, link, int(item['count']))

def get_upc(link):
    return link[link.rindex('/')+1:]

def verify_cart(browser, items, add=True):
    changed = False
    browser.get(BASEURL + "shopping/cart")
    wait_for(browser, "class", "Continue-Shopping")
    cart = browser.find_elements_by_class_name("List-listItem")
    seen = {}
    unexpected = []

    for item in cart:
        name = item.find_element_by_class_name('CartDetailsItem-name').get_attribute('title')
        link = item.find_element_by_class_name('ProductDetailsLink').get_attribute('href')
        upc = get_upc(link)
        count_elem = item.find_element_by_class_name('Quantity-input')
        count = count_elem.get_attribute('value')
        found = None
        for item_link, item_ref in items.items():
            item_upc = get_upc(item_link)
            if upc == item_upc:
                found = 1
                seen[item_link] = 1
                if int(count) != int(item_ref['count']):
                    logging.warning("Count for {} was {} but should be {}.  Fixing".format(name, int(count), int(item_ref['count'])))
                    count_elem.clear()
                    count_elem.send_keys("{}".format(int(item_ref['count'])))
                    count_elem.send_keys("\n")
                    changed = True
                break
        if not found:
            unexpected.append("Found unexpected item in cart: {} Count: {}".format(name, count))
     
    for link, item in items.items():
        if link not in seen:
            if add:
                add_item_to_cart(browser, item)
                changed = True
            else:
                logging.warning("Missing item in cart: {} ({}) Count: {}".format(item['name'], link, int(item['count'])))
    if changed and add:
        logging.info("Rescanning cart")
        logging.info("************************************************************")
        verify_cart(browser, items, False)
    else:
        for msg in unexpected:
            logging.warning(msg) 

def clear_order(browser):
    browser.get(BASEURL + "shopping/cart")
    wait_for(browser, "class", "Continue-Shopping")
    cart = browser.find_elements_by_class_name("List-listItem")
    seen = {}
    for item in cart:
        remove = item.find_element_by_class_name('CartDetailsItem-removeLink')
        name = item.find_element_by_class_name('CartDetailsItem-name').get_attribute('title')
        link = item.find_element_by_class_name('ProductDetailsLink').get_attribute('href')
        upc = get_upc(link)
        count_elem = item.find_element_by_class_name('Quantity-input')
        count = count_elem.get_attribute('value')
        logging.info("Removing {} of '{}' ({})".format(count, name, upc))
        remove.click()

def update_cart():
    xls_data = download(xls_link)
    logging.info("Downloaded List: {} bytes".format(len(xls_data)))
    l = clicklist_manager.excel.build_order(BytesIO(xls_data))
    logging.info("Found {} items to add to cart".format(len(l.keys())))
    logging.info("Logging in")
    browser = login()
    logging.info("Logged in")
    #create_order(browser, l)
    verify_cart(browser, l)
    logging.info("Finished updating cart")

def empty_cart():
    logging.info("Logging in")
    browser = login()
    logging.info("Logged in")
    clear_order(browser)
    logging.info("Finished emptying cart")

def update_cache():
    cache = load_cache()
    logging.info("Logging in")
    browser = login()
    logging.info("Logged in")
    l = get_purchase_list(browser)
    for p in l.keys():
        if p not in cache:
            logging.info("Updating purchase history for {}".format(p))
            cache[p] = get_purchases(browser, p)
        else:
            logging.info("Skipping purchase history for {}".format(p))
    save_cache(cache)

def update_spreadsheet():
    seen = {}
    items = {}
    newrows = []
    cache = load_cache()
    for key in cache:
        for item in cache[key]:
            if 'link' not in item or not item['link']:
                continue
            upc = get_upc(item['link'])
            if upc not in items:
                items[upc] = item
    [id] = re.findall(r'spreadsheets/d/([^/]+)', config.xls_link)
    sheet = clicklist_manager.sheet.Sheet(id, config.secret_json)
    rows = sheet.get_rows('B2:B')
    for row in rows:
        if 'hyperlink' in row['values'][0]:
            link = row['values'][0]['hyperlink']
            upc = get_upc(link)
            seen[upc] = 1
    rownum = len(rows) +2
    for upc in items:
        if upc in seen:
            #print("Seen: {}".format(items[upc]['name']))
            continue
        item = items[upc]
        hyperlink = item['link']
        text = item['name']
        price = item['unit_price']
        newrows.append(["",
                     '=HYPERLINK("{}","{}")'.format(hyperlink, text),
                     '',
                     price,
                     '=if(D{}="","",A{}*D{})'.format(rownum, rownum, rownum)])
        rownum += 1
    sheet.add_rows("A{}:E".format(len(rows)+2), newrows)
