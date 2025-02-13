import http.client
import json
import os

conn = http.client.HTTPSConnection("www.twickets.live")
payload = json.dumps({
            "login": os.getenv("TWICKETS_EMAIL"),
            "password": os.getenv("TWICKETS_PASSWORD"),
            "accountType": "U",
        })
headers = {
  'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:101.0) Gecko/20100101 Firefox/101.0',
  'Accept-Encoding': 'gzip, deflate',
  'Accept': '*/*',
  'Connection': 'keep-alive',
  'Content-Length': '98',
  'Cookie': f'clientId={os.getenv("TWICKETS_CLIENT_ID")}; locale=en_GB; territory=GB',
  'Content-Type': 'application/json'
}
conn.request("POST", "/services/auth/login?api_key=83d6ec0c-54bb-4da3-b2a1-f3cb47b984f1", payload, headers)
res = conn.getresponse()
data = res.read()
print(data.decode("utf-8"))