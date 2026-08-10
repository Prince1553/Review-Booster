"""
Migration 0002: Add MenuItem, ReviewPrompt, PrivateFeedback, update Scan + Business

What changes:
- Business.plan: new pricing choices (₹499/999/2499/5999), default → 'solo'
- MenuItem: menu images per location
- ReviewPrompt: TOS-compliant writing prompts (replaces ghostwritten review flow)
- PrivateFeedback: private 1-3 star feedback inbox
- Scan.prompt_used: FK to ReviewPrompt (old review_chosen FK kept intact)

The original Review model is kept — existing data is safe.
"""
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [

        # 1. Update Business plan choices + default
        migrations.AlterField(
            model_name='business',
            name='plan',
            field=models.CharField(
                choices=[
                    ('solo',   'Solo ₹499/mo'),
                    ('growth', 'Growth ₹999/mo'),
                    ('chain',  'Chain ₹2499/mo'),
                    ('agency', 'Agency ₹5999/mo'),
                ],
                default='solo',
                max_length=20,
            ),
        ),

        # 2. MenuItem
        migrations.CreateModel(
            name='MenuItem',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False,
                                        primary_key=True, serialize=False)),
                ('section', models.CharField(
                    choices=[
                        ('starters',    'Starters'),
                        ('main_course', 'Main Course'),
                        ('beverages',   'Beverages'),
                        ('desserts',    'Desserts'),
                        ('combos',      'Combos / Offers'),
                        ('services',    'Services'),
                        ('packages',    'Packages'),
                        ('general',     'General'),
                    ],
                    default='general', max_length=50,
                )),
                ('title', models.CharField(blank=True, max_length=200)),
                ('image', models.ImageField(upload_to='menus/')),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('location', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='menu_items', to='core.location',
                )),
            ],
            options={'ordering': ['sort_order', 'uploaded_at']},
        ),

        # 3. ReviewPrompt (TOS-compliant writing prompts)
        migrations.CreateModel(
            name='ReviewPrompt',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False,
                                        primary_key=True, serialize=False)),
                ('star_rating', models.IntegerField(choices=[(4, 4), (5, 5)])),
                ('prompt_text', models.TextField()),
                ('used_count', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('location', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='review_prompts', to='core.location',
                )),
            ],
            options={'ordering': ['used_count']},
        ),

        # 4. PrivateFeedback
        migrations.CreateModel(
            name='PrivateFeedback',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False,
                                        primary_key=True, serialize=False)),
                ('star_rating', models.IntegerField()),
                ('feedback_text', models.TextField(blank=True)),
                ('contact', models.CharField(blank=True, max_length=200)),
                ('is_resolved', models.BooleanField(default=False)),
                ('submitted_at', models.DateTimeField(auto_now_add=True)),
                ('location', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='private_feedbacks', to='core.location',
                )),
            ],
            options={'ordering': ['-submitted_at']},
        ),

        # 5. Add prompt_used FK to Scan (old review_chosen stays — no data loss)
        migrations.AddField(
            model_name='scan',
            name='prompt_used',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to='core.reviewprompt',
            ),
        ),
    ]