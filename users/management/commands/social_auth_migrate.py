from allauth.socialaccount.models import SocialAccount, SocialApp
from django.core.management.base import BaseCommand
from django.db import transaction
from social_django.models import UserSocialAuth


class Command(BaseCommand):
    help = 'Migrate allauth social logins to social auth'

    def add_arguments(self, parser):
        parser.add_argument('--apps', action='store_true', dest='apps',
                            help='Print social app keys and secrets')
        parser.add_argument('--accounts', action='store_true', dest='accounts',
                            help='Migrate accounts')

    def migrate_accounts(self):
        self.stdout.write(self.style.SUCCESS('Going through all SocialAccount objects...'))
        # Retrieve existing objects
        providers = {}
        for usa in UserSocialAuth.objects.all():
            provider = providers.setdefault(usa.provider, {})
            provider[usa.uid] = usa

        with transaction.atomic():
            create_objs = []
            for sa in SocialAccount.objects.all():
                provider = providers.setdefault(sa.provider, {})
                if sa.uid in provider:
                    continue
                usa = provider[sa.uid] = UserSocialAuth(
                    user=sa.user,
                    provider=sa.provider,
                    uid=sa.uid,
                    extra_data=sa.extra_data,
                )
                create_objs.append(usa)
                self.stdout.write(self.style.SUCCESS('Adding provider {}, uid {}'.format(sa.provider, sa.uid)))
                if len(create_objs) == 1000:
                    self.stdout.write(self.style.SUCCESS('Saving'))
                    UserSocialAuth.objects.bulk_create(create_objs)
                    create_objs = []

            if create_objs:
                UserSocialAuth.objects.bulk_create(create_objs)

        self.stdout.write(self.style.SUCCESS('Done.'))

    def migrate_apps(self):
        for app in SocialApp.objects.all():
            app_id = app.provider.upper()
            print("SOCIAL_AUTH_%s_KEY = '%s'" % (app_id, app.client_id))
            print("SOCIAL_AUTH_%s_SECRET = '%s'" % (app_id, app.secret))
            print()

    def handle(self, *args, **options):
        if options['apps']:
            self.migrate_apps()
        if options['accounts']:
            self.migrate_accounts()
