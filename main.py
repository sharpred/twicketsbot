""" module for holding and purchasing tickets on twickets """

from time import sleep
from datetime import datetime
import os
import logging
import http.client
import time
import random
import json
from helpers import NotTwoHundredStatusError, ProwlNoticationsClient

logging.captureWarnings(True)
logging.basicConfig(level=logging.DEBUG)

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
        try:
            logging.debug("Ensuring connection")
            self.conn.connect()
        except (http.client.HTTPException, OSError):
            logging.error("Ensuring connection error")
            self.conn.close()
            self.conn = http.client.HTTPSConnection(self.BASE_URL)
            self.conn.connect()

    def check_env_variables(self):
        """ check required keys all present """
        missing_env_variables = [
            key for key in self.REQUIRED_ENV_VARIABLES if not os.getenv(key)]
        if missing_env_variables:
            for key in missing_env_variables:
                logging.error("Environment variable %s is not set", key)
            raise RuntimeError("Missing required environment variables")
        else:
            print("All required keys are populated")

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
            logging.debug("authenticated %s",token)
            return token
        return None

    def check_event_availability(self):
        """ Check ticket availability """
        logging.debug("check_event_availability sock is none: %s",(self.conn.sock is None))
        self._ensure_connection()
        url = f"/services/g2/inventory/listings/{self.event_id}?api_key={self.api_key}"
        self.conn.request("GET", url, headers=self.headers)
        if self.conn.sock is not None:
            try:
                logging.debug("Get response")
                response = self.conn.getresponse()
                if response.status == 200:
                    result = json.loads(response.read().decode())
                    code = result.get("responseCode")
                    clock_val = result.get("clock")
                    items = result.get("responseData")
                    logging.debug("check availability code %s, clock %s, tickets %s",code, clock_val, len(items))
                    return items
                raise NotTwoHundredStatusError(f"check_event_availability status: {response.status}")
            except http.client.ResponseNotReady:
                pass
            except http.client.HTTPException:
                self.conn.close()
        return []
    
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
            
            while True:
                time_delay = round(random.uniform(self.MIN_TIME,self.MAX_TIME))
                now = datetime.now()
                try:
                    logging.debug("Cycle %s at %s with %s seconds delay",count,now.strftime("%H:%M:%S"),time_delay)
                    items = self.check_event_availability()
                    backoff = 0
                    attempts = 1
                    count +=1
                    if items:
                        for item in items:
                            id = str(items['id']).split('@')[1]
                            if id not in notified_ids:
                                url = f"https://www.twickets.live/app/block/{id},1"
                                self.prowl.send_notification(f"Check {url}")
                                notified_ids.add(id)
                                self.save_notified_ids(notified_ids)
                    SLEEP_INTERVAL = time_delay + (attempts*backoff)
                    sleep(SLEEP_INTERVAL)
                except NotTwoHundredStatusError:
                    logging.debug("** Restarting **")
                    items = None
                    count =1
                    backoff = random.uniform(300,500) # need a big delay if you get a 403
                    SLEEP_INTERVAL = time_delay + (backoff)
                    logging.debug("Sleeping for %s", SLEEP_INTERVAL)
                    self.conn.close()
                    sleep(SLEEP_INTERVAL)
                    token = self.authenticate()
                    if token is None:
                        raise RuntimeError("Authentication failed for some reason")
        except KeyboardInterrupt:
            QUIT_MESSAGE = "User interrupted connection with ctrl-C on cycle %s"
            logging.debug(QUIT_MESSAGE, count)
            self.save_notified_ids(notified_ids)
        except Exception as e:
            self.save_notified_ids(notified_ids)
            logging.error("Cycle %s Caught exception of type %s",count, type(e).__name__)
            error_msg = f"Cycle {count} Caught exception {e}"
            self.prowl.send_notification(error_msg)
    

if __name__ == "__main__":
    client = TwicketsClient()
    client.run()
