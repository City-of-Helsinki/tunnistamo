import re
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.utils import timezone
from oidc_provider.models import RSAKey

from key_manager import settings
from key_manager.models import ManagedRSAKey


@pytest.mark.django_db
class TestManageOpenidKeys(object):
    now = timezone.now()

    def test_no_keys(self):
        # there are no keys at the beginning
        self.check_key_counts(0, 0)

        call_command('manage_openid_keys')

        # there should be one managed, unexpired key, created today
        self.check_key_counts(1, 1)
        managed_key = ManagedRSAKey.objects.first()
        self.check_managed_key_ages(managed_key, self.now, None)

    def test_no_managed_keys(self):
        # create one unmanaged key
        RSAKey.objects.create(key='KEYDATA')
        self.check_key_counts(1, 0)

        call_command('manage_openid_keys')

        # there should be two managed keys
        self.check_key_counts(2, 2)
        # first one is created and expired today
        managed_key = ManagedRSAKey.objects.first()
        self.check_managed_key_ages(managed_key, self.now, self.now)
        # second one is unexpired and created today
        managed_key = ManagedRSAKey.objects.last()
        self.check_managed_key_ages(managed_key, self.now, None)

    def test_only_expired_keys(self):
        # create one expired key
        rsakey = RSAKey.objects.create(key='KEYDATA')
        managed_key = ManagedRSAKey.objects.create(rsakey=rsakey, created_at=self.now, expired_at=self.now)
        self.check_key_counts(1, 1)

        call_command('manage_openid_keys')

        # there should be two managed keys
        self.check_key_counts(2, 2)
        # first one is created and expired today
        managed_key = ManagedRSAKey.objects.first()
        self.check_managed_key_ages(managed_key, self.now, self.now)
        # second one is unexpired and created today
        managed_key = ManagedRSAKey.objects.last()
        self.check_managed_key_ages(managed_key, self.now, None)

    @pytest.mark.parametrize("age, expire", [
        (settings.get('KEY_MANAGER_RSA_KEY_MAX_AGE') - 1, False),
        (settings.get('KEY_MANAGER_RSA_KEY_MAX_AGE'),     True),
        (settings.get('KEY_MANAGER_RSA_KEY_MAX_AGE') + 1, True)
    ])
    def test_key_past_max_age(self, age, expire):
        created_at = self.now - timedelta(days=age)
        # create key with given age
        rsakey = RSAKey.objects.create(key='KEYDATA')
        managed_key = ManagedRSAKey.objects.create(rsakey=rsakey, created_at=created_at)
        self.check_key_counts(1, 1)

        call_command('manage_openid_keys')

        if expire:
            # there should be two managed keys
            self.check_key_counts(2, 2)
            # first one is created with given age and expired today
            managed_key = ManagedRSAKey.objects.first()
            self.check_managed_key_ages(managed_key, created_at, self.now)
            # second one is unexpired and created today
            managed_key = ManagedRSAKey.objects.last()
            self.check_managed_key_ages(managed_key, self.now, None)
        else:
            # there should be one unexpired key, created with given age
            self.check_key_counts(1, 1)
            managed_key = ManagedRSAKey.objects.first()
            self.check_managed_key_ages(managed_key, created_at, None)

    @pytest.mark.parametrize("age, remove", [
        (settings.get('KEY_MANAGER_RSA_KEY_EXPIRATION_PERIOD') - 1, False),
        (settings.get('KEY_MANAGER_RSA_KEY_EXPIRATION_PERIOD'),     True),
        (settings.get('KEY_MANAGER_RSA_KEY_EXPIRATION_PERIOD') + 1, True)
    ])
    def test_key_past_expiration_period(self, age, remove):
        expired_at = self.now - timedelta(days=age)
        # create key with given expiration age
        rsakey = RSAKey.objects.create(key='KEYDATA')
        ManagedRSAKey.objects.create(rsakey=rsakey, created_at=expired_at, expired_at=expired_at)
        # and an unexpired key to complement it
        rsakey = RSAKey.objects.create(key='KEYDATA-2')
        ManagedRSAKey.objects.create(rsakey=rsakey, created_at=expired_at)
        self.check_key_counts(2, 2)

        call_command('manage_openid_keys')

        if remove:
            # there should be one managed key
            self.check_key_counts(1, 1)
            # which is the unexpired one
            managed_key = ManagedRSAKey.objects.first()
            self.check_managed_key_ages(managed_key, expired_at, None)
        else:
            # there should be two keys, the expired one and the unexpired one
            self.check_key_counts(2, 2)
            managed_key = ManagedRSAKey.objects.first()
            self.check_managed_key_ages(managed_key, expired_at, expired_at)
            managed_key = ManagedRSAKey.objects.last()
            self.check_managed_key_ages(managed_key, expired_at, None)

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
    def check_key_counts(rsa_keys, managed_keys):
        assert RSAKey.objects.count() == rsa_keys
        assert ManagedRSAKey.objects.count() == managed_keys

    @staticmethod
    def check_managed_key_ages(managed_key, created_at, expired_at):
        assert managed_key.created_at.date() == created_at.date()
        assert managed_key.expired_at == expired_at or managed_key.expired_at.date() == expired_at.date()
