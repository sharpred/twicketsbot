""" module for holding and purchasing tickets on twickets """

from time import sleep
import os
import logging
import requests

# Configure Charles Proxy
PROXY_SERVER = "http://127.0.0.1:8888"  # Default Charles PROXY_SERVER address

proxies = {
    "http": PROXY_SERVER,
    "https": PROXY_SERVER,  # Enable HTTPS proxying
}

headers = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:101.0) Gecko/20100101 Firefox/101.0',
    'content-type': 'application/json'
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
    BASE_URL = "https://www.twickets.live/services/"
    # Required environment variables
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
        self.time_delay = 30
        self.session = requests.Session()
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
        prowl_url = "https://api.prowlapp.com/publicapi/add"
        data = {
            "apikey": self.prowl_api_key,
            "application": "TwicketsBot",
            "event": "Ticket Alert",
            "description": message,
        }
        response = requests.post(prowl_url, data=data, timeout=10)
        response.raise_for_status()

    def validate_auth_response(self,response):
        """
        Validate the authentication response from Twickets.

        Args:
            response (dict): The JSON response from the API.

        Returns:
            str | None: The responseData if valid, otherwise None.
        """
        if not isinstance(response, dict):
            logging.error("Invalid response format: Expected a dictionary")
            return None

        required_keys = {"responseData", "responseCode", "description", "clock"}
    
        if not required_keys.issubset(response.keys()):
            logging.error("Missing required keys in response: %s", response)
            return None

        if response["responseCode"] == 100 and response["description"] == "OK":
            return response["responseData"]

        logging.error("Unexpected response data: %s", response)
        return None

    def authenticate(self):
        """Log in to the Twickets website."""

        url = f"{self.BASE_URL}auth/login?api_key=" + self.api_key
        
        
        data = {
            "login": self.email,
            "password": self.password,
            "accountType": "U",
        }
        response = self.session.post(
            url=url,
            proxies=proxies,
            headers=headers,
            json=data,
            cookies=cookies,
            verify=False
        )
        response.raise_for_status()
        if response.status_code == 200:
            result = response.json()
            logging.debug("Result contents: %s", result)
            return self.validate_auth_response(result)
        
        logging.error("Login: response %s", response.status_code)
        logging.error(str(response))
        return None
    
    def aid(self, token):
        """aid is called immediately after authentication on website, so duplicated here"""
        url = f"{self.BASE_URL}auth/aid?api_key=" + self.api_key
        aid_headers = headers.copy()
        aid_headers['Authorization'] = f"TOKEN {token}"
        aid_headers['Referer'] = "referer: https://www.twickets.live/app/login?target=https:%2F%2Fwww.twickets.live%2Fen%2Fuk"

        response = self.session.get(
            url=url,
            proxies=proxies,
            headers=aid_headers,
            cookies=cookies,
            verify=False
        )
        response.raise_for_status()
        if response.status_code == 200:
            result = response.json()
            logging.debug("aid contents: %s", result)
            return self.validate_auth_response(result)
        
        logging.error("aid: response %s", response.status_code)
        logging.error(str(response))
        return None

    def check_event_availability(self):
        url = f"{self.BASE_URL}g2/inventory/listings/" + self.event_id + '?api_key=' + self.api_key
        avail_headers = headers.copy()
        avail_headers['Referer'] = f"referer: {self.BASE_URL}/event/{self.event_id}"
        response = self.session.get(
            url=url,
            proxies=proxies,
            headers=avail_headers,
            cookies=cookies,
            verify=False
        )
        response.raise_for_status()
        if response.status_code == 200:
            result = response.json()
            logging.debug("check_event_availability: %s", result)
            return self.validate_auth_response(result)
        
        logging.error("check_event_availability %s", response.status_code)
        raise NotTwoHundredStatusError(f"check_event_availability status: {response.status_code}")

    def run(self):
        """ run da ting """
        try:

            self.check_env_variables()
        
            token = self.authenticate()

            if token is None:
                raise RuntimeError("Authentication failed for some reason")
            
            aid_token = self.aid(token)

            if aid_token is None:
                raise RuntimeError("aid failed for some reason")

            while 1:

                try:
                    items = self.check_event_availability()
                    backoff = 0
                except NotTwoHundredStatusError:
                    items = None
                    if backoff == 0:
                        backoff = 2
                    else:
                        backoff += backoff

                count = len(items)

                if count < 0:
                    current = items.pop(0)
                    id = str(current['id']).split('@')[1]
                    url = f"https://www.twickets.live/app/block/{id},1"
                    self.send_prowl_notification(f"Check {url}")
                else:
                    logging.debug("There are currently %s tickets available", count)   

                sleep(self.time_delay+backoff)


            


        except Exception as e:
            #self.send_prowl_notification(e)
            logging.error(e)
        # while True:
        #    tickets = self.check_availability()
        #    if tickets:
        #        message = "Tickets available!"
        #        self.send_prowl_notification(message)
        #        print(message)
        #    sleep(60)


if __name__ == "__main__":
    client = TwicketsClient()
    client.run()
