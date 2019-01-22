import re
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.utils import timezone
from oidc_provider.models import RSAKey

from key_manager import settings
from key_manager.models import ManagedRsaKey


@pytest.mark.django_db
class TestManageOpenidKeys(object):
    def test_no_keys(self):
        # there are no keys at the beginning
        self.check_key_counts(0, 0)

        call_command('manage_openid_keys')

        # there should be one managed, unexpired key, created today
        self.check_key_counts(1, 1)
        managed_key = ManagedRsaKey.objects.get(pk=RSAKey.objects.all().first())
        self.check_managed_key_ages(managed_key, timezone.now(), None)

    def test_no_managed_keys(self):
        # create one unmanaged key
        RSAKey.objects.create(key='KEYDATA')
        self.check_key_counts(1, 0)

        call_command('manage_openid_keys')

        # there should be two managed keys
        self.check_key_counts(2, 2)
        # first one is created and expired today
        managed_key = ManagedRsaKey.objects.get(pk=RSAKey.objects.all().first())
        self.check_managed_key_ages(managed_key, timezone.now(), timezone.now())
        # second one is unexpired and created today
        managed_key = ManagedRsaKey.objects.get(pk=RSAKey.objects.all().last())
        self.check_managed_key_ages(managed_key, timezone.now(), None)

    def test_only_expired_keys(self):
        # create one expired key
        key = RSAKey.objects.create(key='KEYDATA')
        ManagedRsaKey.objects.create(key_id=key, created=timezone.now(), expired=timezone.now())
        self.check_key_counts(1, 1)
        self.check_managed_key_ages(ManagedRsaKey.objects.get(pk=key), timezone.now(), timezone.now())

        call_command('manage_openid_keys')

        # there should be two managed keys
        self.check_key_counts(2, 2)
        # first one is created and expired today
        managed_key = ManagedRsaKey.objects.get(pk=RSAKey.objects.all().first())
        self.check_managed_key_ages(managed_key, timezone.now(), timezone.now())
        # second one is unexpired and created today
        managed_key = ManagedRsaKey.objects.get(pk=RSAKey.objects.all().last())
        self.check_managed_key_ages(managed_key, timezone.now(), None)

    @pytest.mark.parametrize("age, expire", [
        (settings.get('KEY_MANAGER_RSA_KEY_MAX_AGE') - 1, False),
        (settings.get('KEY_MANAGER_RSA_KEY_MAX_AGE'),     True),
        (settings.get('KEY_MANAGER_RSA_KEY_MAX_AGE') + 1, True)
    ])
    def test_key_past_max_age(self, age, expire):
        created = timezone.now() - timedelta(days=age)
        # create key with given age
        key = RSAKey.objects.create(key='KEYDATA')
        managed_key = ManagedRsaKey.objects.create(key_id=key, created=created)
        self.check_key_counts(1, 1)
        self.check_managed_key_ages(ManagedRsaKey.objects.get(pk=key), created, None)

        call_command('manage_openid_keys')

        if expire:
            # there should be two managed keys
            self.check_key_counts(2, 2)
            # first one is created with given age and expired today
            managed_key = ManagedRsaKey.objects.get(pk=RSAKey.objects.all().first())
            self.check_managed_key_ages(managed_key, created, timezone.now())
            # second one is unexpired and created today
            managed_key = ManagedRsaKey.objects.get(pk=RSAKey.objects.all().last())
            self.check_managed_key_ages(managed_key, timezone.now(), None)
        else:
            # there should be one unexpired key, created with given age
            self.check_key_counts(1, 1)
            managed_key = ManagedRsaKey.objects.get(pk=RSAKey.objects.all().first())
            self.check_managed_key_ages(managed_key, created, None)

    @pytest.mark.parametrize("age, remove", [
        (settings.get('KEY_MANAGER_RSA_KEY_EXPIRATION_PERIOD') - 1, False),
        (settings.get('KEY_MANAGER_RSA_KEY_EXPIRATION_PERIOD'),     True),
        (settings.get('KEY_MANAGER_RSA_KEY_EXPIRATION_PERIOD') + 1, True)
    ])
    def test_key_past_expiration_period(self, age, remove):
        expired = timezone.now() - timedelta(days=age)
        # create key with given expiration age
        key = RSAKey.objects.create(key='KEYDATA')
        ManagedRsaKey.objects.create(key_id=key, created=expired, expired=expired)
        # and an unexpired key to complement it
        key = RSAKey.objects.create(key='KEYDATA-2')
        ManagedRsaKey.objects.create(key_id=key, created=expired)

        self.check_key_counts(2, 2)
        managed_key = ManagedRsaKey.objects.get(pk=RSAKey.objects.all().first())
        self.check_managed_key_ages(managed_key, expired, expired)
        managed_key = ManagedRsaKey.objects.get(pk=RSAKey.objects.all().last())
        self.check_managed_key_ages(managed_key, expired, None)

        call_command('manage_openid_keys')

        if remove:
            # there should be one managed key
            self.check_key_counts(1, 1)
            # which is the unexpired one
            managed_key = ManagedRsaKey.objects.get(pk=RSAKey.objects.all().first())
            self.check_managed_key_ages(managed_key, expired, None)
        else:
            # there should be two keys, the expired one and the unexpired one
            self.check_key_counts(2, 2)
            managed_key = ManagedRsaKey.objects.get(pk=RSAKey.objects.all().first())
            self.check_managed_key_ages(managed_key, expired, expired)
            managed_key = ManagedRsaKey.objects.get(pk=RSAKey.objects.all().last())
            self.check_managed_key_ages(managed_key, expired, None)

    @pytest.mark.parametrize("param, line_patterns", [
        ('--list-before', [(0, r'Unmanaged.*'), (-1, r'(?!Managed).*')]),
        ('--list-after',  [(0, r'(?!Unmanaged).*'), (-1, r'Managed.*')]),
        ('--list-only',  [(0, r'Unmanaged.*'), (-1, r'Unmanaged.*')]),
    ])
    def test_list_keys(self, capsys, param, line_patterns):
        # create one unmanaged key
        RSAKey.objects.create(key='KEYDATA')
        self.check_key_counts(1, 0)

        call_command('manage_openid_keys', param)

        # check output
        output = capsys.readouterr().out.splitlines()
        for line_pattern in line_patterns:
            assert re.match(line_pattern[1], output[line_pattern[0]])

    @patch('Cryptodome.PublicKey.RSA.generate')
    def test_key_generation_failure(self, mock):
        # there are no keys at the beginning
        self.check_key_counts(0, 0)

        # when RSA key generation fails
        def mock_generate(bits):
            raise Exception('TEST')
        mock.side_effect = mock_generate

        # an exception rises
        with pytest.raises(Exception, match='TEST'):
            call_command('manage_openid_keys')

    @staticmethod
    def check_key_counts(keys, managed_keys):
        assert RSAKey.objects.count() == keys
        assert ManagedRsaKey.objects.count() == managed_keys

    @staticmethod
    def check_managed_key_ages(key, created, expired):
        assert key.created.date() == created.date()
        assert key.expired == expired or key.expired.date() == expired.date()
