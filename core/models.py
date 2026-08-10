from django.db import models
from django.contrib.auth.models import User
import uuid


class Business(models.Model):
    PLAN_CHOICES = [
        ('solo',   'Solo Rs499/mo'),
        ('growth', 'Growth Rs999/mo'),
        ('chain',  'Chain Rs2499/mo'),
        ('agency', 'Agency Rs5999/mo'),
    ]
    CATEGORY_CHOICES = [
        ('restaurant', 'Restaurant / Cafe / Dhaba'),
        ('salon',      'Salon / Spa'),
        ('clinic',     'Clinic / Hospital'),
        ('gym',        'Gym / Fitness'),
        ('hotel',      'Hotel / Guesthouse'),
        ('retail',     'Retail Shop'),
        ('other',      'Other'),
    ]
    id         = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user       = models.OneToOneField(User, on_delete=models.CASCADE, related_name='business')
    name       = models.CharField(max_length=200)
    category   = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    plan       = models.CharField(max_length=20, choices=PLAN_CHOICES, default='solo')
    active     = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Location(models.Model):
    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business        = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='locations')
    name            = models.CharField(max_length=200)
    address         = models.TextField(blank=True)
    place_id        = models.CharField(max_length=200, blank=True)
    custom_keywords = models.TextField(blank=True)

    # ── NEW: Website & social links ──────────────────────────────────────────
    website_url     = models.URLField(blank=True, help_text='e.g. https://sharmacafe.com')
    facebook_url    = models.URLField(blank=True, help_text='Facebook page URL')
    instagram_url   = models.URLField(blank=True, help_text='Instagram profile URL')
    youtube_url     = models.URLField(blank=True, help_text='YouTube channel URL')
    # ────────────────────────────────────────────────────────────────────────

    qr_image   = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.business.name} - {self.name}"

    @property
    def google_review_url(self):
        if self.place_id:
            return f"https://search.google.com/local/writereview?placeid={self.place_id}"
        import urllib.parse
        q = urllib.parse.quote_plus(f"{self.business.name} {self.address}")
        return f"https://www.google.com/search?q={q}#lrd=,1,"

    @property
    def review_page_url(self):
        return f"/review/{self.id}/"

    @property
    def has_social(self):
        return bool(self.facebook_url or self.instagram_url or self.youtube_url)


# ── Menu uploads ──────────────────────────────────────────────────────────────
class MenuItem(models.Model):
    SECTION_CHOICES = [
        ('starters',    'Starters'),
        ('main_course', 'Main Course'),
        ('beverages',   'Beverages'),
        ('desserts',    'Desserts'),
        ('combos',      'Combos / Offers'),
        ('services',    'Services'),
        ('packages',    'Packages'),
        ('general',     'General'),
    ]
    FILE_TYPE_PDF   = 'pdf'
    FILE_TYPE_IMAGE = 'image'

    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    location    = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='menu_items')
    section     = models.CharField(max_length=50, choices=SECTION_CHOICES, default='general')
    title       = models.CharField(max_length=200, blank=True)
    file        = models.FileField(upload_to='menus/')
    file_type   = models.CharField(max_length=10, default='image')
    sort_order  = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sort_order', 'uploaded_at']

    def __str__(self):
        return f"{self.location} — {self.get_section_display()} ({self.file_type})"

    @property
    def is_pdf(self):
        return self.file_type == self.FILE_TYPE_PDF

    @property
    def file_url(self):
        return self.file.url if self.file else ''


# ── NEW: Offer posters ────────────────────────────────────────────────────────
class OfferPoster(models.Model):
    """
    Owner uploads offer/discount poster images.
    Shown on QR page as a grid — customer taps to see full size.
    """
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    location    = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='offer_posters')
    title       = models.CharField(max_length=200, blank=True,
                                   help_text='e.g. "20% off this weekend"')
    image       = models.ImageField(upload_to='offers/')
    is_active   = models.BooleanField(default=True)
    sort_order  = models.PositiveIntegerField(default=0)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sort_order', 'uploaded_at']

    def __str__(self):
        return f"{self.location} — {self.title or 'Offer'}"


# ── Review prompts ────────────────────────────────────────────────────────────
class ReviewPrompt(models.Model):
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    location    = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='review_prompts')
    star_rating = models.IntegerField(choices=[(4, 4), (5, 5)])
    prompt_text = models.TextField()
    used_count  = models.IntegerField(default=0)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['used_count', 'created_at']

    def __str__(self):
        return f"{self.location} — {self.star_rating}* (used:{self.used_count})"


# ── Private feedback ──────────────────────────────────────────────────────────
class PrivateFeedback(models.Model):
    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    location      = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='private_feedbacks')
    star_rating   = models.IntegerField()
    feedback_text = models.TextField(blank=True)
    contact       = models.CharField(max_length=200, blank=True)
    is_resolved   = models.BooleanField(default=False)
    submitted_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-submitted_at']


# ── Legacy ────────────────────────────────────────────────────────────────────
class Review(models.Model):
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    location    = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='reviews')
    star_rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    review_text = models.TextField()
    used_count  = models.IntegerField(default=0)
    created_at  = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['used_count']


class Scan(models.Model):
    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    location      = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='scans')
    star_selected = models.IntegerField(null=True, blank=True)
    review_chosen = models.ForeignKey(Review, on_delete=models.SET_NULL, null=True, blank=True)
    prompt_used   = models.ForeignKey(ReviewPrompt, on_delete=models.SET_NULL, null=True, blank=True)
    posted        = models.BooleanField(default=False)
    scanned_at    = models.DateTimeField(auto_now_add=True)