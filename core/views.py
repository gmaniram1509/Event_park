from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from functools import wraps
import json
from . import api_client as api
from . import parking_client as parking


# ══════════════════════════════════════════════════════════════
# LOGIN REQUIRED DECORATOR
# ══════════════════════════════════════════════════════════════

def login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        token = request.session.get('access_token')
        if not token:
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


# ══════════════════════════════════════════════════════════════
# AUTHENTICATION VIEWS — AWS Cognito
# ══════════════════════════════════════════════════════════════

def login_view(request):
    if request.session.get('access_token'):
        return redirect('home')
    return render(request, 'core/login.html', {
        'cognito_client_id': getattr(settings, 'COGNITO_CLIENT_ID', '6ejksvkfvi81ong4ev63nll5a3'),
        'cognito_region':    getattr(settings, 'COGNITO_REGION', 'us-east-1'),
    })


def register_view(request):
    if request.session.get('access_token'):
        return redirect('home')
    return render(request, 'core/register.html', {
        'cognito_client_id': getattr(settings, 'COGNITO_CLIENT_ID', '6ejksvkfvi81ong4ev63nll5a3'),
        'cognito_region':    getattr(settings, 'COGNITO_REGION', 'us-east-1'),
    })


@csrf_exempt
def save_token(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            request.session['access_token']  = data.get('access_token')
            request.session['id_token']      = data.get('id_token')
            request.session['refresh_token'] = data.get('refresh_token')
            request.session['user_email']    = data.get('user_email')
            return JsonResponse({'status': 'ok'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    return JsonResponse({'status': 'error'}, status=405)


def logout_view(request):
    request.session.flush()
    messages.success(request, 'You have been logged out.')
    return redirect('login')


# ══════════════════════════════════════════════════════════════
# MAIN VIEWS — All protected with @login_required
# ══════════════════════════════════════════════════════════════

@login_required
def home(request):
    events_data, err = api.list_events(page_size=6, status='published')
    venues_data, verr = api.list_venues(page_size=4)
    health, _ = api.health_check()
    return render(request, 'core/home.html', {
        'events': events_data.get('events', []) if events_data else [],
        'venues': venues_data.get('venues', []) if venues_data else [],
        'api_status': health.get('status') if health else 'offline',
        'error': err,
        'user_email': request.session.get('user_email', ''),
    })


@login_required
def event_list(request):
    page = int(request.GET.get('page', 1))
    q = request.GET.get('q', '').strip()
    category = request.GET.get('category', '')
    city = request.GET.get('city', '')
    is_free = request.GET.get('is_free', '')
    is_outdoor = request.GET.get('is_outdoor', '')
    status_filter = request.GET.get('status', '')

    if q:
        data, err = api.search_events(q, page=page)
    else:
        data, err = api.list_events(
            page=page, page_size=12,
            category=category or None,
            city=city or None,
            is_free=True if is_free == 'true' else (False if is_free == 'false' else None),
            is_outdoor=True if is_outdoor == 'true' else (False if is_outdoor == 'false' else None),
            status=status_filter or None,
        )

    events = data.get('events', []) if data else []
    total = data.get('total', 0) if data else 0
    total_pages = (total + 11) // 12

    return render(request, 'core/event_list.html', {
        'events': events, 'total': total, 'page': page, 'total_pages': total_pages,
        'q': q, 'category': category, 'city': city, 'is_free': is_free,
        'is_outdoor': is_outdoor, 'status_filter': status_filter,
        'categories': ['music', 'sports', 'comedy', 'food', 'arts', 'tech', 'business', 'health', 'education', 'other'],
        'error': err,
        'user_email': request.session.get('user_email', ''),
    })


@login_required
def event_detail(request, event_id):
    event, err = api.get_event(event_id)
    crowd, _ = api.get_crowd(event_id) if event else (None, None)
    tags = []
    if event and event.get('tags'):
        tags = [t.strip() for t in event['tags'].split(',')]

    # Get nearby parking from classmate Smart Parking API
    parking_lots = []
    parking_stats = None
    if event and event.get('venue'):
        venue = event['venue']
        lat = venue.get('latitude')
        lng = venue.get('longitude')
        # Fix longitude sign if positive (Dublin is west = negative)
        if lng and lng > 0:
            lng = -lng
        if lat and lng:
            parking_data, _ = parking.get_nearby_parking(lat, lng, radius=10)
            if parking_data:
                parking_lots = parking_data if isinstance(parking_data, list) else []
            stats, _ = parking.get_parking_stats()
            parking_stats = stats
    # Fallback to Dublin city center if no parking found
    if not parking_lots:
        parking_data, _ = parking.get_nearby_parking(53.3498, -6.2603, radius=10)
        if parking_data:
            parking_lots = parking_data if isinstance(parking_data, list) else []
        if not parking_stats:
            stats, _ = parking.get_parking_stats()
            parking_stats = stats

    return render(request, 'core/event_detail.html', {
        'event': event,
        'crowd': crowd,
        'error': err,
        'tags': tags,
        'GOOGLE_MAPS_API_KEY': settings.GOOGLE_MAPS_API_KEY,
        'user_email': request.session.get('user_email', ''),
        'parking_lots': parking_lots,
        'parking_stats': parking_stats,
    })


@login_required
def event_create(request):
    venues_data, _ = api.list_venues(page_size=100)
    venues = venues_data.get('venues', []) if venues_data else []
    if request.method == 'POST':
        data = {
            'title': request.POST.get('title'),
            'description': request.POST.get('description'),
            'category': request.POST.get('category', 'other'),
            'venue_id': request.POST.get('venue_id'),
            'start_date': request.POST.get('start_date'),
            'end_date': request.POST.get('end_date') or None,
            'max_capacity': int(request.POST.get('max_capacity')) if request.POST.get('max_capacity') else None,
            'tickets_sold': int(request.POST.get('tickets_sold', 0)),
            'is_free': request.POST.get('is_free') == 'on',
            'price_min': float(request.POST.get('price_min')) if request.POST.get('price_min') else None,
            'price_max': float(request.POST.get('price_max')) if request.POST.get('price_max') else None,
            'currency': request.POST.get('currency', 'EUR'),
            'organizer_name': request.POST.get('organizer_name') or None,
            'organizer_email': request.POST.get('organizer_email') or None,
            'image_url': request.POST.get('image_url') or None,
            'ticket_url': request.POST.get('ticket_url') or None,
            'tags': request.POST.get('tags') or None,
            'is_outdoor': request.POST.get('is_outdoor') == 'on',
        }
        result, err = api.create_event(data)
        if result:
            messages.success(request, f'Event "{result["title"]}" created!')
            return redirect('event_detail', event_id=result['id'])
        messages.error(request, f'Error: {err}')
    return render(request, 'core/event_form.html', {
        'venues': venues,
        'categories': ['music', 'sports', 'comedy', 'food', 'arts', 'tech', 'business', 'health', 'education', 'other'],
        'form_title': 'Create Event', 'action': 'create',
        'user_email': request.session.get('user_email', ''),
    })


@login_required
def event_edit(request, event_id):
    event, err = api.get_event(event_id)
    if not event:
        messages.error(request, f'Event not found: {err}')
        return redirect('event_list')
    venues_data, _ = api.list_venues(page_size=100)
    venues = venues_data.get('venues', []) if venues_data else []
    if request.method == 'POST':
        data = {
            'title': request.POST.get('title'),
            'description': request.POST.get('description'),
            'category': request.POST.get('category'),
            'status': request.POST.get('status'),
            'venue_id': request.POST.get('venue_id'),
            'start_date': request.POST.get('start_date'),
            'end_date': request.POST.get('end_date') or None,
            'max_capacity': int(request.POST.get('max_capacity')) if request.POST.get('max_capacity') else None,
            'tickets_sold': int(request.POST.get('tickets_sold', 0)),
            'is_free': request.POST.get('is_free') == 'on',
            'price_min': float(request.POST.get('price_min')) if request.POST.get('price_min') else None,
            'price_max': float(request.POST.get('price_max')) if request.POST.get('price_max') else None,
            'currency': request.POST.get('currency', 'EUR'),
            'organizer_name': request.POST.get('organizer_name') or None,
            'organizer_email': request.POST.get('organizer_email') or None,
            'image_url': request.POST.get('image_url') or None,
            'ticket_url': request.POST.get('ticket_url') or None,
            'tags': request.POST.get('tags') or None,
            'is_outdoor': request.POST.get('is_outdoor') == 'on',
        }
        result, err = api.update_event(event_id, data)
        if result:
            messages.success(request, 'Event updated!')
            return redirect('event_detail', event_id=event_id)
        messages.error(request, f'Error: {err}')
    return render(request, 'core/event_form.html', {
        'event': event, 'venues': venues,
        'categories': ['music', 'sports', 'comedy', 'food', 'arts', 'tech', 'business', 'health', 'education', 'other'],
        'statuses': ['draft', 'published', 'cancelled', 'postponed', 'completed'],
        'form_title': 'Edit Event', 'action': 'edit',
        'user_email': request.session.get('user_email', ''),
    })


@login_required
def event_delete(request, event_id):
    if request.method == 'POST':
        ok, err = api.delete_event(event_id)
        if ok:
            messages.success(request, 'Event deleted.')
        else:
            messages.error(request, f'Delete failed: {err}')
    return redirect('event_list')


@login_required
def venue_list(request):
    page = int(request.GET.get('page', 1))
    q = request.GET.get('q', '').strip()
    if q:
        data, err = api.search_venues(q, page=page)
    else:
        data, err = api.list_venues(page=page)
    venues = data.get('venues', []) if data else []
    total = data.get('total', 0) if data else 0
    total_pages = (total + 11) // 12
    return render(request, 'core/venue_list.html', {
        'venues': venues, 'total': total, 'page': page, 'total_pages': total_pages,
        'q': q, 'error': err,
        'user_email': request.session.get('user_email', ''),
    })


@login_required
def venue_detail(request, venue_id):
    venue, err = api.get_venue(venue_id)
    events, _ = api.get_venue_events(venue_id) if venue else (None, None)
    ev_list = events if isinstance(events, list) else (events.get('events', []) if events else [])
    return render(request, 'core/venue_detail.html', {
        'venue': venue, 'events': ev_list, 'error': err,
        'user_email': request.session.get('user_email', ''),
    })


@login_required
def venue_create(request):
    if request.method == 'POST':
        data = {
            'name': request.POST.get('name'),
            'address': request.POST.get('address'),
            'city': request.POST.get('city'),
            'country': request.POST.get('country', 'Ireland'),
            'latitude': float(request.POST.get('latitude', 0)),
            'longitude': float(request.POST.get('longitude', 0)),
            'venue_type': request.POST.get('venue_type', 'other'),
            'capacity': int(request.POST.get('capacity')) if request.POST.get('capacity') else None,
            'description': request.POST.get('description') or None,
            'phone': request.POST.get('phone') or None,
            'website': request.POST.get('website') or None,
            'image_url': request.POST.get('image_url') or None,
        }
        result, err = api.create_venue(data)
        if result:
            messages.success(request, f'Venue "{result["name"]}" created!')
            return redirect('venue_detail', venue_id=result['id'])
        messages.error(request, f'Error: {err}')
    return render(request, 'core/venue_form.html', {
        'venue_types': ['stadium', 'theater', 'arena', 'club', 'restaurant', 'park', 'gallery', 'conference_center', 'other'],
        'form_title': 'Add Venue', 'action': 'create',
        'user_email': request.session.get('user_email', ''),
    })


@login_required
def venue_edit(request, venue_id):
    venue, err = api.get_venue(venue_id)
    if not venue:
        messages.error(request, f'Venue not found: {err}')
        return redirect('venue_list')
    if request.method == 'POST':
        data = {
            'name': request.POST.get('name'),
            'address': request.POST.get('address'),
            'city': request.POST.get('city'),
            'country': request.POST.get('country', 'Ireland'),
            'latitude': float(request.POST.get('latitude', 0)),
            'longitude': float(request.POST.get('longitude', 0)),
            'venue_type': request.POST.get('venue_type', 'other'),
            'capacity': int(request.POST.get('capacity')) if request.POST.get('capacity') else None,
            'description': request.POST.get('description') or None,
            'phone': request.POST.get('phone') or None,
            'website': request.POST.get('website') or None,
            'image_url': request.POST.get('image_url') or None,
        }
        result, err = api.update_venue(venue_id, data)
        if result:
            messages.success(request, 'Venue updated!')
            return redirect('venue_detail', venue_id=venue_id)
        messages.error(request, f'Error: {err}')
    return render(request, 'core/venue_form.html', {
        'venue': venue,
        'venue_types': ['stadium', 'theater', 'arena', 'club', 'restaurant', 'park', 'gallery', 'conference_center', 'other'],
        'form_title': 'Edit Venue', 'action': 'edit',
        'user_email': request.session.get('user_email', ''),
    })


@login_required
def venue_delete(request, venue_id):
    if request.method == 'POST':
        ok, err = api.delete_venue(venue_id)
        if ok:
            messages.success(request, 'Venue deleted.')
        else:
            messages.error(request, f'Delete failed: {err}')
    return redirect('venue_list')

def test_parking(request):
    """Test parking API connection."""
    from . import parking_client as parking
    data, err = parking.get_nearby_parking(53.3498, -6.2603, radius=10)
    return JsonResponse({
        'parking_data': data,
        'error': str(err),
        'count': len(data) if data else 0
    })
