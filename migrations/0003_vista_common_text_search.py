# Generated by Django 3.2.9 on 2021-12-23 15:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tougshire_vistas', '0002_rename_fieldlist_vista_shown_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='vista',
            name='common_text_search',
            field=models.TextField(blank=True, help_text='The text to search on common text fields'),
        ),
    ]
