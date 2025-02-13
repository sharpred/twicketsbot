""" module for holding and purchasing tickets on twickets """

from time import sleep
import os
import logging
import http.client
import json

headers = {
  'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:101.0) Gecko/20100101 Firefox/101.0',
  'Accept-Encoding': 'gzip, deflate',
  'Accept': '*/*',
  'Connection': 'keep-alive',
  'Content-Type': 'application/json'
}
cookies = {
            'clientId': os.getenv("TWICKETS_CLIENT_ID"),
            'territory': 'GB',
            'locale': 'en_GB'
}

logging.captureWarnings(True)
logging.basicConfig(level=logging.DEBUG)

class NotTwoHundredStatusError(Exception):
    """Twickets sometimes throws errors due to cloudflare rate limiting, want to capture this as an exception"""
    def __init__(self, message):
        super().__init__(message)

class TwicketsClient:
    """Base class for handling Twickets API logic."""
    BASE_URL = "www.twickets.live"
    REQUIRED_KEYS = [
        "TWICKETS_API_KEY", 
        "TWICKETS_EMAIL", 
        "TWICKETS_PASSWORD",
        "TWICKETS_CLIENT_ID",  
        "TWICKETS_EVENT_ID", 
        "PROWL_API_KEY"
    ]

    def __init__(self):
        self.api_key = os.getenv("TWICKETS_API_KEY")
        self.email = os.getenv("TWICKETS_EMAIL")
        self.password = os.getenv("TWICKETS_PASSWORD")
        self.event_id = os.getenv("TWICKETS_EVENT_ID")
        self.prowl_api_key = os.getenv("PROWL_API_KEY")
        self.time_delay = 45
        self.token = None

    def check_env_variables(self):
        """ check required keys all present """
        missing_keys = [
            key for key in self.REQUIRED_KEYS if not os.getenv(key)]
        if missing_keys:
            for key in missing_keys:
                logging.error("Environment variable %s is not set", key)
            raise RuntimeError("Missing required environment variables")
        else:
            print("All required keys are populated")

    def send_prowl_notification(self, message):
        """ send a prowl notification """
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

    def validate_auth_response(self, response):
        """ Validate the authentication response """
        required_keys = required_keys = {"responseData", "responseCode", "description", "clock"}
        if all(key in response for key in required_keys):
            return response['responseData']
        return None

    def authenticate(self):
        """Log in to the Twickets website."""
        conn = http.client.HTTPSConnection(self.BASE_URL)
        url = f"/services/auth/login?api_key={self.api_key}"
        data = json.dumps({
            "login": self.email,
            "password": self.password,
            "accountType": "U",
        })
        conn.request("POST", url, body=data, headers=headers)
        response = conn.getresponse()
        if response.status == 200:
            result = json.loads(response.read().decode())
            logging.debug(result)
            return self.validate_auth_response(result)
        return None

    def check_event_availability(self):
        """ Check ticket availability """
        conn = http.client.HTTPSConnection(self.BASE_URL)
        url = f"/services/g2/inventory/listings/{self.event_id}?api_key={self.api_key}"
        conn.request("GET", url, headers=headers)
        response = conn.getresponse()
        if response.status == 200:
            result = json.loads(response.read().decode())
            return result.get("responseData")
        raise NotTwoHundredStatusError(f"check_event_availability status: {response.status}")

    def run(self):
        """ run da ting """
        try:
            self.check_env_variables()
            token = self.authenticate()
            if token is None:
                raise RuntimeError("Authentication failed for some reason")
            while True:
                try:
                    items = self.check_event_availability()
                    backoff = 0
                except KeyboardInterrupt:
                    items = None
                    backoff == 0
                    logging.debug("User interrupted session")
                except NotTwoHundredStatusError:
                    items = None
                    backoff = 2 if backoff == 0 else backoff * 2
                if items:
                    id = str(items[0]['id']).split('@')[1]
                    url = f"https://www.twickets.live/app/block/{id},1"
                    self.send_prowl_notification(f"Check {url}")
                else:
                    logging.debug("There are currently no tickets available")
                sleep(self.time_delay + backoff)
        except KeyboardInterrupt:
            logging.debug("User interrupted connection with ctrl-C")
        except Exception as e:
            logging.error(e)

if __name__ == "__main__":
    client = TwicketsClient()
    client.run()
