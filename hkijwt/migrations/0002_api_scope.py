# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-05-16 11:17
from __future__ import unicode_literals

import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import hkijwt.mixins
import multiselectfield.db.fields
import parler.models


class Migration(migrations.Migration):

    dependencies = [
        ('oidc_provider', '0020_client__post_logout_redirect_uris'),
        ('hkijwt', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Api',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=50, validators=[django.core.validators.RegexValidator('^[a-z0-9]*$', message='May contain only lower case letters and digits.')], verbose_name='name')),
                ('required_scopes', multiselectfield.db.fields.MultiSelectField(choices=[('email', 'E-mail'), ('profile', 'Profile'), ('address', 'Address'), ('github_username', 'GitHub username')], default=['email', 'profile'], help_text='Select the scopes that this API needs information from. Information from the selected scopes will be included to the ID tokens.', max_length=1000, verbose_name='required scopes')),
            ],
            options={
                'verbose_name': 'API',
                'verbose_name_plural': 'APIs',
            },
        ),
        migrations.CreateModel(
            name='ApiDomain',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('identifier', models.CharField(help_text='API domain identifier, e.g. https://api.hel.fi/auth', max_length=50, unique=True, verbose_name='identifier')),
            ],
            options={
                'verbose_name': 'API domain',
                'verbose_name_plural': 'API domains',
            },
        ),
        migrations.CreateModel(
            name='ApiScope',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('identifier', models.CharField(editable=False, help_text='The scope identifier as known by the API application (i.e. the Resource Owner).  Generated automatically from the API identifier and the scope specifier.', max_length=150, unique=True, verbose_name='identifier')),
                ('specifier', models.CharField(blank=True, help_text='If there is a need for multiple scopes per API, this can specify what kind of scope this is about, e.g. "readonly".  For general API scope just leave this empty.', max_length=30, validators=[django.core.validators.RegexValidator('^[a-z0-9]*$', message='May contain only lower case letters and digits.')], verbose_name='specifier')),
                ('allowed_apps', models.ManyToManyField(help_text='Select client applications which are allowed to get access to this API scope.', related_name='granted_api_scopes', to='oidc_provider.Client', verbose_name='allowed applications')),
                ('api', models.ForeignKey(help_text='The API that this scope is for.', on_delete=django.db.models.deletion.CASCADE, related_name='scopes', to='hkijwt.Api', verbose_name='API')),
            ],
            options={
                'verbose_name': 'API scope',
                'verbose_name_plural': 'API scopes',
            },
            bases=(hkijwt.mixins.AutoFilledIdentifier, hkijwt.mixins.ImmutableFields, parler.models.TranslatableModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name='ApiScopeTranslation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('language_code', models.CharField(db_index=True, max_length=15, verbose_name='Language')),
                ('name', models.CharField(max_length=200, verbose_name='name')),
                ('description', models.CharField(max_length=1000, verbose_name='description')),
                ('master', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='translations', to='hkijwt.ApiScope', verbose_name='API scope')),
            ],
            options={
                'verbose_name': 'API scope translation',
                'verbose_name_plural': 'API scope translations',
            },
        ),
        migrations.AddField(
            model_name='api',
            name='domain',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='hkijwt.ApiDomain', verbose_name='domain'),
        ),
        migrations.AlterUniqueTogether(
            name='apiscopetranslation',
            unique_together=set([('language_code', 'master')]),
        ),
        migrations.AlterUniqueTogether(
            name='apiscope',
            unique_together=set([('api', 'specifier')]),
        ),
        migrations.AlterUniqueTogether(
            name='api',
            unique_together=set([('domain', 'name')]),
        ),
    ]