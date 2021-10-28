# Generated by Django 2.2.24 on 2021-08-25 12:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('oidc_apis', '0002_add_multiselect_field_ad_groups_option'),
    ]

    operations = [
        migrations.AddField(
            model_name='api',
            name='backchannel_logout_url',
            field=models.URLField(blank=True, help_text='If this URL is given Tunnistamo will send an OIDC Log Out token to the API when the user logs out. e.g. in APIs using Helusers the URL would be [helusers.urls path]/logout/oidc/backchannel/', null=True, verbose_name='Back-channel log out URL'),
        ),
    ]