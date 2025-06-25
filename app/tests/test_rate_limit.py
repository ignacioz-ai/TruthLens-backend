import requests
import time
from app.core.config import settings

API_URL = f"{settings.TEST_API_BASE_URL}/api/analyze"
headers = {"Content-Type": "application/json"}
payload = {
    "input_text": "The government announced a new climate policy today."
}

for i in range(6):
    print(f"\nRequest #{i + 1}")
    response = requests.post(API_URL, json=payload, headers=headers)

    print("Status Code:", response.status_code)
    if response.status_code == 200:
        print("✅ Response OK")
        print(response.json())
    elif response.status_code == 429:
        print("❌ Rate limit exceeded as expected.")
        print(response.text)
    else:
        print("⚠️ Unexpected response:")
        print(response.text)

    # Optional: wait a bit between requests to simulate user behavior
    time.sleep(1)