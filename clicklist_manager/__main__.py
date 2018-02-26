import clicklist_manager
import time
import logging
import argparse

logging.basicConfig(level=logging.INFO)

parser = argparse.ArgumentParser(description='Process some integers.')

parser.add_argument('--update_cart', action="store_true", default=False)
parser.add_argument('--empty_cart', action="store_true", default=False)
parser.add_argument('--update_cache', action="store_true", default=False)
parser.add_argument('--update_spreadsheet', action="store_true", default=False)
args = parser.parse_args()
if args.update_cart:
    clicklist_manager.update_cart()
elif args.empty_cart:
    clicklist_manager.empty_cart()
elif args.update_cache:
    clicklist_manager.update_cache()
elif args.update_spreadsheet:
    clicklist_manager.update_spreadsheet()
