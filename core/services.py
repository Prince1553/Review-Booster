"""
AI Review Generation Service
- Called ONCE at onboarding → generates 100 reviews → saves to DB
- Customer scan → DB fetch only → ZERO AI cost
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
from .models import Review, Location


CATEGORY_KEYWORDS = {
    'restaurant': ['food', 'taste', 'service', 'ambience', 'menu', 'chef', 'fresh', 'delicious'],
    'salon':      ['haircut', 'styling', 'staff', 'clean', 'professional', 'color', 'treatment'],
    'clinic':     ['doctor', 'staff', 'hygiene', 'care', 'treatment', 'waiting time', 'professional'],
    'gym':        ['equipment', 'trainers', 'cleanliness', 'atmosphere', 'classes', 'machines'],
    'hotel':      ['rooms', 'service', 'cleanliness', 'staff', 'location', 'breakfast', 'comfort'],
    'retail':     ['products', 'staff', 'variety', 'price', 'quality', 'service', 'stock'],
    'other':      ['service', 'staff', 'quality', 'experience', 'professional', 'value'],
}

STAR_SENTIMENTS = {
    5: "extremely positive, delighted, highly recommend",
    4: "positive, satisfied, would recommend",
    3: "average, okay, decent but could improve",
    2: "slightly negative, disappointed, needs improvement",
    1: "very negative, dissatisfied, not recommended",
}


def generate_reviews_for_location(location: Location) -> int:
    """
    Called ONCE when a business onboards.
    Generates 20 reviews per star (100 total) and saves to DB.
    ✅ Run in background thread to avoid signup freeze.
    """
    api_key = settings.ANTHROPIC_API_KEY
    business = location.business
    keywords = CATEGORY_KEYWORDS.get(business.category, CATEGORY_KEYWORDS['other'])
    total = 0

    for star in range(1, 6):
        prompt = f"""Generate exactly 20 different Google review texts for a {business.category} business called "{business.name}" in India.

Star rating: {star}/5 stars — {STAR_SENTIMENTS[star]}
Keywords to include naturally: {', '.join(keywords)}

Rules:
- Each review: 1-3 sentences, natural Indian English
- Vary length and style across 20 reviews
- Sound like real customers, not marketing
- NO numbering, NO bullet points
- Separate each review with exactly: ---NEXT---

Return ONLY the 20 reviews separated by ---NEXT--- and nothing else."""

        if api_key:
            try:
                data = json.dumps({
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 2000,
                    "messages": [{"role": "user", "content": prompt}]
                }).encode()
                req = urllib.request.Request(
                    "https://api.anthropic.com/v1/messages",
                    data=data,
                    headers={
                        "Content-Type": "application/json",
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01"
                    }
                )
                with urllib.request.urlopen(req, timeout=30) as resp:
                    result = json.loads(resp.read())
                    raw = result['content'][0]['text']
                    texts = [t.strip() for t in raw.split('---NEXT---') if t.strip()]
            except Exception:
                texts = _fallback_reviews(business.name, business.category, star)
        else:
            texts = _fallback_reviews(business.name, business.category, star)

        for text in texts[:20]:
            Review.objects.create(
                location=location,
                star_rating=star,
                review_text=text,
                used_count=0
            )
            total += 1

    return total


def generate_reviews_async(location: Location):
    """Run AI generation in background — signup stays instant."""
    t = threading.Thread(target=generate_reviews_for_location, args=(location,))
    t.daemon = True
    t.start()


def _fallback_reviews(name, category, star):
    """Demo reviews used when no API key is set."""
    templates = {
        5: [
            f"Absolutely loved my experience at {name}! The service was outstanding and I will definitely be coming back.",
            f"Best {category} in the area without a doubt. Highly recommend to everyone!",
            f"Amazing experience at {name}. Staff was very helpful and professional.",
            f"Five stars is not enough for {name}. Truly exceptional service every single time.",
            f"Visited {name} last week and was blown away by the quality. Will tell all my friends.",
            f"Outstanding {category}! {name} exceeded all my expectations. Will visit again.",
            f"Exceptional quality and service at {name}. My go-to place from now on.",
            f"Loved everything about {name}. Clean, professional, and great value for money.",
            f"10/10 experience at {name}. The staff made us feel very welcome.",
            f"Cannot recommend {name} enough. Truly the best {category} experience I have had.",
        ],
        4: [
            f"Great experience at {name}. Very satisfied with the service overall.",
            f"Good place, {name} offers solid quality and friendly staff. Recommended!",
            f"Really enjoyed my visit to {name}. Minor wait time but totally worth it.",
            f"Four stars for {name} — great service and value for money.",
            f"Positive experience overall at {name}. Will visit again for sure.",
            f"Good quality and nice staff at {name}. A reliable choice.",
            f"Enjoyed my time at {name}. Small improvements could make it perfect.",
            f"Happy with my visit to {name}. Good service and reasonable pricing.",
            f"Solid {category} experience at {name}. Would recommend to friends.",
            f"Pleasant visit to {name}. Staff was courteous and service was prompt.",
        ],
        3: [
            f"Decent experience at {name}. Service was okay, nothing extraordinary.",
            f"Average visit to {name}. Could improve on a few things but okay overall.",
            f"Okay experience. {name} is fine but there is room for improvement.",
            f"Mixed feelings about {name}. Some things were good, others not so much.",
            f"Three stars for {name}. Not bad but not great either.",
            f"Moderate experience at {name}. Gets the job done but could be better.",
            f"Fair service at {name}. Nothing to complain about, nothing to rave about.",
            f"Average quality at {name}. Meets basic expectations but nothing more.",
            f"Okay visit to {name}. A few things could use improvement.",
            f"Satisfactory experience at {name}. Would consider coming back if improved.",
        ],
        2: [
            f"Disappointed with my visit to {name}. Expected better quality.",
            f"Below average experience. {name} needs to work on their service.",
            f"Not happy with my visit to {name}. Staff could be more attentive.",
            f"Two stars for {name}. Several issues that need to be addressed.",
            f"Could be much better. {name} did not meet my expectations.",
            f"Underwhelming experience at {name}. Quite a few things went wrong.",
            f"Not impressed with {name}. Quality was below what I expected.",
            f"Had issues during my visit to {name}. Needs improvement.",
            f"Service was lacking at {name}. Disappointed overall.",
            f"Below par visit to {name}. Would not recommend at this point.",
        ],
        1: [
            f"Very poor experience at {name}. Would not recommend at all.",
            f"Terrible service at {name}. Really disappointed.",
            f"Would not return to {name}. Multiple issues during my visit.",
            f"One star for {name}. Nothing went right during my visit.",
            f"Extremely disappointed. {name} needs major improvements.",
            f"Worst {category} experience I have had. {name} was very disappointing.",
            f"Unacceptable service at {name}. Will not be coming back.",
            f"Very unhappy with my visit to {name}. Many things went wrong.",
            f"Cannot recommend {name}. The experience was quite poor.",
            f"Terrible visit to {name}. Staff was unhelpful and quality was very low.",
        ],
    }
    base = templates.get(star, templates[3])
    result = []
    while len(result) < 20:
        result.extend(base)
    return result[:20]


def get_reviews_for_star(location_id, star_rating, count=5):
    """
    Fast DB fetch — NO AI call.
    Returns least-used reviews first with randomness for variety.
    """
    reviews = list(
        Review.objects.filter(
            location_id=location_id,
            star_rating=star_rating
        ).order_by('used_count')[:count * 3]
    )
    if not reviews:
        return []
    if len(reviews) <= count:
        return reviews
    return random.sample(reviews, count)


def increment_used_count(review_id):
    """Increment usage counter so least-used reviews get shown more."""
    Review.objects.filter(id=review_id).update(used_count=F('used_count') + 1)


def generate_qr_code(location: Location, base_url: str) -> None:
    """Generate QR PNG and save to media/qr_codes/."""
    url = f"{base_url}/review/{location.id}/"
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    location.qr_image.save(f"qr_{location.id}.png", ContentFile(buf.read()), save=True)