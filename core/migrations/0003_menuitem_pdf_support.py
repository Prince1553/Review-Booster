"""
Migration 0003: PDF support for MenuItem

Changes:
- Renames `image` field → `file` (FileField, accepts PDF + images)
- Adds `file_type` field ('pdf' or 'image', default 'image')

Existing image records stay intact — their file paths in media/menus/
are unchanged. file_type defaults to 'image' for all existing rows.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_add_menu_prompts_feedback'),
    ]

    operations = [
        # Step 1: add the new file field (nullable first so existing rows don't break)
        migrations.AddField(
            model_name='menuitem',
            name='file',
            field=models.FileField(upload_to='menus/', null=True, blank=True),
        ),

        # Step 2: add file_type field
        migrations.AddField(
            model_name='menuitem',
            name='file_type',
            field=models.CharField(
                default='image', max_length=10,
                help_text="'pdf' or 'image' — set automatically on upload"
            ),
        ),

        # Step 3: copy existing image paths into file field via data migration
        migrations.RunSQL(
            sql="UPDATE core_menuitem SET file = image WHERE image IS NOT NULL AND image != '';",
            reverse_sql="UPDATE core_menuitem SET image = file WHERE file IS NOT NULL AND file != '';",
        ),

        # Step 4: make file non-nullable now that data is copied
        migrations.AlterField(
            model_name='menuitem',
            name='file',
            field=models.FileField(upload_to='menus/'),
        ),

        # Step 5: remove old image field
        migrations.RemoveField(
            model_name='menuitem',
            name='image',
        ),
    ]