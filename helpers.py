""" module providing useful helper functions """

from time import sleep
import os
import logging
import requests
import json

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