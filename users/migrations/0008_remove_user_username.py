# Generated by Django 5.1.7 on 2025-04-05 07:45

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0007_user_birth_date_user_gender_user_region_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='username',
        ),
    ]
