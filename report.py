import os
import requests

WEBHOOK_URL = os.environ["WEBHOOK_URL"]

payload = {
    "embeds": [
        {
            "title": "DHDR Test Report",
            "description": "Python formatting is working correctly.",
            "fields": [
                {
                    "name": "Status",
                    "value": "Success",
                    "inline": False
                }
            ]
        }
    ]
}

response = requests.post(
    WEBHOOK_URL,
    json=payload,
    timeout=30
)

print("Discord status:", response.status_code)
