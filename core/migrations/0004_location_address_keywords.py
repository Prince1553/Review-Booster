"""
Migration 0004: Add address, custom_keywords to Location.
Remove required place_id (now optional).
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_menuitem_pdf_support'),
    ]

    operations = [
        # address field
        migrations.AddField(
            model_name='location',
            name='address',
            field=models.TextField(
                blank=True,
                help_text='Full business address',
                default='',
            ),
        ),
        # custom_keywords field
        migrations.AddField(
            model_name='location',
            name='custom_keywords',
            field=models.TextField(
                blank=True,
                default='',
                help_text='Comma-separated keywords e.g. "biryani, quick service"',
            ),
        ),
        # Make place_id optional (blank=True)
        migrations.AlterField(
            model_name='location',
            name='place_id',
            field=models.CharField(max_length=200, blank=True, default=''),
        ),
    ]