# Generated by Django 5.1.2 on 2025-01-25 15:21

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0005_alter_myaddress_latitude_alter_myaddress_longitude'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='order',
            name='cart',
        ),
    ]
