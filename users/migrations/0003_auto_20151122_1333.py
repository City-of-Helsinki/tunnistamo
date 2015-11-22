# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_auto_20151031_1511'),
    ]

    operations = [
        migrations.AddField(
            model_name='loginmethod',
            name='background_color',
            field=models.CharField(max_length=50, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='loginmethod',
            name='logo_url',
            field=models.URLField(null=True, blank=True),
        ),
        migrations.AlterField(
            model_name='user',
            name='uuid',
            field=models.UUIDField(unique=True),
        ),
    ]
