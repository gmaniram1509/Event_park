import requests

PARKING_BASE = 'http://SmartParking-env.eba-dwhzmncq.us-east-1.elasticbeanstalk.com'

def get_nearby_parking(latitude, longitude, radius=5):
    try:
        response = requests.get(
            f"{PARKING_BASE}/api/parking-lots/nearby",
            params={'lat': latitude, 'long': longitude, 'radius': radius},
            timeout=5
        )
        if response.status_code == 200:
            return response.json(), None
        return None, f"Error: {response.status_code}"
    except Exception as e:
        return None, str(e)

def get_parking_stats():
    try:
        response = requests.get(f"{PARKING_BASE}/api/parking-lots/stats", timeout=5)
        if response.status_code == 200:
            return response.json(), None
        return None, f"Error: {response.status_code}"
    except Exception as e:
        return None, str(e)
