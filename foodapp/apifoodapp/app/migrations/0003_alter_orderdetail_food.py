# Generated by Django 5.1.2 on 2025-01-12 15:01

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0002_order_order_date_alter_orderdetail_order'),
    ]

    operations = [
        migrations.AlterField(
            model_name='orderdetail',
            name='food',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='food_details', to='app.food'),
        ),
    ]
