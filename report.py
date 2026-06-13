import requests
import json

url = "https://zkillboard.com/api/kills/corporationID/98834399/"

r = requests.get(url)

print("Status:", r.status_code)

data = r.json()

print("Records:", len(data))

print(json.dumps(data[0], indent=2)[:3000])
