from django.contrib import admin
from .models import (
    Business, Location, MenuItem, OfferPoster,
    ReviewPrompt, PrivateFeedback, Review, Scan,
)

@admin.register(Business)
class BusinessAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'plan', 'active', 'created_at']
    list_filter  = ['plan', 'category', 'active']

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ['name', 'business', 'address', 'created_at']

@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ['location', 'section', 'title', 'file_type', 'sort_order']
    list_filter  = ['section', 'file_type']

@admin.register(OfferPoster)
class OfferPosterAdmin(admin.ModelAdmin):
    list_display  = ['location', 'title', 'is_active', 'sort_order', 'uploaded_at']
    list_filter   = ['is_active']
    list_editable = ['is_active']

@admin.register(ReviewPrompt)
class ReviewPromptAdmin(admin.ModelAdmin):
    list_display = ['location', 'star_rating', 'used_count', 'prompt_text']
    list_filter  = ['star_rating']

@admin.register(PrivateFeedback)
class PrivateFeedbackAdmin(admin.ModelAdmin):
    list_display  = ['location', 'star_rating', 'is_resolved', 'contact', 'submitted_at']
    list_filter   = ['star_rating', 'is_resolved']
    list_editable = ['is_resolved']

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['location', 'star_rating', 'used_count']

@admin.register(Scan)
class ScanAdmin(admin.ModelAdmin):
    list_display = ['location', 'star_selected', 'posted', 'scanned_at']