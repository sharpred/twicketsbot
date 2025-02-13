""" module providing useful helper functions """

from time import sleep
import os
import logging
import http.client
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
        logging.debug("sending %s",message)
        conn = http.client.HTTPSConnection("api.prowlapp.com")
        data = json.dumps({
            "apikey": self.prowl_api_key,
            "application": "TwicketsBot",
            "event": "Ticket Alert",
            "description": message,
        })
        headers = {'Content-Type': 'application/json'}
        conn.request("POST", "/publicapi/add", body=data, headers=headers)
        response = conn.getresponse()
        response.read()
        logging.debug(response.status)
    