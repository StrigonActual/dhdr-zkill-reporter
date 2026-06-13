import os
import requests
from datetime import datetime, timedelta, timezone
from collections import Counter

CORP_ID = 98834399
WEBHOOK_URL = os.environ["WEBHOOK_URL"]

HEADERS = {"User-Agent": "DHDR Daily Report Bot"}
CORP_LOGO = f"https://images.evetech.net/corporations/{CORP_ID}/logo"


def get_zkill(endpoint):
    url = f"https://zkillboard.com/api/{endpoint}/corporationID/{CORP_ID}/"
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()


def get_killmail(killmail_id, kill_hash):
    url = f"https://esi.evetech.net/latest/killmails/{killmail_id}/{kill_hash}/"
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return r.json()


def resolve_names(ids):
    ids = [i for i in set(ids) if i]
    if not ids:
        return {}

    r = requests.post(
        "https://esi.evetech.net/latest/universe/names/",
        json=ids,
        headers=HEADERS,
        timeout=30,
    )

    if r.status_code != 200:
        return {}

    return {item["id"]: item["name"] for item in r.json()}


def format_isk(value):
    if value >= 1_000_000_000:
        return f"{value/1_000_000_000:.2f} B"
    if value >= 1_000_000:
        return f"{value/1_000_000:.2f} M"
    return f"{value:,.0f}"


def get_recent(endpoint, hours=24):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    results = []

    for km in get_zkill(endpoint):
        try:
            detail = get_killmail(km["killmail_id"], km["zkb"]["hash"])

            kill_time = datetime.strptime(
                detail["killmail_time"],
                "%Y-%m-%dT%H:%M:%SZ"
            ).replace(tzinfo=timezone.utc)

            if kill_time >= cutoff:
                results.append({
                    "summary": km,
                    "detail": detail
                })

        except Exception as ex:
            print(f"Failed {km['killmail_id']}: {ex}")

    return results


kills = get_recent("kills")
losses = get_recent("losses")

all_character_ids = set()
all_ship_ids = set()

for group in [kills, losses]:
    for km in group:
        victim = km["detail"]["victim"]

        all_character_ids.add(victim.get("character_id"))
        all_ship_ids.add(victim.get("ship_type_id"))

        for attacker in km["detail"].get("attackers", []):
            all_character_ids.add(attacker.get("character_id"))

character_names = resolve_names(all_character_ids)
ship_names = resolve_names(all_ship_ids)

isk_destroyed = sum(k["summary"]["zkb"]["totalValue"] for k in kills)
isk_lost = sum(l["summary"]["zkb"]["totalValue"] for l in losses)

efficiency = 100.0
if (isk_destroyed + isk_lost) > 0:
    efficiency = (isk_destroyed / (isk_destroyed + isk_lost)) * 100

largest_kill = max(kills, key=lambda x: x["summary"]["zkb"]["totalValue"], default=None)
largest_loss = max(losses, key=lambda x: x["summary"]["zkb"]["totalValue"], default=None)

final_blows = Counter()
participation = Counter()

for kill in kills:
    for attacker in kill["detail"].get("attackers", []):
        if attacker.get("corporation_id") != CORP_ID:
            continue

        char_id = attacker.get("character_id")
        if not char_id:
            continue

        participation[char_id] += 1

        if attacker.get("final_blow"):
            final_blows[char_id] += 1

embed = {
    "title": "☠️ DHDR Daily PvP Report",
    "description": "Last 24 Hours",
    "thumbnail": {"url": CORP_LOGO},
    "fields": [
        {"name": "Kills", "value": str(len(kills)), "inline": True},
        {"name": "Losses", "value": str(len(losses)), "inline": True},
        {"name": "Efficiency", "value": f"{efficiency:.1f}%", "inline": True},
        {"name": "ISK Destroyed", "value": format_isk(isk_destroyed), "inline": True},
        {"name": "ISK Lost", "value": format_isk(isk_lost), "inline": True},
    ],
    "footer": {"text": "Administrative Atrocities • zKillboard"}
}

if largest_kill:
    victim = largest_kill["detail"]["victim"]
    embed["fields"].append({
        "name": "🏆 Biggest Kill",
        "value": (
            f"{ship_names.get(victim.get('ship_type_id'),'Unknown Ship')}\n"
            f"Victim: {character_names.get(victim.get('character_id'),'Unknown Pilot')}\n"
            f"{format_isk(largest_kill['summary']['zkb']['totalValue'])}"
        ),
        "inline": False
    })

if largest_loss:
    victim = largest_loss["detail"]["victim"]
    embed["fields"].append({
        "name": "💀 Biggest Loss",
        "value": (
            f"{ship_names.get(victim.get('ship_type_id'),'Unknown Ship')}\n"
            f"Pilot: {character_names.get(victim.get('character_id'),'Unknown Pilot')}\n"
            f"{format_isk(largest_loss['summary']['zkb']['totalValue'])}"
        ),
        "inline": False
    })

if final_blows:
    cid, count = final_blows.most_common(1)[0]
    embed["fields"].append({
        "name": "🔥 Top Final Blow",
        "value": f"{character_names.get(cid,'Unknown')}\n{count} final blows",
        "inline": False
    })

if participation:
    cid, count = participation.most_common(1)[0]
    embed["fields"].append({
        "name": "⚔ Most Active Pilot",
        "value": f"{character_names.get(cid,'Unknown')}\n{count} participations",
        "inline": False
    })

embed["fields"].append({
    "name": "📈 zKillboard",
    "value": "https://zkillboard.com/corporation/98834399/",
    "inline": False
})

requests.post(WEBHOOK_URL, json={"embeds": [embed]}, timeout=30)
print("Report posted")
