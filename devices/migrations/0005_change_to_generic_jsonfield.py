# Generated by Django 3.2.8 on 2021-10-21 11:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('devices', '0004_make_secret_key_longer'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userdevice',
            name='public_key',
            field=models.JSONField(verbose_name='public key'),
        ),
        migrations.AlterField(
            model_name='userdevice',
            name='secret_key',
            field=models.JSONField(verbose_name='secret key'),
        ),
    ]
