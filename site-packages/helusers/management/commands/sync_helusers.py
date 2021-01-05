from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp
from helusers.providers.helsinki.provider import HelsinkiProvider


class Command(BaseCommand):
    help = 'Create or update helusers allauth SocialApp'

    def handle(self, *args, **options):
        changed = False
        try:
            app = SocialApp.objects.get(provider=HelsinkiProvider.id)
        except SocialApp.DoesNotExist:
            app = SocialApp(provider=HelsinkiProvider.id)
            self.stdout.write(self.style.SUCCESS('Creating new SocialApp'))

        if not app.name:
            app.name = 'Helsingin kaupungin työntekijät'
            changed = True

        client_id = secret_key = None

        jwt_settings = getattr(settings, 'JWT_AUTH')
        if jwt_settings:
            client_id = jwt_settings.get('JWT_AUDIENCE')
            secret_key = jwt_settings.get('JWT_SECRET_KEY')

        if not client_id:
            raise ImproperlyConfigured("You must set JWT_AUTH['JWT_AUDIENCE'] to correspond to your client ID")
        if not secret_key:
            raise ImproperlyConfigured("You must set JWT_AUTH['JWT_SECRET_KEY'] to correspond to your secret key")

        if app.client_id != client_id:
            changed = True
            app.client_id = client_id
        if app.secret != secret_key:
            changed = True
            app.secret = secret_key
        if changed:
            app.save()

        if not app.sites.exists():
            app.sites.add(Site.objects.get(id=settings.SITE_ID))
            changed = True

        if changed:
            self.stdout.write(self.style.SUCCESS('SocialApp successfully updated'))
        else:
            self.stdout.write(self.style.NOTICE('Already synced -- no changes needed'))
