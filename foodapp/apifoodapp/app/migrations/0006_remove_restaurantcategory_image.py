# Generated by Django 5.1.2 on 2024-12-17 15:04

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0005_menu_food'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='restaurantcategory',
            name='image',
        ),
    ]
