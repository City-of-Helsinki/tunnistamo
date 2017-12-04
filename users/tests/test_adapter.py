import pytest
from allauth.account.models import EmailAddress
from allauth.socialaccount.adapter import get_adapter
from allauth.socialaccount.helpers import complete_social_login
from allauth.socialaccount.models import SocialAccount, SocialLogin
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory
from django.urls import reverse

from django.utils.crypto import get_random_string

from users.models import User


@pytest.mark.django_db
def test_is_open_for_signup_duplicate_email(user_factory, emailaddress_factory, socialaccount_factory):
    email_address = '{}@example.com'.format(get_random_string())

    user1 = user_factory(email=email_address)
    emailaddress_factory(user=user1, email=email_address)
    socialaccount_factory(user=user1, provider='facebook')

    request = RequestFactory().get('/accounts/signup/')
    request.user = AnonymousUser()

    user2 = User()
    user2.email = email_address
    email_address2 = EmailAddress(email=email_address)

    account = SocialAccount(provider='facebook', uid='123')
    sociallogin = SocialLogin(user=user2, account=account, email_addresses=[email_address2])

    assert get_adapter(request).is_open_for_signup(request, sociallogin) is False


@pytest.mark.django_db
@pytest.mark.parametrize('provider_id, expected', (
    (None, False),
    ('facebook', False),
    ('helsinki_adfs', True),
    ('espoo_adfs', False),
))
def test_is_auto_signup_allowed_override_for_helsinki_adfs(settings, provider_id, expected):
    settings.SOCIALACCOUNT_AUTO_SIGNUP = False

    request = RequestFactory().get('/accounts/signup/')

    account = SocialAccount(provider=provider_id)
    sociallogin = SocialLogin(account=account)

    assert get_adapter(request).is_auto_signup_allowed(request, sociallogin) == expected


@pytest.mark.django_db
def test_handle_facebook_without_email_cancel():
    request = RequestFactory().get('/accounts/login/callback/')
    request.user = AnonymousUser()

    account = SocialAccount(provider='facebook')
    sociallogin = SocialLogin(user=User(), account=account)
    sociallogin.state = SocialLogin.state_from_request(request)
    response = complete_social_login(request, sociallogin)

    assert response.status_code == 302
    assert response['location'].startswith(reverse('email_needed'))

    sociallogin.state['auth_params'] = 'auth_type=rerequest'

    response = complete_social_login(request, sociallogin)

    assert response.status_code == 302
    assert response['location'] == reverse('socialaccount_login_cancelled')
