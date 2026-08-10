"""
Migration 0005: Website URL, social links, OfferPoster model
"""
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_location_address_keywords'),
    ]

    operations = [
        # Website + social fields on Location
        migrations.AddField(
            model_name='location',
            name='website_url',
            field=models.URLField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='location',
            name='facebook_url',
            field=models.URLField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='location',
            name='instagram_url',
            field=models.URLField(blank=True, default=''),
        ),
        migrations.AddField(
            model_name='location',
            name='youtube_url',
            field=models.URLField(blank=True, default=''),
        ),

        # OfferPoster model
        migrations.CreateModel(
            name='OfferPoster',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False,
                                        primary_key=True, serialize=False)),
                ('title', models.CharField(blank=True, max_length=200)),
                ('image', models.ImageField(upload_to='offers/')),
                ('is_active', models.BooleanField(default=True)),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('location', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='offer_posters',
                    to='core.location',
                )),
            ],
            options={'ordering': ['sort_order', 'uploaded_at']},
        ),
    ]