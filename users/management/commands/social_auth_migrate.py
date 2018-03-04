from allauth.socialaccount.models import SocialAccount
from django.core.management.base import BaseCommand
from django.db import IntegrityError
from social_django.models import UserSocialAuth


class Command(BaseCommand):
    help = 'Migrate allauth social logins to social auth'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Going through all SocialAccount objects...'))

        # Retrieve existing objects
        providers = {}
        for usa in UserSocialAuth.objects.all():
            provider = providers.setdefault(usa.provider, {})
            provider[usa.user_id] = usa

        for sa in SocialAccount.objects.all():
            provider = providers.setdefault(sa.provider, {})
            if sa.user_id in provider:
                continue
            provider[sa.user_id] = UserSocialAuth.objects.create(
                user=sa.user,
                provider=sa.provider,
                uid=sa.uid,
                extra_data=sa.extra_data,
            )
            self.stdout.write(self.style.SUCCESS('Added. (provider: {}, uid: {})'.format(sa.provider, sa.uid)))

        self.stdout.write(self.style.SUCCESS('Done.'))
