# Generated by Django 3.2.9 on 2021-12-30 15:44

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('tougshire_vistas', '0003_vista_common_text_search'),
    ]

    operations = [
        migrations.RenameField(
            model_name='vista',
            old_name='common_text_search',
            new_name='combined_text_search',
        ),
    ]
