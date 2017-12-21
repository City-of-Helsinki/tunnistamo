from allauth.socialaccount.models import SocialAccount
from django.core.management.base import BaseCommand
from django.db import IntegrityError
from social_django.models import UserSocialAuth


class Command(BaseCommand):
    help = 'Migrate allauth social logins to social auth'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Going through all SocialAccount objects...'))
        for sa in SocialAccount.objects.all():
            provider_id = sa.provider

            try:
                UserSocialAuth.objects.create(
                    user=sa.user,
                    provider=provider_id,
                    uid=sa.uid,
                    extra_data=sa.extra_data,
                )
                self.stdout.write(self.style.SUCCESS('Added. (provider: {}, uid: {})'.format(provider_id, sa.uid)))
            except IntegrityError:
                self.stdout.write(self.style.WARNING('UserSocialAuth already exists. (provider: {}, uid: {})'.format(
                    provider_id, sa.uid)))

        self.stdout.write(self.style.SUCCESS('Done.'))
