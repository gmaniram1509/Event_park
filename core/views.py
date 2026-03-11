from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.conf import settings
from . import api_client as api


def home(request):
    events_data, err = api.list_events(page_size=6, status='published')
    venues_data, verr = api.list_venues(page_size=4)
    health, _ = api.health_check()
    return render(request, 'core/home.html', {
        'events': events_data.get('events', []) if events_data else [],
        'venues': venues_data.get('venues', []) if venues_data else [],
        'api_status': health.get('status') if health else 'offline',
        'error': err,
    })


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
    })


def event_detail(request, event_id):
    event, err = api.get_event(event_id)
    crowd, _ = api.get_crowd(event_id) if event else (None, None)
    tags = []
    if event and event.get('tags'):
        tags = [t.strip() for t in event['tags'].split(',')]
    return render(request, 'core/event_detail.html', {
        'event': event,
        'crowd': crowd,
        'error': err,
        'GOOGLE_MAPS_API_KEY': settings.GOOGLE_MAPS_API_KEY,  # ← added for Google Maps
    })


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
    })


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
    })


def event_delete(request, event_id):
    if request.method == 'POST':
        ok, err = api.delete_event(event_id)
        if ok:
            messages.success(request, 'Event deleted.')
        else:
            messages.error(request, f'Delete failed: {err}')
    return redirect('event_list')


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
    })


def venue_detail(request, venue_id):
    venue, err = api.get_venue(venue_id)
    events, _ = api.get_venue_events(venue_id) if venue else (None, None)
    ev_list = events if isinstance(events, list) else (events.get('events', []) if events else [])
    return render(request, 'core/venue_detail.html', {'venue': venue, 'events': ev_list, 'error': err})


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
    })


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
    })


def venue_delete(request, venue_id):
    if request.method == 'POST':
        ok, err = api.delete_venue(venue_id)
        if ok:
            messages.success(request, 'Venue deleted.')
        else:
            messages.error(request, f'Delete failed: {err}')
    return redirect('venue_list')


# ── AUTHENTICATION ──

def login_view(request):
    """Handle user login"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        
        if not username or not password:
            messages.error(request, 'Username and password required.')
            return render(request, 'core/login.html')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name or user.username}!')
            return redirect('home')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'core/login.html')


def register_view(request):
    """Handle user registration"""
    if request.user.is_authenticated:
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        password = request.POST.get('password', '').strip()
        password_confirm = request.POST.get('password_confirm', '').strip()
        
        # Validation
        if not all([username, email, password, password_confirm]):
            messages.error(request, 'All fields are required.')
            return render(request, 'core/register.html')
        
        if password != password_confirm:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'core/register.html')
        
        if len(password) < 6:
            messages.error(request, 'Password must be at least 6 characters.')
            return render(request, 'core/register.html')
        
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already taken.')
            return render(request, 'core/register.html')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
            return render(request, 'core/register.html')
        
        # Create user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
        )
        
        # Log them in
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome, {user.first_name or user.username}!')
            return redirect('home')
    
    return render(request, 'core/register.html')


def logout_view(request):
    """Handle user logout"""
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('home')