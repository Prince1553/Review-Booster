from django.shortcuts import render

# Create your views here.
import json
import threading
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Avg
from django.utils import timezone
from datetime import timedelta

from .models import Business, Location, Review, Scan
from .services import (
    generate_reviews_for_location,
    generate_reviews_async,
    get_reviews_for_star,
    generate_qr_code,
    increment_used_count,
)


# ─────────────────────────────────────────
# PUBLIC PAGES
# ─────────────────────────────────────────

def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'core/home.html')


def signup_view(request):
    if request.method == 'POST':
        d = request.POST

        # Validation
        if not d.get('email') or not d.get('password') or not d.get('business_name'):
            return render(request, 'core/auth.html', {
                'error': 'All fields are required.', 'mode': 'signup'
            })
        if len(d['password']) < 6:
            return render(request, 'core/auth.html', {
                'error': 'Password must be at least 6 characters.', 'mode': 'signup'
            })
        if User.objects.filter(username=d['email']).exists():
            return render(request, 'core/auth.html', {
                'error': 'This email is already registered. Please login.', 'mode': 'signup'
            })

        # Create user + business + location
        user = User.objects.create_user(
            username=d['email'], email=d['email'],
            password=d['password'], first_name=d.get('name', '')
        )
        business = Business.objects.create(
            user=user, name=d['business_name'],
            category=d['category'], plan='starter'
        )
        location = Location.objects.create(
            business=business, name='Main Branch', place_id=d['place_id']
        )

        # Generate QR (fast, synchronous)
        base = request.build_absolute_uri('/').rstrip('/')
        generate_qr_code(location, base)

        # Generate reviews in BACKGROUND — signup stays instant
        generate_reviews_async(location)

        login(request, user)
        return redirect('dashboard')

    return render(request, 'core/auth.html', {'mode': 'signup'})


def login_view(request):
    if request.method == 'POST':
        user = authenticate(
            request,
            username=request.POST.get('email'),
            password=request.POST.get('password')
        )
        if user:
            login(request, user)
            return redirect('dashboard')
        return render(request, 'core/auth.html', {
            'error': 'Wrong email or password. Please try again.', 'mode': 'login'
        })
    return render(request, 'core/auth.html', {'mode': 'login'})


def logout_view(request):
    logout(request)
    return redirect('home')


# ─────────────────────────────────────────
# BUSINESS DASHBOARD
# ─────────────────────────────────────────

@login_required
def dashboard(request):
    try:
        business = request.user.business
    except Business.DoesNotExist:
        return redirect('signup')

    locations = business.locations.all()
    total_scans = Scan.objects.filter(location__business=business).count()
    scans_this_week = Scan.objects.filter(
        location__business=business,
        scanned_at__gte=timezone.now() - timedelta(days=7)
    ).count()
    avg_star = Scan.objects.filter(
        location__business=business,
        star_selected__isnull=False
    ).aggregate(avg=Avg('star_selected'))['avg'] or 0

    # 7-day trend
    trend = []
    for i in range(6, -1, -1):
        day = timezone.now() - timedelta(days=i)
        count = Scan.objects.filter(
            location__business=business,
            scanned_at__date=day.date()
        ).count()
        trend.append({'day': day.strftime('%d %b'), 'count': count})

    # Star distribution
    star_dist = []
    for s in range(5, 0, -1):
        cnt = Scan.objects.filter(
            location__business=business, star_selected=s
        ).count()
        star_dist.append({'star': s, 'count': cnt})

    return render(request, 'core/dashboard.html', {
        'business': business,
        'locations': locations,
        'total_scans': total_scans,
        'scans_this_week': scans_this_week,
        'avg_star': round(avg_star, 1),
        'trend_json': json.dumps(trend),
        'star_dist_json': json.dumps(star_dist),
    })


@login_required
def add_location(request):
    if request.method == 'POST':
        business = request.user.business
        location = Location.objects.create(
            business=business,
            name=request.POST['name'],
            place_id=request.POST['place_id']
        )
        base = request.build_absolute_uri('/').rstrip('/')
        generate_qr_code(location, base)
        generate_reviews_async(location)   # background, non-blocking
        return redirect('dashboard')
    return render(request, 'core/add_location.html')


# ─────────────────────────────────────────
# CUSTOMER REVIEW FLOW (public, mobile)
# ─────────────────────────────────────────

def review_page(request, location_id):
    location = get_object_or_404(Location, id=location_id)
    scan = Scan.objects.create(location=location)
    return render(request, 'core/review_page.html', {
        'location': location,
        'scan_id': str(scan.id),
    })


@csrf_exempt
@require_POST
def get_reviews(request):
    """
    API: Customer tapped a star.
    Returns 5 reviews from pool — NO AI call, pure DB.
    """
    data = json.loads(request.body)
    location_id = data.get('location_id')
    star = int(data.get('star', 5))
    scan_id = data.get('scan_id')

    reviews = get_reviews_for_star(location_id, star)
    Scan.objects.filter(id=scan_id).update(star_selected=star)

    if not reviews:
        # Pool not ready yet (AI still generating in background)
        from .services import _fallback_reviews
        location = Location.objects.get(id=location_id)
        fallback = _fallback_reviews(location.business.name, location.business.category, star)
        reviews_data = [{'id': '', 'text': t} for t in fallback[:5]]
    else:
        reviews_data = [{'id': str(r.id), 'text': r.review_text} for r in reviews]

    location = Location.objects.get(id=location_id)
    return JsonResponse({
        'reviews': reviews_data,
        'google_url': location.google_review_url,
    })


@csrf_exempt
@require_POST
def confirm_post(request):
    """API: Customer chose a review and tapped Post."""
    data = json.loads(request.body)
    scan_id = data.get('scan_id')
    review_id = data.get('review_id')
    if review_id:
        increment_used_count(review_id)
        Scan.objects.filter(id=scan_id).update(
            review_chosen_id=review_id, posted=True
        )
    return JsonResponse({'status': 'ok'})


@login_required
def api_analytics(request):
    """API: Dashboard chart data."""
    business = request.user.business
    days = int(request.GET.get('days', 7))
    trend = []
    for i in range(days - 1, -1, -1):
        day = timezone.now() - timedelta(days=i)
        count = Scan.objects.filter(
            location__business=business,
            scanned_at__date=day.date()
        ).count()
        trend.append({'day': day.strftime('%d %b'), 'count': count})
    return JsonResponse({'trend': trend})