""" module providing useful helper functions """

from time import sleep
import os
import logging
import requests
import json
from pathlib import Path
from deepdiff import DeepDiff

logging.captureWarnings(True)
logging.basicConfig(level=logging.DEBUG)

class NotTwoHundredStatusError(Exception):
    """Twickets sometimes throws errors due to cloudflare rate limiting, want to capture this as an exception"""
    def __init__(self, message):
        super().__init__(message)

class ProwlNoticationsClient:
    
    def __init__(self):
        self.prowl_api_key = os.getenv("PROWL_API_KEY")

    def send_notification(self, message):
        """ send a prowl notification """
        prowl_url = "https://api.prowlapp.com/publicapi/add"
        data = {
            "apikey": self.prowl_api_key,
            "application": "TwicketsBot",
            "event": "Ticket Alert",
            "description": message,
        }
        response = requests.post(prowl_url, data=data, timeout=10)
        response.raise_for_status()

def compare_json_files(path1: str, path2: str) -> bool:
    """Compares two JSON files and returns True if they match, otherwise False."""
    print("Comparing files")
    file1, file2 = Path(path1), Path(path2)

    with open(file1, "r", encoding="utf-8") as f1, open(file2, "r", encoding="utf-8") as f2:
        data1 = json.load(f1)  
        data2 = json.load(f2)

    diff = DeepDiff(data1, data2, ignore_order=True)

    if not diff:
        print("Files match")
    else:
        print("Differences found:")
        print(diff.pretty())  # Pretty-print the differences
