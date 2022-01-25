# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import parler.models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='LoginMethod',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('provider_id', models.CharField(unique=True, max_length=50)),
                ('name', models.CharField(max_length=100, default='-')),
            ],
            bases=(parler.models.TranslatableModelMixin, models.Model),
        ),
        migrations.AddField(
            model_name='application',
            name='login_methods',
            field=models.ManyToManyField(to='users.LoginMethod'),
        ),
    ]
