"""
EventPark API Client — wraps all calls to the FastAPI backend.
"""
import requests
from django.conf import settings

API_BASE = getattr(settings, 'EVENTPARK_API_BASE', 'http://localhost:8001/api/v1')
API_KEY = getattr(settings, 'EVENTPARK_API_KEY', '')


def _headers():
    h = {'Content-Type': 'application/json'}
    if API_KEY:
        h['X-API-Key'] = API_KEY
    return h


def _get(path, params=None):
    try:
        r = requests.get(f'{API_BASE}{path}', params=params, headers=_headers(), timeout=8)
        r.raise_for_status()
        return r.json(), None
    except requests.exceptions.ConnectionError:
        return None, 'Cannot connect to EventPark API. Make sure it is running on port 8001.'
    except requests.exceptions.HTTPError as e:
        return None, f'API error: {e.response.status_code}'
    except Exception as e:
        return None, str(e)


def _post(path, data):
    try:
        r = requests.post(f'{API_BASE}{path}', json=data, headers=_headers(), timeout=8)
        r.raise_for_status()
        return r.json(), None
    except requests.exceptions.ConnectionError:
        return None, 'Cannot connect to EventPark API.'
    except requests.exceptions.HTTPError as e:
        try:
            detail = e.response.json().get('detail', str(e))
        except Exception:
            detail = str(e)
        return None, detail
    except Exception as e:
        return None, str(e)


def _put(path, data):
    try:
        r = requests.put(f'{API_BASE}{path}', json=data, headers=_headers(), timeout=8)
        r.raise_for_status()
        return r.json(), None
    except requests.exceptions.ConnectionError:
        return None, 'Cannot connect to EventPark API.'
    except requests.exceptions.HTTPError as e:
        try:
            detail = e.response.json().get('detail', str(e))
        except Exception:
            detail = str(e)
        return None, detail
    except Exception as e:
        return None, str(e)


def _delete(path):
    try:
        r = requests.delete(f'{API_BASE}{path}', headers=_headers(), timeout=8)
        r.raise_for_status()
        return True, None
    except requests.exceptions.ConnectionError:
        return False, 'Cannot connect to EventPark API.'
    except requests.exceptions.HTTPError as e:
        return False, f'API error: {e.response.status_code}'
    except Exception as e:
        return False, str(e)


# ── Events ──────────────────────────────────────────────────────────────────

def list_events(page=1, page_size=12, category=None, city=None, is_free=None,
                is_outdoor=None, status=None):
    params = {'page': page, 'page_size': page_size}
    if category:
        params['category'] = category
    if city:
        params['city'] = city
    if is_free is not None:
        params['is_free'] = is_free
    if is_outdoor is not None:
        params['is_outdoor'] = is_outdoor
    if status:
        params['status'] = status
    return _get('/events', params)


def search_events(q, page=1, page_size=12):
    return _get('/events/search', {'q': q, 'page': page, 'page_size': page_size})


def nearby_events(latitude, longitude, radius=5000):
    return _get('/events/nearby', {'latitude': latitude, 'longitude': longitude, 'radius': radius})


def get_event(event_id):
    return _get(f'/events/{event_id}')


def get_crowd(event_id):
    return _get(f'/events/{event_id}/crowd')


def create_event(data):
    return _post('/events', data)


def update_event(event_id, data):
    return _put(f'/events/{event_id}', data)


def delete_event(event_id):
    return _delete(f'/events/{event_id}')


# ── Venues ───────────────────────────────────────────────────────────────────

def list_venues(page=1, page_size=12):
    return _get('/venues', {'page': page, 'page_size': page_size})


def search_venues(q, page=1, page_size=12):
    return _get('/venues/search', {'q': q, 'page': page, 'page_size': page_size})


def get_venue(venue_id):
    return _get(f'/venues/{venue_id}')


def get_venue_events(venue_id):
    return _get(f'/venues/{venue_id}/events')


def create_venue(data):
    return _post('/venues', data)


def update_venue(venue_id, data):
    return _put(f'/venues/{venue_id}', data)


def delete_venue(venue_id):
    return _delete(f'/venues/{venue_id}')


# ── Health ────────────────────────────────────────────────────────────────────

def health_check():
    return _get('/health')
