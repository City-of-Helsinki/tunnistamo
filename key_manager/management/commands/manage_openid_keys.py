from datetime import timedelta

from Cryptodome.PublicKey import RSA
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand
from django.utils import timezone
from oidc_provider.models import RSAKey

from key_manager import settings
from key_manager.models import ManagedRSAKey


class Command(BaseCommand):
    help = 'Manages default OpenID RSA key for Tunnistamo'

    def add_arguments(self, parser):
        parser.add_argument('--list-before', action='store_true', help='List keys before management cycle')
        parser.add_argument('--list-after', action='store_true', help='List keys after management cycle')
        parser.add_argument('--list-only', action='store_true', help='Only list keys, do not manage')

    def handle(self, *args, **options):
        # Show key summary
        if options['list_before'] or options['list_only']:
            self.list_keys()
        if options['list_only']:
            return

        now = timezone.now()
        valid_keys = False
        # loop through all the keys
        for rsakey in RSAKey.objects.all():
            # check if key is managed, and if not, create it
            managedkey, created = ManagedRSAKey.objects.get_or_create(
                rsakey=rsakey,
                defaults={'created_at': now, 'expired_at': now})
            if created:
                # if key was not managed it is now considered expired
                self.stdout.write('Expired key with id: {0}'.format(rsakey))
            elif managedkey.expired_at:
                # remove expired key after hold period
                if managedkey.expired_at + timedelta(days=settings.get('KEY_MANAGER_RSA_KEY_EXPIRATION_PERIOD')) < now:
                    rsakey.delete()
                    self.stdout.write('Removed key with id: {0}'.format(rsakey))
            elif managedkey.created_at + timedelta(days=settings.get('KEY_MANAGER_RSA_KEY_MAX_AGE')) < now:
                # expire key older than maximum age
                managedkey.expired_at = now
                managedkey.save()
                self.stdout.write('Expired key with id: {0}'.format(rsakey))
            else:
                # valid key was found
                valid_keys = True

        # create a new key if there are no unexpired ones
        if not valid_keys:
            self.create_managed_rsa_key(settings.get('KEY_MANAGER_RSA_KEY_LENGTH'))

        # Show key summary
        if options['list_after']:
            self.list_keys()

    def create_managed_rsa_key(self, length):
        """
        Create an RSA key with a given length.
        Basically the same as oidc_provider.creatersakey but with configurable key length.
        """
        key = RSA.generate(length)
        rsakey = RSAKey.objects.create(key=key.exportKey('PEM').decode('utf8'))
        ManagedRSAKey.objects.create(rsakey=rsakey, created_at=timezone.now())
        self.stdout.write('Created new key of length {0} with id: {1}'.format(length, rsakey))

    def list_keys(self):
        """
        List all RSA keys found in the database.
        """
        for rsakey in RSAKey.objects.all():
            try:
                self.stdout.write('Managed {0}'.format(ManagedRSAKey.objects.get(rsakey=rsakey)))
            except ObjectDoesNotExist:
                self.stdout.write('Unmanaged key: {0}'.format(rsakey))
