import os
import requests
from datetime import datetime, timedelta, timezone
from collections import Counter

CORP_ID = 98834399
WEBHOOK_URL = os.environ["WEBHOOK_URL"]

HEADERS = {
"User-Agent": "DHDR Daily Report Bot"
}

CORP_LOGO = f"https://images.evetech.net/corporations/{CORP_ID}/logo"

def get_zkill(endpoint):
url = f"https://zkillboard.com/api/{endpoint}/corporationID/{CORP_ID}/"
r = requests.get(url, headers=HEADERS, timeout=30)
r.raise_for_status()
return r.json()

def get_killmail(killmail_id, kill_hash):
url = (
f"https://esi.evetech.net/latest/"
f"killmails/{killmail_id}/{kill_hash}/"
)

```
r = requests.get(url, headers=HEADERS, timeout=30)
r.raise_for_status()
return r.json()
```

def resolve_names(ids):
ids = list(set(i for i in ids if i))

```
if not ids:
    return {}

r = requests.post(
    "https://esi.evetech.net/latest/universe/names/",
    json=ids,
    headers=HEADERS,
    timeout=30
)

if r.status_code != 200:
    return {}

data = r.json()

return {
    item["id"]: item["name"]
    for item in data
}
```

def format_isk(value):
if value >= 1_000_000_000:
return f"{value/1_000_000_000:.2f} B"

```
if value >= 1_000_000:
    return f"{value/1_000_000:.2f} M"

return f"{value:,.0f}"
```

def get_recent_killmails(endpoint):
cutoff = datetime.now(timezone.utc) - timedelta(days=1)

```
results = []

for km in get_zkill(endpoint):

    try:
        detail = get_killmail(
            km["killmail_id"],
            km["zkb"]["hash"]
        )

        kill_time = datetime.strptime(
            detail["killmail_time"],
            "%Y-%m-%dT%H:%M:%SZ"
        ).replace(tzinfo=timezone.utc)

        if kill_time >= cutoff:
            results.append({
                "summary": km,
                "detail": detail
            })

    except Exception as e:
        print(
            f"Failed killmail {km['killmail_id']}: {e}"
        )

return results
```

print("Loading kills...")
kills = get_recent_killmails("kills")

print("Loading losses...")
losses = get_recent_killmails("losses")

all_character_ids = set()
all_ship_ids = set()

for collection in [kills, losses]:

```
for km in collection:

    victim = km["detail"]["victim"]

    all_character_ids.add(
        victim.get("character_id")
    )

    all_ship_ids.add(
        victim.get("ship_type_id")
    )

    for attacker in km["detail"].get(
        "attackers", []
    ):

        all_character_ids.add(
            attacker.get("character_id")
        )
```

character_names = resolve_names(
list(all_character_ids)
)

ship_names = resolve_names(
list(all_ship_ids)
)

isk_destroyed = sum(
k["summary"]["zkb"]["totalValue"]
for k in kills
)

isk_lost = sum(
l["summary"]["zkb"]["totalValue"]
for l in losses
)

efficiency = 100

if (isk_destroyed + isk_lost) > 0:
efficiency = (
isk_destroyed /
(isk_destroyed + isk_lost)
) * 100

largest_kill = max(
kills,
key=lambda x: x["summary"]["zkb"]["totalValue"],
default=None
)

largest_loss = max(
losses,
key=lambda x: x["summary"]["zkb"]["totalValue"],
default=None
)

final_blow_counter = Counter()
participation_counter = Counter()

for kill in kills:

```
for attacker in kill["detail"].get(
    "attackers", []
):

    if attacker.get(
        "corporation_id"
    ) != CORP_ID:
        continue

    char_id = attacker.get(
        "character_id"
    )

    if not char_id:
        continue

    participation_counter[
        char_id
    ] += 1

    if attacker.get("final_blow"):
        final_blow_counter[
            char_id
        ] += 1
```

top_final = (
final_blow_counter.most_common(1)[0]
if final_blow_counter
else None
)

top_active = (
participation_counter.most_common(1)[0]
if participation_counter
else None
)

embed = {
"title": "☠️ DHDR Daily PvP Report",
"description": "Last 24 Hours",
"thumbnail": {
"url": CORP_LOGO
},
"fields": [
{
"name": "Kills",
"value": str(len(kills)),
"inline": True
},
{
"name": "Losses",
"value": str(len(losses)),
"inline": True
},
{
"name": "Efficiency",
"value": f"{efficiency:.1f}%",
"inline": True
},
{
"name": "ISK Destroyed",
"value": format_isk(
isk_destroyed
),
"inline": True
},
{
"name": "ISK Lost",
"value": format_isk(
isk_lost
),
"inline": True
}
],
"footer": {
"text":
"Death's Head Division • zKillboard"
}
}

if largest_kill:

```
victim = largest_kill["detail"][
    "victim"
]

ship_name = ship_names.get(
    victim.get("ship_type_id"),
    "Unknown Ship"
)

victim_name = character_names.get(
    victim.get("character_id"),
    "Unknown Pilot"
)

embed["fields"].append({
    "name": "🏆 Biggest Kill",
    "value":
        f"{ship_name}\n"
        f"Victim: {victim_name}\n"
        f"{format_isk(largest_kill['summary']['zkb']['totalValue'])}",
    "inline": False
})
```

if largest_loss:

```
victim = largest_loss["detail"][
    "victim"
]

ship_name = ship_names.get(
    victim.get("ship_type_id"),
    "Unknown Ship"
)

pilot_name = character_names.get(
    victim.get("character_id"),
    "Unknown Pilot"
)

embed["fields"].append({
    "name": "💀 Biggest Loss",
    "value":
        f"{ship_name}\n"
        f"Pilot: {pilot_name}\n"
        f"{format_isk(largest_loss['summary']['zkb']['totalValue'])}",
    "inline": False
})
```

if top_final:

```
embed["fields"].append({
    "name": "🔥 Top Final Blow",
    "value":
        f"{character_names.get(top_final[0], 'Unknown')}\n"
        f"{top_final[1]} final blows",
    "inline": False
})
```

if top_active:

```
embed["fields"].append({
    "name": "⚔ Most Active Pilot",
    "value":
        f"{character_names.get(top_active[0], 'Unknown')}\n"
        f"{top_active[1]} participations",
    "inline": False
})
```

embed["fields"].append({
"name": "📈 zKillboard",
"value":
"https://zkillboard.com/corporation/98834399/",
"inline": False
})

payload = {
"embeds": [embed]
}

r = requests.post(
WEBHOOK_URL,
json=payload,
timeout=30
)

print(
"Discord status:",
r.status_code
)
