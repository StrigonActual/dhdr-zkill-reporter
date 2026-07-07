import os
import requests
from datetime import datetime, timedelta, timezone
from collections import Counter

CORP_ID = 98838034
WEBHOOK_URL = os.environ["WEBHOOK_URL"]
HEADERS = {"User-Agent": "FOSFO Weekly Report Bot"}


def get_zkill(endpoint):
    r = requests.get(
        f"https://zkillboard.com/api/{endpoint}/corporationID/{CORP_ID}/",
        headers=HEADERS,
        timeout=30,
    )
    r.raise_for_status()
    return r.json()


def get_killmail(killmail_id, kill_hash):
    r = requests.get(
        f"https://esi.evetech.net/latest/killmails/{killmail_id}/{kill_hash}/",
        headers=HEADERS,
        timeout=30,
    )
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


cutoff = datetime.now(timezone.utc) - timedelta(days=7)

kills = []
losses = []

for endpoint, target in [("kills", kills), ("losses", losses)]:
    for km in get_zkill(endpoint):
        try:
            detail = get_killmail(km["killmail_id"], km["zkb"]["hash"])

            t = datetime.strptime(
                detail["killmail_time"],
                "%Y-%m-%dT%H:%M:%SZ"
            ).replace(tzinfo=timezone.utc)

            if t >= cutoff:
                target.append({"summary": km, "detail": detail})
        except Exception as e:
            print("Skipped:", e)

participation = Counter()
final_blows = Counter()
character_ids = set()

for kill in kills:
    for attacker in kill["detail"].get("attackers", []):
        if attacker.get("corporation_id") != CORP_ID:
            continue

        cid = attacker.get("character_id")
        if not cid:
            continue

        character_ids.add(cid)
        participation[cid] += 1

        if attacker.get("final_blow"):
            final_blows[cid] += 1

names = resolve_names(character_ids)

isk_destroyed = sum(k["summary"]["zkb"]["totalValue"] for k in kills)
isk_lost = sum(l["summary"]["zkb"]["totalValue"] for l in losses)

efficiency = 100.0
if (isk_destroyed + isk_lost) > 0:
    efficiency = isk_destroyed / (isk_destroyed + isk_lost) * 100

top_participation = "\n".join(
    f"{i+1}. {names.get(cid, str(cid))} — {count}"
    for i, (cid, count) in enumerate(participation.most_common(10))
)

top_finals = "\n".join(
    f"{i+1}. {names.get(cid, str(cid))} — {count}"
    for i, (cid, count) in enumerate(final_blows.most_common(5))
)

embed = {
    "title": "🏆 The Ministry of Ungentlemanly Warfare Weekly Leaderboard",
    "description": "Last 7 Days",
    "fields": [
        {
            "name": "Top Kills",
            "value": top_participation or "No data",
            "inline": False,
        },
        {
            "name": "🔥 Top Final Blows",
            "value": top_finals or "No data",
            "inline": False,
        },
        {
            "name": "Weekly Statistics",
            "value": (
                f"Kills: {len(kills)}\n"
                f"Losses: {len(losses)}\n\n"
                f"ISK Destroyed: {format_isk(isk_destroyed)}\n"
                f"ISK Lost: {format_isk(isk_lost)}\n\n"
                f"Efficiency: {efficiency:.1f}%"
            ),
            "inline": False,
        },
    ],
}

r = requests.post(WEBHOOK_URL, json={"embeds": [embed]}, timeout=30)
print("Discord status:", r.status_code)
