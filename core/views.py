import json
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

from .models import (
    Business, Location, ReviewPrompt, PrivateFeedback,
    Scan, MenuItem, OfferPoster,
)
from .services import (
    generate_prompts_async, get_prompts_for_star,
    generate_qr_code, increment_prompt_used, _fallback_prompts,
    generate_reviews_for_location, generate_reviews_async,
    get_reviews_for_star, increment_used_count,
)


# ── Public ─────────────────────────────────────────────────────────────────────

def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'core/home.html')


def signup_view(request):
    if request.method == 'POST':
        d = request.POST
        if not d.get('email') or not d.get('password') or not d.get('business_name'):
            return render(request, 'core/auth.html',
                          {'error': 'Name, email and password are required.', 'mode': 'signup'})
        if len(d['password']) < 6:
            return render(request, 'core/auth.html',
                          {'error': 'Password must be at least 6 characters.', 'mode': 'signup'})
        if User.objects.filter(username=d['email']).exists():
            return render(request, 'core/auth.html',
                          {'error': 'Email already registered. Please login.', 'mode': 'signup'})
        if not d.get('address'):
            return render(request, 'core/auth.html',
                          {'error': 'Please enter your business address.', 'mode': 'signup'})

        user = User.objects.create_user(
            username=d['email'], email=d['email'],
            password=d['password'], first_name=d.get('name', ''))
        business = Business.objects.create(
            user=user, name=d['business_name'],
            category=d['category'], plan='solo')
        location = Location.objects.create(
            business=business, name='Main Branch',
            address=d.get('address', ''),
            place_id=d.get('place_id', ''),
            custom_keywords=d.get('custom_keywords', ''),
        )
        base = request.build_absolute_uri('/').rstrip('/')
        generate_qr_code(location, base)
        generate_prompts_async(location)
        login(request, user)
        return redirect('dashboard')
    return render(request, 'core/auth.html', {'mode': 'signup'})


def login_view(request):
    if request.method == 'POST':
        user = authenticate(request,
                            username=request.POST.get('email'),
                            password=request.POST.get('password'))
        if user:
            login(request, user)
            return redirect('dashboard')
        return render(request, 'core/auth.html',
                      {'error': 'Wrong email or password.', 'mode': 'login'})
    return render(request, 'core/auth.html', {'mode': 'login'})


def logout_view(request):
    logout(request)
    return redirect('home')


# ── Dashboard ──────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    try:
        business = request.user.business
    except Business.DoesNotExist:
        return redirect('signup')

    locations = business.locations.prefetch_related(
        'menu_items', 'private_feedbacks', 'offer_posters'
    ).all()

    total_scans = Scan.objects.filter(location__business=business).count()
    scans_this_week = Scan.objects.filter(
        location__business=business,
        scanned_at__gte=timezone.now() - timedelta(days=7)
    ).count()
    avg_star = Scan.objects.filter(
        location__business=business, star_selected__isnull=False
    ).aggregate(avg=Avg('star_selected'))['avg'] or 0

    trend = []
    for i in range(6, -1, -1):
        day = timezone.now() - timedelta(days=i)
        cnt = Scan.objects.filter(
            location__business=business, scanned_at__date=day.date()).count()
        trend.append({'day': day.strftime('%d %b'), 'count': cnt})

    star_dist = []
    for s in range(5, 0, -1):
        cnt = Scan.objects.filter(
            location__business=business, star_selected=s).count()
        star_dist.append({'star': s, 'count': cnt})

    unresolved_feedback = PrivateFeedback.objects.filter(
        location__business=business, is_resolved=False).count()
    recent_feedbacks = PrivateFeedback.objects.filter(
        location__business=business
    ).select_related('location').order_by('-submitted_at')[:20]

    prompt_stats = {}
    for loc in locations:
        prompt_stats[str(loc.id)] = {
            4: ReviewPrompt.objects.filter(location=loc, star_rating=4, used_count=0).count(),
            5: ReviewPrompt.objects.filter(location=loc, star_rating=5, used_count=0).count(),
        }

    return render(request, 'core/dashboard.html', {
        'business': business,
        'locations': locations,
        'total_scans': total_scans,
        'scans_this_week': scans_this_week,
        'avg_star': round(avg_star, 1),
        'trend_json': json.dumps(trend),
        'star_dist_json': json.dumps(star_dist),
        'menu_sections': MenuItem.SECTION_CHOICES,
        'unresolved_feedback': unresolved_feedback,
        'recent_feedbacks': recent_feedbacks,
        'prompt_stats': prompt_stats,
    })


@login_required
def add_location(request):
    if request.method == 'POST':
        business = request.user.business
        location = Location.objects.create(
            business=business,
            name=request.POST['name'],
            address=request.POST.get('address', ''),
            place_id=request.POST.get('place_id', ''),
            custom_keywords=request.POST.get('custom_keywords', ''),
        )
        base = request.build_absolute_uri('/').rstrip('/')
        generate_qr_code(location, base)
        generate_prompts_async(location)
        return redirect('dashboard')
    return render(request, 'core/add_location.html')


# ── Location settings (website + social) ──────────────────────────────────────

@login_required
@require_POST
def update_location_links(request, location_id):
    """Save website URL and social media links for a location."""
    loc = get_object_or_404(Location, id=location_id, business=request.user.business)
    loc.website_url   = request.POST.get('website_url', '').strip()
    loc.facebook_url  = request.POST.get('facebook_url', '').strip()
    loc.instagram_url = request.POST.get('instagram_url', '').strip()
    loc.youtube_url   = request.POST.get('youtube_url', '').strip()
    loc.save(update_fields=['website_url', 'facebook_url', 'instagram_url', 'youtube_url'])
    return redirect('dashboard')


# ── Menu ───────────────────────────────────────────────────────────────────────

@login_required
@require_POST
def upload_menu(request, location_id):
    location = get_object_or_404(Location, id=location_id, business=request.user.business)
    files = request.FILES.getlist('menu_files')
    section = request.POST.get('section', 'general')
    title = request.POST.get('title', '')
    if not files:
        return redirect('dashboard')
    existing_max = (
        location.menu_items.order_by('-sort_order')
        .values_list('sort_order', flat=True).first() or 0)
    for i, f in enumerate(files):
        is_pdf = (f.content_type == 'application/pdf' or
                  f.name.lower().endswith('.pdf'))
        MenuItem.objects.create(
            location=location, section=section, title=title,
            file=f, file_type='pdf' if is_pdf else 'image',
            sort_order=existing_max + i + 1)
    return redirect('dashboard')


@login_required
@require_POST
def delete_menu_item(request, item_id):
    item = get_object_or_404(MenuItem, id=item_id, location__business=request.user.business)
    if item.file:
        item.file.delete(save=False)
    item.delete()
    return redirect('dashboard')


# ── Offers ─────────────────────────────────────────────────────────────────────

@login_required
@require_POST
def upload_offer(request, location_id):
    """Upload offer poster image(s) for a location."""
    location = get_object_or_404(Location, id=location_id, business=request.user.business)
    files = request.FILES.getlist('offer_images')
    title = request.POST.get('offer_title', '').strip()
    if not files:
        return redirect('dashboard')
    existing_max = (
        location.offer_posters.order_by('-sort_order')
        .values_list('sort_order', flat=True).first() or 0)
    for i, f in enumerate(files):
        OfferPoster.objects.create(
            location=location, title=title,
            image=f, sort_order=existing_max + i + 1)
    return redirect('dashboard')


@login_required
@require_POST
def delete_offer(request, offer_id):
    offer = get_object_or_404(OfferPoster, id=offer_id, location__business=request.user.business)
    if offer.image:
        offer.image.delete(save=False)
    offer.delete()
    return redirect('dashboard')


@login_required
@require_POST
def toggle_offer(request, offer_id):
    """Activate / deactivate an offer without deleting it."""
    offer = get_object_or_404(OfferPoster, id=offer_id, location__business=request.user.business)
    offer.is_active = not offer.is_active
    offer.save(update_fields=['is_active'])
    return redirect('dashboard')


# ── Private feedback ───────────────────────────────────────────────────────────

@login_required
@require_POST
def resolve_feedback(request, feedback_id):
    fb = get_object_or_404(PrivateFeedback, id=feedback_id,
                           location__business=request.user.business)
    fb.is_resolved = True
    fb.save(update_fields=['is_resolved'])
    return redirect('dashboard')


# ── Customer QR page ───────────────────────────────────────────────────────────

def review_page(request, location_id):
    location = get_object_or_404(Location, id=location_id)
    scan = Scan.objects.create(location=location)

    menu_items = location.menu_items.all()
    has_menu = menu_items.exists()
    menu_by_section = {}
    for item in menu_items:
        label = item.get_section_display()
        if label not in menu_by_section:
            menu_by_section[label] = []
        menu_by_section[label].append(item)

    active_offers = location.offer_posters.filter(is_active=True)

    return render(request, 'core/review_page.html', {
        'location': location,
        'scan_id': str(scan.id),
        'has_menu': has_menu,
        'menu_by_section': menu_by_section,
        'active_offers': active_offers,
        'has_offers': active_offers.exists(),
    })


# ── Customer APIs ──────────────────────────────────────────────────────────────

@csrf_exempt
@require_POST
def get_prompts(request):
    data = json.loads(request.body)
    location_id = data.get('location_id')
    star = int(data.get('star', 5))
    scan_id = data.get('scan_id')

    location = get_object_or_404(Location, id=location_id)
    prompts = get_prompts_for_star(location, star)
    Scan.objects.filter(id=scan_id).update(star_selected=star)

    if not prompts:
        fallback = _fallback_prompts(location.business.category, star)
        prompts_data = [{'id': '', 'text': t} for t in fallback[:3]]
    else:
        prompts_data = [{'id': str(p.id), 'text': p.prompt_text} for p in prompts]

    return JsonResponse({'prompts': prompts_data, 'google_url': location.google_review_url})


@csrf_exempt
@require_POST
def confirm_redirect(request):
    data = json.loads(request.body)
    scan_id = data.get('scan_id')
    prompt_id = data.get('prompt_id')
    if prompt_id:
        increment_prompt_used(prompt_id)
        Scan.objects.filter(id=scan_id).update(prompt_used_id=prompt_id, posted=True)
    return JsonResponse({'status': 'ok'})


@csrf_exempt
@require_POST
def submit_private_feedback(request):
    data = json.loads(request.body)
    location_id = data.get('location_id')
    star = int(data.get('star', 1))
    location = get_object_or_404(Location, id=location_id)
    PrivateFeedback.objects.create(
        location=location,
        star_rating=star,
        feedback_text=data.get('feedback', '').strip(),
        contact=data.get('contact', '').strip(),
    )
    Scan.objects.filter(id=data.get('scan_id')).update(star_selected=star)
    return JsonResponse({'status': 'ok'})


@login_required
def api_analytics(request):
    business = request.user.business
    days = int(request.GET.get('days', 7))
    trend = []
    for i in range(days - 1, -1, -1):
        day = timezone.now() - timedelta(days=i)
        cnt = Scan.objects.filter(
            location__business=business, scanned_at__date=day.date()).count()
        trend.append({'day': day.strftime('%d %b'), 'count': cnt})
    return JsonResponse({'trend': trend})