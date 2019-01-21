from datetime import date, timedelta

from Cryptodome.PublicKey import RSA
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError
from oidc_provider.models import RSAKey

from key_manager import settings
from key_manager.models import ManagedRsaKey


class Command(BaseCommand):
    help = 'Manages default OpenID RSA key for Tunnistamo'

    def add_arguments(self, parser):
        parser.add_argument('--list-before', action='store_true', help='List keys before management cycle')
        parser.add_argument('--list-after', action='store_true', help='List keys after management cycle')

    def handle(self, *args, **options):
        # Show key summary
        if options['list_before']:
            self.list_keys()

        valid_keys = False
        # loop through all the keys
        for rsakey in RSAKey.objects.all():
            valid_keys |= self.process_rsa_key(rsakey)

        # create a new key if there are no unexpired ones
        if not valid_keys:
            self.create_managed_rsa_key()

        # Show key summary
        if options['list_after']:
            self.list_keys()

    def process_rsa_key(self, rsakey):
        # helper method for expiring managed keys
        def expire(managedkey):
            managedkey.expired = date.today()
            managedkey.save()
            self.stdout.write('Expired key with id: {0}'.format(rsakey))

        # check key for expiration
        try:
            managedkey = ManagedRsaKey.objects.get(pk=rsakey)
            if managedkey.expired:
                # remove expired key after hold period
                if managedkey.expired + timedelta(days=settings.get('KEY_MANAGER_RSA_KEY_EXPIRATION_PERIOD')) \
                        < date.today():
                    managedkey.delete()
                    rsakey.delete()
                    self.stdout.write('Removed key with id: {0}'.format(rsakey))
            else:
                # expire keys past max age
                if managedkey.created + timedelta(days=settings.get('KEY_MANAGER_RSA_KEY_MAX_AGE')) < date.today():
                    expire(managedkey)
                else:
                    return True
        # if key is not managed start managing it and expire it immediately
        except ObjectDoesNotExist:
            managedkey = self.manage_rsa_key(rsakey)
            expire(managedkey)
        return False

    def create_managed_rsa_key(self):
        """
        Create an RSA key and take it under management.
        """
        rsakey = self.create_rsa_key(settings.get('KEY_MANAGER_RSA_KEY_LENGTH'))
        self.manage_rsa_key(rsakey)

    def create_rsa_key(self, length):
        """
        Create an RSA key with a given length.
        Basically the same as oidc_provider.creatersakey but with configurable key length.
        """
        try:
            key = RSA.generate(length)
            rsakey = RSAKey(key=key.exportKey('PEM').decode('utf8'))
            rsakey.save()
            self.stdout.write('Created new key of length {0} with id: {1}'.format(length, rsakey))
            return rsakey
        except Exception as e:
            self.stdout.write('Something went wrong: {0}'.format(e))
            raise CommandError('Could not create RSA key: {0}'.format(e))

    def manage_rsa_key(self, rsakey):
        """
        Start managing an unmanaged RSA key.
        """
        managedkey = None
        try:
            managedkey = ManagedRsaKey.objects.get(pk=rsakey)
        except ObjectDoesNotExist:
            managedkey = ManagedRsaKey(key_id=rsakey, created=date.today())
            managedkey.save()
        return managedkey

    def list_keys(self):
        """
        List all RSA keys found in the database.
        """
        for rsakey in RSAKey.objects.all():
            try:
                self.stdout.write('Managed {0}'.format(ManagedRsaKey.objects.get(pk=rsakey)))
            except ObjectDoesNotExist:
                self.stdout.write('Unmanaged key: {0}'.format(rsakey))
