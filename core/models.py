from django.db import models

# Create your models here.
from django.db import models
from django.contrib.auth.models import User
import uuid


class Business(models.Model):
    PLAN_CHOICES = [
        ('starter', 'Starter Rs299'),
        ('growth', 'Growth Rs599'),
        ('chain', 'Chain Rs999'),
    ]
    CATEGORY_CHOICES = [
        ('restaurant', 'Restaurant / Cafe / Dhaba'),
        ('salon', 'Salon / Spa'),
        ('clinic', 'Clinic / Hospital'),
        ('gym', 'Gym / Fitness'),
        ('hotel', 'Hotel / Guesthouse'),
        ('retail', 'Retail Shop'),
        ('other', 'Other'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='business')
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES, default='starter')
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Location(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='locations')
    name = models.CharField(max_length=200)
    place_id = models.CharField(max_length=200)
    qr_image = models.ImageField(upload_to='qr_codes/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.business.name} - {self.name}"

    @property
    def google_review_url(self):
        return f"https://search.google.com/local/writereview?placeid={self.place_id}"

    @property
    def review_page_url(self):
        return f"/review/{self.id}/"


class Review(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='reviews')
    star_rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    review_text = models.TextField()
    used_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['used_count']


class Scan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='scans')
    star_selected = models.IntegerField(null=True, blank=True)
    review_chosen = models.ForeignKey(Review, on_delete=models.SET_NULL, null=True, blank=True)
    posted = models.BooleanField(default=False)
    scanned_at = models.DateTimeField(auto_now_add=True)