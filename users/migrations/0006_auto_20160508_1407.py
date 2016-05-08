# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_auto_20160405_0756'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='application',
            options={'ordering': ('site_type', 'name')},
        ),
        migrations.AddField(
            model_name='application',
            name='site_type',
            field=models.CharField(max_length=20, null=True, verbose_name='Site type', choices=[('dev', 'Development'), ('test', 'Testing'), ('production', 'Production')]),
        ),
    ]
