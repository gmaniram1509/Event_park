from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),

    # Authentication
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),

    # Events
    path('events/', views.event_list, name='event_list'),
    path('events/create/', views.event_create, name='event_create'),
    path('events/<str:event_id>/', views.event_detail, name='event_detail'),
    path('events/<str:event_id>/edit/', views.event_edit, name='event_edit'),
    path('events/<str:event_id>/delete/', views.event_delete, name='event_delete'),

    # Venues
    path('venues/', views.venue_list, name='venue_list'),
    path('venues/create/', views.venue_create, name='venue_create'),
    path('venues/<str:venue_id>/', views.venue_detail, name='venue_detail'),
    path('venues/<str:venue_id>/edit/', views.venue_edit, name='venue_edit'),
    path('venues/<str:venue_id>/delete/', views.venue_delete, name='venue_delete'),
]
