#!/usr/bin/env python3

import os
import time
import requests
import logging
import config
import clicklist_manager.excel

from io import (BytesIO, StringIO)
from clicklist_manager.cache import (load_cache, save_cache)

from selenium import webdriver
from selenium.common.exceptions import (ElementNotVisibleException,
                                        WebDriverException,
                                        NoSuchElementException)


BASEURL = config.BASEURL
username = config.username
password = config.password
xls_link = config.xls_link

def download(link):
    """Downlaod file into variable for requested link"""
    session = requests.Session()
    response = session.get(link)
    return response.content

def wait_for(browser, elemtype, query, max_count=120):
    """Wait for requested element on dymanically loading pages"""
    count = 0
    while count < max_count:
        try:    
            if elemtype == "id":
                found = browser.find_element_by_id(query)
            elif elemtype == "class":
                found = browser.find_element_by_class_name(query)
            else:
                logging.error("Unknown type: {}".format(elemtype))
                break
            return found
        except NoSuchElementException:
            logging.debug("Waiting for %s = %s (Count: %d)",
                          elemtype, query, count)
            time.sleep(1)
            count += 1
    raise TimeoutError

def login():
    # but browser can be replaced with browser = webdriver.FireFox(),
    # which is good for debugging.
    #options = webdriver.ChromeOptions()
    #options.add_argument('headless')
    #browser = webdriver.Chrome(chrome_options=options)
    os.environ['MOZ_HEADLESS'] = '1'
    browser = webdriver.Firefox()
    URL = BASEURL + 'signin?redirectUrl=/'
    browser.get(URL)
    try:
       unsupported = browser.find_element_by_class_name("unsupported-continue-link")
       unsupported.click()
       time.sleep(1)
       browser.get(URL)
    except NoSuchElementException:
       pass
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

def add_item_to_cart(browser, link, count):
    browser.get(link)
    wanted_upc = get_upc(link)
    upc = ''
    retry = 10
    
    div = wait_for(browser, 'class', 'Page-content')
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
            logging.error("Couldn't open {}".format(link))
            return
        time.sleep(0.5)
    try:
        btn = div.find_element_by_class_name("AddItem-btn")
        btn.click()
    except:
        pass
    count_elem = wait_for(div, "class", 'Quantity-input')
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
    logging.info("Adding {} of '{}' ({})".format(count, name_elem.text, link))

def create_order(browser, items):
    for link, count in items.items():
        add_item_to_cart(browser, link, int(count))

def get_upc(link):
    return link[link.rindex('/')+1:]

def verify_cart(browser, items):
    browser.get(BASEURL + "shopping/cart")
    wait_for(browser, "class", "Continue-Shopping")
    cart = browser.find_elements_by_class_name("List-listItem")
    seen = {}
    for item in cart:
        name = item.find_element_by_class_name('CartDetailsItem-name').get_attribute('title')
        link = item.find_element_by_class_name('ProductDetailsLink').get_attribute('href')
        upc = get_upc(link)
        count_elem = item.find_element_by_class_name('Quantity-input')
        count = count_elem.get_attribute('value')
        found = None
        for item_link, item_count in items.items():
            item_upc = get_upc(item_link)
            if upc == item_upc:
                found = 1
                seen[item_link] = 1
                if int(count) != int(item_count):
                    logging.warning("Count for {} was {} but should be {}.  Fixing".format(name, int(count), int(item_count)))
                    count_elem.clear()
                    count_elem.send_keys("{}".format(int(item_count)))
                    count_elem.send_keys("\n")
                break
        if not found:
            logging.warning("Found unexpected item in cart: {} Count: {}".format(name, count))
     
    for link, count in items.items():
        if link not in seen:
            logging.warning("Missing item in cart: {} Count: {}".format(link, int(count)))
            add_item(browser, link, int(count))

def update_cart():
    xls_data = download(xls_link)
    logging.info("Downloaded List: {} bytes".format(len(xls_data)))
    l = clicklist_manager.excel.build_order(BytesIO(xls_data))
    logging.info("Found {} items to add to cart".format(len(l.keys())))
    logging.info("Logging in")
    browser = login()
    logging.info("Logged in")
    create_order(browser, l)
    verify_cart(browser, l)
    logging.info("Finished updating cart")

# logging.basicConfig(level=logging.INFO)
# cache = {}
#l = get_purchase_list(browser)
#for p in l.keys():
#    cache[p] = get_purchases(browser, p)
#
#save_cache()
