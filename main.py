""" module for holding and purchasing tickets on twickets """

# from time import sleep
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

        if response.status_code == 200:
            result = response.json()
            logging.debug("Result contents: %s", result)

            if result.get("responseCode") == 100 and result.get("description") == "OK":
                return result.get("responseData")

            logging.error("Login failed: unexpected response data")
            return None
        else:
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
        return response.json()

    def check_availability(self):
        """ check ticket availability """
        url = f"{self.BASE_URL}events/{self.event_id}/tickets"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def purchase_ticket(self, ticket_id):
        """ purchase a ticket """
        url = f"{self.BASE_URL}purchases"
        data = {"ticketId": ticket_id}
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()

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

    def run(self):
        """ run da ting """
        self.check_env_variables()
        token = self.authenticate()

        if token is not None:
            logging.debug("Authenticated ok %s",token)
            my_aid = self.aid(token)
            logging.debug(my_aid)
        else:
            raise RuntimeError("Authentication failed for some reason")
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
