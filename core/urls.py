from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/add-location/', views.add_location, name='add_location'),
    path('review/<uuid:location_id>/', views.review_page, name='review_page'),
    path('api/reviews/', views.get_reviews, name='api_reviews'),
    path('api/confirm/', views.confirm_post, name='api_confirm'),
    path('api/analytics/', views.api_analytics, name='api_analytics'),
]