from django.contrib import admin

# Register your models here.
from django.contrib import admin
from .models import Business, Location, Review, Scan

@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'plan', 'active', 'created_at']

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ['name', 'business', 'place_id', 'created_at']

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['location', 'star_rating', 'used_count', 'review_text']
    list_filter = ['star_rating']

@admin.register(Scan)
class ScanAdmin(admin.ModelAdmin):
    list_display = ['location', 'star_selected', 'posted', 'scanned_at']