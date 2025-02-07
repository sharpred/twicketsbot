""" module for holding and purchasing tickets on twickets """

#from time import sleep
import os
import logging
import json
import requests

# Configure Charles Proxy
PROXY_SERVER = "http://127.0.0.1:8888"  # Default Charles PROXY_SERVER address

proxies = {
    "http": PROXY_SERVER,
    "https": PROXY_SERVER,  # Enable HTTPS proxying
}

logging.captureWarnings(True)
logging.basicConfig(level=logging.DEBUG)


class TwicketsClient:
    """Base class for handling Twickets API logic."""
    BASE_URL = "https://www.twickets.live/services/"
    # Required environment variables
    REQUIRED_KEYS = [
        "TWICKETS_API_KEY", "TWICKETS_EMAIL", "TWICKETS_PASSWORD", "TWICKETS_EVENT_ID", "PROWL_API_KEY"
    ]

    def __init__(self):
        self.api_key = os.getenv("TWICKETS_API_KEY")
        self.email = os.getenv("TWICKETS_EMAIL")
        self.password = os.getenv("TWICKETS_PASSWORD")
        self.event_id = os.getenv("TWICKETS_EVENT_ID")
        self.prowl_api_key = os.getenv("PROWL_API_KEY")
        self.session = requests.Session()
        self.token = None
    
    def authenticate(self):
        """log in to the Twickets website."""
        
        url = f"{self.BASE_URL}auth/login?api_key=" + self.api_key
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:101.0) Gecko/20100101 Firefox/101.0',
            'content-type': 'application/json'
            }
        cookies = {
            'clientId': 'e0111c5e-ad13-4209-9c08-16e913b5baf5', 
            'territory': 'GB', 
            'locale': 'en_GB'}
        data = {
            "login": self.email,
            "password": self.password,
            "accountType": "U",
        }
        login_data = json.dumps(data)
        logging.debug("user %s", self.email)
        logging.debug("pass %s", self.password)
        response = self.session.post(url=url, proxies=proxies,headers=headers,json=data,cookies=cookies, verify=False)
        if response.status_code == 200:
            result = response.json()
            logging.debug("Result contents: %s", result)
            if result['responseCode']:
                logging.debug("Login: response status %s", result['responseCode'])
            if result['responseData']:
                return result['responseData']
            else:
                logging.error("Login: no results")
                return None
        else:
            logging.error("Login: response %s",response.status_code)
            logging.error(str(response))
            return None

    def check_env_variables(self):
        """ check required keys all present """
        missing_keys = [key for key in self.REQUIRED_KEYS if not os.getenv(key)]
        if missing_keys:
            for key in missing_keys:
                print(f"Warning: Missing environment variable {key}")
            exit(1)
        else:
            print("All required keys are populated")

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
        self.authenticate()
        #while True:
        #    tickets = self.check_availability()
        #    if tickets:
        #        message = "Tickets available!"
        #        self.send_prowl_notification(message)
        #        print(message)
        #    sleep(60)

if __name__ == "__main__":
    client = TwicketsClient()
    client.run()
