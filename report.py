import requests
import json

zkill = requests.get(
    "https://zkillboard.com/api/kills/corporationID/98834399/"
).json()

first = zkill[0]

killmail_id = first["killmail_id"]
hash_value = first["zkb"]["hash"]

print("Killmail ID:", killmail_id)

esi_url = (
    f"https://esi.evetech.net/latest/"
    f"killmails/{killmail_id}/{hash_value}/"
)

esi = requests.get(esi_url)

print("ESI Status:", esi.status_code)

data = esi.json()

print(json.dumps(data, indent=2)[:4000])
