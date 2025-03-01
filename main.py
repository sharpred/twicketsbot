""" module for holding and purchasing tickets on twickets """

from time import sleep
from datetime import datetime, timedelta
import socket
import os
import logging
import http.client
import time
import random
import json
import sys
from helpers import NotTwoHundredStatusError, ProwlNoticationsClient
from telegram import TelegramBotClient

#logging.captureWarnings(True)
logging.basicConfig(level=logging.WARNING)
print(f"Logging level set to: {logging.getLogger().getEffectiveLevel()}")

class TwicketsClient:
    """Base class for handling Twickets API logic."""
    BASE_URL = "www.twickets.live"
    REQUIRED_ENV_VARIABLES = [
        "TWICKETS_API_KEY", 
        "TWICKETS_EMAIL", 
        "TWICKETS_PASSWORD",
        "TWICKETS_CLIENT_ID",  
        "TWICKETS_EVENT_ID", 
        "PROWL_API_KEY"
    ]

    MIN_TIME=15
    MAX_TIME=30
    MAX_RETRIES = 5  # Number of retry attempts
    BASE_DELAY = 60   # Base delay in seconds (exponential backoff)

    def __init__(self):
        self.api_key = os.getenv("TWICKETS_API_KEY")
        self.email = os.getenv("TWICKETS_EMAIL")
        self.password = os.getenv("TWICKETS_PASSWORD")
        self.event_id = os.getenv("TWICKETS_EVENT_ID")
        
        self.token = None
        self.conn = http.client.HTTPSConnection(self.BASE_URL)

        self.headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:101.0) Gecko/20100101 Firefox/101.0',
            'Accept-Encoding': 'gzip, deflate',
            'Accept': '*/*',
            'Connection': 'keep-alive',
            'Content-Type': 'application/json',
            'Cache-Control': 'no-cache'
        }
        self.prowl = ProwlNoticationsClient()
        self.teleclient = TelegramBotClient()

    NOTIFIED_IDS_FILE = "notified_ids.json"

    def load_notified_ids(self):
        """Load notified IDs from a file."""
        if os.path.exists(self.NOTIFIED_IDS_FILE):
            try:
                with open(self.NOTIFIED_IDS_FILE, "r") as f:
                    return set(json.load(f))
            except json.JSONDecodeError:
                return set()
        return set()

    def save_notified_ids(self,notified_ids):
        """Save notified IDs to a file."""
        with open(self.NOTIFIED_IDS_FILE, "w") as f:
            json.dump(list(notified_ids), f)

    def _ensure_connection(self):
        """Ensure the connection is open, reconnect if necessary."""
        retries = 0
        while retries < self.MAX_RETRIES:
            try:
                logging.debug(f"Attempting connection to {self.conn.host}")
                self.conn.connect()
                logging.debug("Connection successful")
                return
            except socket.gaierror as ge:
                logging.warning(f"DNS resolution failed: {ge}. Retrying in {BASE_DELAY * (2 ** retries)}s...")
            except (http.client.HTTPException, OSError):
                logging.warning("Connection error")
                #TODO wrap self.conn.close in method
                self.conn.close()
                self.conn = http.client.HTTPSConnection(self.BASE_URL)
                self.conn.connect()
            retries += 1
            time.sleep(BASE_DELAY * (2 ** retries))
        logging.error("Max retries reached. Could not establish a connection.")

    def check_env_variables(self):
        """ check required keys all present """
        missing_env_variables = [
            key for key in self.REQUIRED_ENV_VARIABLES if not os.getenv(key)]
        if missing_env_variables:
            for key in missing_env_variables:
                logging.error("Environment variable %s is not set", key)
            raise RuntimeError("Missing required environment variables")
        else:
            logging.debug("All required keys are populated")

    def validate_auth_response(self, response):
        """ Validate the authentication response """
        required_keys = required_keys = {"responseData", "responseCode", "description", "clock"}
        if all(key in response for key in required_keys):
            return response['responseData']
        return None

    def authenticate(self):
        """Log in to the Twickets website."""
        self._ensure_connection()
        url = f"/services/auth/login?api_key={self.api_key}"
        data = json.dumps({
            "login": self.email,
            "password": self.password,
            "accountType": "U",
        })
        logging.debug("about to connect")
        self.conn.request("POST", url, body=data, headers=self.headers)
        response = self.conn.getresponse()
        if response.status == 200:
            result = json.loads(response.read().decode())
            token = self.validate_auth_response(result)
            logging.debug("Authenticated successfully")
            return token
        logging.warning(f"Authentication error status {response.status}")
        return None

    def check_event_availability(self):
        """ Check ticket availability """
        logging.debug("Connection socket is none: %s",(self.conn.sock is None))
        self._ensure_connection()
        url = f"/services/g2/inventory/listings/{self.event_id}?api_key={self.api_key}"
        if self.conn.sock is not None:
            try:
                logging.debug(f"Get response event: {self.event_id}")
                self.conn.request("GET", url, headers=self.headers)
                response = self.conn.getresponse()
                if response.status == 200:
                    result = json.loads(response.read().decode())
                    code = result.get("responseCode")
                    clock_val = result.get("clock")
                    items = result.get("responseData")
                    logging.info("Response code %s, clock %s, tickets %s",code, clock_val, len(items))
                    return items
                raise NotTwoHundredStatusError(f"Check availability status: {response.status}")
            except http.client.ResponseNotReady:
                logging.warning("http.client.ResponseNotReady exception")
                pass
            except http.client.HTTPException:
                self.conn.close()
        return []

    def process_ticket(self, id, notified_ids):
        """ Process and notify about a ticket if it's not already notified """
        if id not in notified_ids:
            url = f"https://www.twickets.live/app/block/{id},1"
            found_str = f"found tickets {url}"
            self.prowl.send_notification(found_str)
            logging.info(found_str)
            self.teleclient.send_notification("Ticket Alert", found_str)
            notified_ids.add(id)
            self.save_notified_ids(notified_ids)

    def run(self):
        """ run da ting """
        try:
            logging.debug("Checking env variables")
            count = 1
            notified_ids = self.load_notified_ids()
            self.check_env_variables()
            logging.debug("Authenticating")
            token = self.authenticate()
            if token is None:
                raise RuntimeError("Authentication failed for some reason")
            START_MESSAGE = "starting ticket check"
            logging.debug(START_MESSAGE)  
            attempts = 0
            
            while True:
                now = datetime.now()
                tomorrow = now + timedelta(days=1)
                time_delay = round(random.uniform(self.MIN_TIME,self.MAX_TIME))
                auth_time_delay = round(random.uniform(180,360)) # need a bigger delay if you get a 403    
                
                try:
                    logging.debug("Check cycle %s at %s with %s seconds delay",count,now.strftime("%d/%m %H:%M:%S"),time_delay)
                    items = self.check_event_availability()
                    #reset everything if items returned
                    backoff = 0
                    attempts = 0
                    count +=1
                    if items:
                        if isinstance(items, list):
                            for item in items:
                                id = str(items['id']).split('@')[1]
                                self.process_ticket(id, notified_ids)
                        elif isinstance(items, dict):
                           id = str(items.get('id', '')).split('@')[1]  # Directly access if it's a dictionary 
                           self.process_ticket(id, notified_ids)
                        else:
                            raise TypeError(f"Unexpected type for items: {type(items)} - {items}")
                    SLEEP_INTERVAL = time_delay + (backoff)
                    sleep(SLEEP_INTERVAL)
                except NotTwoHundredStatusError as error_msg:
                    logging.info(f"{error_msg} %s. Attempt {attempts}",now.strftime("%H:%M:%S"))
                    items = None
                    if attempts > self.MAX_RETRIES:
                        #give up
                        self.save_notified_ids(notified_ids)
                        exit_error_message = "Exiting after five failed login attempts"
                        self.prowl.send_notification(exit_error_message)
                        logging.error(exit_error_message)
                        sys.exit(exit_error_message)
                    SLEEP_INTERVAL = auth_time_delay * (2 ** attempts)
                    new_time = now + timedelta(seconds=SLEEP_INTERVAL)
                    logging.warning("Pausing due to 403 error. Resuming at %s", new_time.strftime("%H:%M:%S"))
                    self.conn.close()
                    sleep(SLEEP_INTERVAL)
                    attempts+=1
                    token = self.authenticate()
                    if token is None:
                        raise RuntimeError("Authentication failed for some reason")
        except KeyboardInterrupt:
            QUIT_MESSAGE = "User interrupted connection with ctrl-C on cycle %s"
            logging.info(QUIT_MESSAGE, count)
            self.conn.close()
            self.save_notified_ids(notified_ids)
        except Exception as e:
            self.save_notified_ids(notified_ids)
            logging.error("Cycle %s Caught exception of type %s",count, type(e).__name__)
            error_msg = f"Cycle {count} Caught exception {e}\nitems received {items}"
            self.conn.close()
            self.prowl.send_notification(error_msg)
    

if __name__ == "__main__":
    client = TwicketsClient()
    client.run()
