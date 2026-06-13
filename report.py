import requests

zkill = requests.get(
    "https://zkillboard.com/api/kills/corporationID/98834399/"
).json()

print("Records:", len(zkill))

first = zkill[0]
last = zkill[-1]

for label, km in [("Newest", first), ("Oldest", last)]:

    killmail_id = km["killmail_id"]
    hash_value = km["zkb"]["hash"]

    esi = requests.get(
        f"https://esi.evetech.net/latest/killmails/{killmail_id}/{hash_value}/"
    ).json()

    print(label, esi["killmail_time"])
