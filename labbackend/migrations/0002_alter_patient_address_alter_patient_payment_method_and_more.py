# Generated by Django 4.1.13 on 2024-12-10 03:51

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('labbackend', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='patient',
            name='address',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='patient',
            name='payment_method',
            field=models.JSONField(blank=True),
        ),
        migrations.AlterField(
            model_name='patient',
            name='sample_collector',
            field=models.CharField(blank=True, max_length=100),
        ),
    ]