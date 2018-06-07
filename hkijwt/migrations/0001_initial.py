# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.OAUTH2_PROVIDER_APPLICATION_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='AppToAppPermission',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('requester', models.ForeignKey(related_name='+', to=settings.OAUTH2_PROVIDER_APPLICATION_MODEL, on_delete=models.CASCADE)),
                ('target', models.ForeignKey(related_name='+', to=settings.OAUTH2_PROVIDER_APPLICATION_MODEL, on_delete=models.CASCADE)),
            ],
        ),
    ]
