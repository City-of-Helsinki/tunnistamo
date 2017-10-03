# -*- coding: utf-8 -*-
# Generated by Django 1.11.5 on 2017-10-03 12:54
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('oidc_provider', '0022_auto_20170331_1626'),
        ('users', '0010_add_fields_to_users_applications'),
    ]

    operations = [
        migrations.CreateModel(
            name='OidcClientOptions',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('site_type', models.CharField(choices=[('dev', 'Development'), ('test', 'Testing'), ('production', 'Production')], max_length=20, null=True, verbose_name='Site type')),
                ('include_ad_groups', models.BooleanField(default=False)),
                ('login_methods', models.ManyToManyField(to='users.LoginMethod')),
                ('oidc_client', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='+', to='oidc_provider.Client', verbose_name='OIDC client')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
