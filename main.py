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
from typing import Optional
from helpers import NotTwoHundredStatusError, ProwlNoticationsClient
from telegram import TelegramBotClient
from ticketalertresponse import TicketAlertResponse

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
        "PROWL_API_KEY",
        "TWICKETS_EVENT_NAME"
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
        self.event_name = os.getenv("TWICKETS_EVENT_NAME")
        
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
                logging.warning(f"DNS resolution failed: {ge}. Retrying in {self.BASE_DELAY * (2 ** retries)}s...")
            except (http.client.HTTPException, OSError):
                logging.warning("Connection error")
                #TODO wrap self.conn.close in method
                self.conn.close()
                self.conn = http.client.HTTPSConnection(self.BASE_URL)
                self.conn.connect()
            retries += 1
            time.sleep(self.BASE_DELAY * (2 ** retries))
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

    def check_event_availability(self) -> Optional[TicketAlertResponse]:
        """ Check ticket availability """
        logging.debug("Connection socket is none: %s",(self.conn.sock is None))
        self._ensure_connection()
        url = f"/services/g2/inventory/listings/{self.event_id}?api_key={self.api_key}"
        if self.conn.sock is None:
            # No valid connection, so we return None.
            return None
        try:
            logging.debug(f"Get response event: {self.event_id}")
            self.conn.request("GET", url, headers=self.headers)
            response = self.conn.getresponse()
            if response.status == 200:
                result = json.loads(response.read().decode())
                # Convert the response into a TicketAlertResponse object
                ticket_alert_response = TicketAlertResponse.from_dict(result)
                logging.info(f"Response code {ticket_alert_response.response_code}, clock {ticket_alert_response.clock}, has valid tickets {ticket_alert_response.has_valid_tickets}")
                return ticket_alert_response
            raise NotTwoHundredStatusError(f"Check availability status: {response.status}")
        except http.client.ResponseNotReady:
            logging.warning("http.client.ResponseNotReady exception")
            pass
            return None
        except http.client.HTTPException as e:
            self.conn.close()
            raise e
        

    def process_ticket_alert(self, ticket_alert_response: TicketAlertResponse, notified_ids) -> bool:
        """Process and notify about tickets from a TicketAlertResponse."""
        new_notification_sent = False  # Track if any new notification is sent

        for response_datum in ticket_alert_response.response_data:
            if response_datum.is_required_ticket == True:

                id = response_datum.url_id  # Extract url_id directly
        
                if id not in notified_ids:
                    url = f"https://{self.BASE_URL}/app/block/{id},1"
                    found_str = f"found {self.event_name} tickets {url}"
                    self.prowl.send_notification(found_str)
                    logging.info(found_str)
                    self.teleclient.send_notification("Ticket Alert", found_str)
                    notified_ids.add(id)
                    self.save_notified_ids(notified_ids)
                    new_notification_sent = True  # Set to True since a new notification was sent
                else:
                    logging.debug(f"Ignoring repeat notification {id}")
            else:
                logging.info(f"Ignoring listing for {response_datum.pricing.prices[0].label}")

        return new_notification_sent


    def run(self):
        """ run da ting """
        try:
            logging.debug(f"Checking {self.event_name} availability")
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
            blocked_requests = 0
            while True:
                now = datetime.now()
                tomorrow = now + timedelta(days=1)
                time_delay = round(random.uniform(self.MIN_TIME,self.MAX_TIME))
                auth_time_delay = round(random.uniform(180,360)) # need a bigger delay if you get a 403    
                
                try:
                    logging.debug("Check cycle %s at %s with %s seconds delay",count,now.strftime("%d/%m %H:%M:%S"),time_delay)
                    ticket_alert = self.check_event_availability()
                    #reset everything if ticket alert returned
                    backoff = 0
                    attempts = 0
                    count +=1
                    new_notification_sent = False
                    if isinstance(ticket_alert, TicketAlertResponse):
                        if ticket_alert.has_valid_tickets == True:
                            new_notification_sent = self.process_ticket_alert(ticket_alert, notified_ids)
                            #might as well wait a bit longer if there is an active alert
                            if new_notification_sent == True:
                                SLEEP_INTERVAL = auth_time_delay
                                logging.info(f"Pausing for {SLEEP_INTERVAL} as notification sent")
                    else:
                        raise TypeError(f"Unexpected type for ticket alert: {type(ticket_alert)} ")
                    SLEEP_INTERVAL = time_delay + (backoff)
                    sleep(SLEEP_INTERVAL)
                except NotTwoHundredStatusError as error_msg:
                    blocked_requests += 1
                    logging.info("Check cycle %s, blocked requests: %s",count,blocked_requests)
                    logging.info(f"{error_msg} %s. Attempt {attempts}",now.strftime("%H:%M:%S"))
                    ticket_alert = None
                    if attempts > self.MAX_RETRIES:
                        #give up
                        self.save_notified_ids(notified_ids)
                        exit_error_message = "Exiting after five failed login attempts"
                        self.prowl.send_notification(exit_error_message)
                        logging.error(exit_error_message)
                        self.conn.close()
                        #If running as a k8s deployment the pod will just respawn on exit and you will still be in a 403 shutout timeframe, so sleep before exit
                        SLEEP_INTERVAL = auth_time_delay * (2 ** attempts)
                        new_time = now + timedelta(seconds=SLEEP_INTERVAL)
                        logging.error("Exiting due to repeated 403 errors at %s", new_time.strftime("%H:%M:%S"))
                        sleep(SLEEP_INTERVAL)
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
            logging.error(f"Cycle {count} {e} ")
            exception_error_msg = f"Cycle {count} Caught exception {e}"
            self.conn.close()
            self.prowl.send_notification(exception_error_msg)
    

if __name__ == "__main__":
    client = TwicketsClient()
    client.run()
