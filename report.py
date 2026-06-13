import os
import requests
from datetime import datetime, timedelta, timezone
from collections import Counter

CORP_ID = 98834399
WEBHOOK_URL = os.environ["WEBHOOK_URL"]

HEADERS = {
    "User-Agent": "DHDR Daily Report Bot"
}


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

    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()


def get_recent_killmails(endpoint):
    cutoff = datetime.now(timezone.utc) - timedelta(days=1)

    results = []

    for km in get_zkill(endpoint):

        try:
            killmail = get_killmail(
                km["killmail_id"],
                km["zkb"]["hash"]
            )

            kill_time = datetime.strptime(
                killmail["killmail_time"],
                "%Y-%m-%dT%H:%M:%SZ"
            ).replace(tzinfo=timezone.utc)

            if kill_time >= cutoff:
                results.append({
                    "summary": km,
                    "detail": killmail
                })

        except Exception as e:
            print(
                f"Failed killmail {km['killmail_id']}: {e}"
            )

    return results


print("Loading kills...")
kills = get_recent_killmails("kills")

print("Loading losses...")
losses = get_recent_killmails("losses")

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
active_counter = Counter()

for kill in kills:

    detail = kill["detail"]

    for attacker in detail.get("attackers", []):

        pilot = attacker.get("character_id")

        if not pilot:
            continue

        active_counter[pilot] += 1

        if attacker.get("final_blow"):
            final_blow_counter[pilot] += 1

top_killer = (
    final_blow_counter.most_common(1)[0]
    if final_blow_counter
    else None
)

most_active = (
    active_counter.most_common(1)[0]
    if active_counter
    else None
)

embed = {
    "title": "☠️ DHDR Daily PvP Report",
    "description": "Last 24 Hours",
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
            "value": f"{isk_destroyed/1e9:.2f} B",
            "inline": True
        },
        {
            "name": "ISK Lost",
            "value": f"{isk_lost/1e9:.2f} B",
            "inline": True
        }
    ],
    "footer": {
        "text": "Death's Head Division"
    }
}

if largest_kill:
    embed["fields"].append({
        "name": "🏆 Biggest Kill",
        "value": f"{largest_kill['summary']['zkb']['totalValue']/1e9:.2f} B",
        "inline": False
    })

if largest_loss:
    embed["fields"].append({
        "name": "💀 Biggest Loss",
        "value": f"{largest_loss['summary']['zkb']['totalValue']/1e9:.2f} B",
        "inline": False
    })

if top_killer:
    embed["fields"].append({
        "name": "🔥 Top Final Blow",
        "value": (
            f"Character ID {top_killer[0]}\n"
            f"{top_killer[1]} final blows"
        ),
        "inline": False
    })

if most_active:
    embed["fields"].append({
        "name": "⚔ Most Active Pilot",
        "value": (
            f"Character ID {most_active[0]}\n"
            f"{most_active[1]} killmails"
        ),
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

print("Discord status:", r.status_code)
print("Done")
