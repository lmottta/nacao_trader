import requests
import json

url = "http://127.0.0.1:8001/api/v1/signals"
data = {
    "asset": "PETR4.SA",
    "timeframe": "15m"
}

try:
    response = requests.post(url, json=data)
    print(f"Status Code: {response.status_code}")
    try:
        print("Response JSON:")
        print(json.dumps(response.json(), indent=2))
    except json.JSONDecodeError:
        print("Response Text:")
        print(response.text)
except requests.exceptions.RequestException as e:
    print(f"An error occurred: {e}")