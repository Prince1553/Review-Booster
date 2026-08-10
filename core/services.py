"""
ReviewBoost Services — TOS-Compliant Architecture
==================================================
4-5 star  -> Gemini generates WRITING PROMPTS (what to mention)
             -> Customer writes their OWN review on Google
             -> 100% TOS compliant
1-3 star  -> Private feedback form -> dashboard inbox only, never Google

Key rules:
  * 100 prompts generated per star level (4* + 5* = 200 total) at signup
  * Each prompt is SINGLE-USE: once shown (used_count >= 1), never shown again
  * When unused prompts hit 0, auto-replenish fires (generates 100 more)
  * Custom keywords from owner are woven into every generation batch
  * Same QR code & URL works forever

settings.py mein add karo:
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')
    GEMINI_MODEL   = 'gemini-2.0-flash-lite'
"""
import json
import random
import threading
import urllib.request
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile
from django.conf import settings
from django.db.models import F
from .models import ReviewPrompt, Location

# ── CONFIG ────────────────────────────────────────────────────────────────────
INITIAL_COUNT     = 100   # prompts per star level at onboarding
REPLENISH_AT      = 0     # replenish when unused prompts reach this count
REPLENISH_COUNT   = 100   # how many to generate per replenish run
GEMINI_MODEL      = getattr(settings, 'GEMINI_MODEL', 'gemini-2.0-flash-lite')
# ─────────────────────────────────────────────────────────────────────────────

CATEGORY_ASPECTS = {
    'restaurant': ['food quality', 'taste of dishes', 'service speed', 'staff behaviour',
                   'ambience', 'cleanliness', 'value for money', 'portion size', 'menu variety',
                   'freshness', 'chef skills', 'seating comfort'],
    'salon':      ['haircut quality', 'styling', 'staff expertise', 'cleanliness',
                   'product quality', 'waiting time', 'pricing', 'overall experience',
                   'colour treatment', 'scalp care'],
    'clinic':     ['doctor expertise', 'staff behaviour', 'hygiene', 'waiting time',
                   'explanation of treatment', 'follow-up care', 'cleanliness',
                   'appointment process', 'medicine guidance'],
    'gym':        ['equipment quality', 'trainer guidance', 'cleanliness', 'atmosphere',
                   'class variety', 'membership value', 'locker facilities',
                   'peak-hour management', 'nutrition advice'],
    'hotel':      ['room cleanliness', 'staff service', 'breakfast quality', 'location',
                   'check-in process', 'amenities', 'value for money', 'noise level',
                   'WiFi quality', 'housekeeping'],
    'retail':     ['product quality', 'staff helpfulness', 'product variety', 'pricing',
                   'store cleanliness', 'checkout speed', 'return policy', 'packaging'],
    'other':      ['service quality', 'staff behaviour', 'value for money', 'cleanliness',
                   'overall experience', 'professionalism', 'timeliness', 'communication'],
}


def _call_gemini(prompt: str, api_key: str) -> list[str]:
    """Calls Google Gemini REST API. No SDK required."""
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={api_key}"
    )
    data = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 8192, "temperature": 1.0},
    }).encode()
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read())
        raw = result['candidates'][0]['content']['parts'][0]['text']
        return [t.strip() for t in raw.split('---NEXT---') if t.strip()]


def _build_prompt(business_name: str, category: str, star: int,
                  count: int, custom_keywords: str = '') -> str:
    """
    Builds prompt for Gemini.
    If owner gave custom keywords, those are prioritised over generic aspects.
    """
    aspects = CATEGORY_ASPECTS.get(category, CATEGORY_ASPECTS['other'])
    sampled = random.sample(aspects, min(5, len(aspects)))

    # Merge custom keywords in front so they get more weight
    if custom_keywords.strip():
        kw_list = [k.strip() for k in custom_keywords.split(',') if k.strip()]
        all_aspects = kw_list + sampled
    else:
        all_aspects = sampled

    mood = "absolutely delighted, very happy" if star == 5 else "satisfied and happy"

    return f"""You are helping a {category} business called "{business_name}" in India.

Generate exactly {count} unique REVIEW PROMPTS for customers who are {mood} ({star}/5 stars).

A review prompt = a short reminder of what this customer could mention in their OWN Google review.
It is NOT a review itself. The customer will write their own words.

Priority aspects to include: {', '.join(all_aspects[:8])}

Good examples:
- "Mention the biryani and how quickly your order arrived"
- "Tell them about the friendly staff and the clean seating area"
- "Share how the doctor explained the treatment clearly and was very patient"

Rules:
- Exactly 1 sentence per prompt, 8-20 words
- Start with a verb: Mention / Tell / Share / Describe / Talk about / Highlight
- Each prompt must focus on DIFFERENT aspects — no repetition
- Natural Indian English — sound like a suggestion from a friend
- NO numbering, NO bullet points, NO quotes around the prompt
- Separate each prompt with exactly: ---NEXT---

Return ONLY the {count} prompts separated by ---NEXT--- and nothing else."""


def _unused_count(location: Location, star: int) -> int:
    """Returns count of prompts not yet shown to any customer."""
    return ReviewPrompt.objects.filter(
        location=location, star_rating=star, used_count=0
    ).count()


def generate_prompts_for_location(location: Location,
                                   per_star: int = INITIAL_COUNT) -> int:
    """
    Called ONCE at onboarding in a background thread.
    Generates `per_star` prompts for 4* and 5* each.
    Uses custom_keywords if the owner set them.
    """
    api_key = getattr(settings, 'GEMINI_API_KEY', '')
    business = location.business
    keywords = location.custom_keywords
    total = 0

    for star in (4, 5):
        prompt_text = _build_prompt(
            business.name, business.category, star, per_star, keywords
        )
        if api_key:
            try:
                texts = _call_gemini(prompt_text, api_key)
            except Exception:
                texts = _fallback_prompts(business.category, star)
        else:
            texts = _fallback_prompts(business.category, star)

        for text in texts[:per_star]:
            ReviewPrompt.objects.create(
                location=location,
                star_rating=star,
                prompt_text=text,
                used_count=0,
            )
            total += 1

    return total


def generate_prompts_async(location: Location):
    """Non-blocking wrapper — signup stays instant."""
    t = threading.Thread(target=generate_prompts_for_location, args=(location,))
    t.daemon = True
    t.start()


# ── AUTO-REPLENISH ─────────────────────────────────────────────────────────────

def check_and_replenish(location: Location):
    """
    Called in background after every get_prompts_for_star.
    If UNUSED prompts for any star == 0, generates REPLENISH_COUNT more.
    """
    for star in (4, 5):
        if _unused_count(location, star) <= REPLENISH_AT:
            t = threading.Thread(
                target=_replenish_star,
                args=(location, star, REPLENISH_COUNT)
            )
            t.daemon = True
            t.start()


def _replenish_star(location: Location, star: int, count: int):
    api_key = getattr(settings, 'GEMINI_API_KEY', '')
    business = location.business
    keywords = location.custom_keywords
    prompt_text = _build_prompt(
        business.name, business.category, star, count, keywords
    )
    if api_key:
        try:
            texts = _call_gemini(prompt_text, api_key)
        except Exception:
            texts = _fallback_prompts(business.category, star)
    else:
        texts = _fallback_prompts(business.category, star)

    for text in texts[:count]:
        ReviewPrompt.objects.create(
            location=location,
            star_rating=star,
            prompt_text=text,
            used_count=0,
        )

# ──────────────────────────────────────────────────────────────────────────────


def _fallback_prompts(category: str, star: int) -> list[str]:
    """Used when no API key configured. Returns enough to fill 100."""
    base = {
        'restaurant': [
            "Mention the food quality and how quickly your order arrived",
            "Tell them about the taste of the dishes and the friendly staff",
            "Share your experience with the ambience and overall service",
            "Describe the cleanliness and value for money at this place",
            "Talk about the menu variety and how helpful the staff was",
            "Mention what dish you had and why you would recommend it",
            "Share how the staff made you feel welcome during your visit",
            "Tell others about the portion size and overall food quality",
            "Describe the dining experience and what you liked most",
            "Mention the service speed and your favourite item on the menu",
            "Tell them how fresh the ingredients tasted in every dish",
            "Share how the seating was comfortable and the place was spotless",
            "Mention the chef speciality and why it stood out for you",
            "Describe the overall vibe and why you would visit again",
            "Tell others about the friendly staff and the quick service",
        ],
        'salon': [
            "Tell them about the haircut quality and your stylist expertise",
            "Mention how clean the salon was and how comfortable you felt",
            "Share your experience with the staff and the final result",
            "Describe how the stylist understood exactly what you wanted",
            "Talk about the products used and the overall atmosphere",
            "Mention the waiting time and how professional the team was",
            "Share why you would recommend this salon to your friends",
            "Tell others about the pricing and the quality of service",
            "Describe what treatment you got and how happy you are with it",
            "Mention the booking process and overall experience",
            "Tell them how the colour treatment turned out perfectly",
            "Share how relaxing the experience was from start to finish",
            "Mention the expert advice given before the treatment",
            "Describe the hygiene standards and the quality of products used",
            "Tell others how the final look exceeded your expectations",
        ],
        'other': [
            "Mention what you liked most about the service and the staff",
            "Tell them about the overall experience and why you recommend it",
            "Share what made your visit special and worth returning for",
            "Describe the professionalism and quality of service you received",
            "Talk about the value for money and the cleanliness of the place",
            "Mention how helpful the team was throughout your visit",
            "Share the specific thing that impressed you the most",
            "Tell others about the timing and quality of the service",
            "Describe your overall experience and what you would tell a friend",
            "Mention the staff behaviour and the quality of the outcome",
            "Tell them how smoothly everything was handled from start to finish",
            "Share how the team went above and beyond to help you",
            "Mention the attention to detail and the friendly approach",
            "Describe how the service matched exactly what was promised",
            "Tell others how comfortable and welcome you felt throughout",
        ],
    }
    prompts = base.get(category, base['other'])
    result = []
    while len(result) < 100:
        result.extend(prompts)
    return result[:100]


def get_prompts_for_star(location: Location, star_rating: int, count: int = 3) -> list:
    """
    Pure DB fetch — zero AI cost at scan time.
    SINGLE-USE: only returns prompts with used_count == 0.
    Fires auto-replenish check in background.
    """
    # Only fetch unused prompts
    prompts = list(
        ReviewPrompt.objects.filter(
            location=location,
            star_rating=star_rating,
            used_count=0,          # <-- KEY: never show a used prompt again
        ).order_by('created_at')[:count * 4]
    )

    # Non-blocking replenish check
    t = threading.Thread(target=check_and_replenish, args=(location,))
    t.daemon = True
    t.start()

    if not prompts:
        return []
    if len(prompts) <= count:
        return prompts
    return random.sample(prompts, count)


def increment_prompt_used(prompt_id):
    """Mark prompt as used. Will never be shown to another customer."""
    ReviewPrompt.objects.filter(id=prompt_id).update(used_count=F('used_count') + 1)


def generate_qr_code(location: Location, base_url: str) -> None:
    """Generate QR PNG. URL never changes — safe to reprint anytime."""
    url = f"{base_url}/review/{location.id}/"
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    location.qr_image.save(f"qr_{location.id}.png", ContentFile(buf.read()), save=True)


# ── Backward-compat aliases ────────────────────────────────────────────────────
generate_reviews_for_location = generate_prompts_for_location
generate_reviews_async        = generate_prompts_async
get_reviews_for_star          = get_prompts_for_star
increment_used_count          = increment_prompt_used