import requests
import json

url = "https://zkillboard.com/api/kills/corporationID/98834399/page/1/"

r = requests.get(
    url,
    headers={
        "User-Agent": "DHDR Discord Bot"
    }
)

print("Status:", r.status_code)

data = r.json()

print("Records:", len(data))

if len(data) > 0:
    print(json.dumps(data[0], indent=2))
