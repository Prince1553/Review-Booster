from django.urls import path
from . import views

urlpatterns = [
    # Auth
    path('', views.home, name='home'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/add-location/', views.add_location, name='add_location'),

    # Location settings (links + social)
    path('dashboard/location/<uuid:location_id>/links/',
         views.update_location_links, name='update_location_links'),

    # Menu
    path('dashboard/location/<uuid:location_id>/upload-menu/',
         views.upload_menu, name='upload_menu'),
    path('dashboard/menu-item/<uuid:item_id>/delete/',
         views.delete_menu_item, name='delete_menu_item'),

    # Offers
    path('dashboard/location/<uuid:location_id>/upload-offer/',
         views.upload_offer, name='upload_offer'),
    path('dashboard/offer/<uuid:offer_id>/delete/',
         views.delete_offer, name='delete_offer'),
    path('dashboard/offer/<uuid:offer_id>/toggle/',
         views.toggle_offer, name='toggle_offer'),

    # Private feedback
    path('dashboard/feedback/<uuid:feedback_id>/resolve/',
         views.resolve_feedback, name='resolve_feedback'),

    # Customer QR page
    path('review/<uuid:location_id>/', views.review_page, name='review_page'),

    # Customer APIs
    path('api/prompts/', views.get_prompts, name='api_prompts'),
    path('api/confirm/', views.confirm_redirect, name='api_confirm'),
    path('api/feedback/', views.submit_private_feedback, name='api_feedback'),
    path('api/analytics/', views.api_analytics, name='api_analytics'),
]