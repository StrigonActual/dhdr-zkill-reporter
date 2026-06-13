import requests
import json

url = "https://zkillboard.com/api/kills/corporationID/98834399/"

r = requests.get(url)

print("Status:", r.status_code)

data = r.json()

print("Records:", len(data))

print("\nFIELDS:")
print(list(data[0].keys()))

print("\nFIRST RECORD:")
print(json.dumps(data[0], indent=2))
