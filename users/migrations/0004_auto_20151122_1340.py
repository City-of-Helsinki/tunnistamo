# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_auto_20151122_1333'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='loginmethod',
            options={'ordering': ('order',)},
        ),
        migrations.AddField(
            model_name='loginmethod',
            name='order',
            field=models.PositiveIntegerField(null=True),
        ),
    ]
