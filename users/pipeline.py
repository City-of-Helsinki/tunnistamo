import uuid
from urllib.parse import urlencode

from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from django.urls import reverse
from helusers.utils import uuid_to_username

from auth_backends.adfs.base import BaseADFS
from users.models import LoginMethod
from users.views import AuthenticationErrorView


def get_user_uuid(details, backend, response, user=None, *args, **kwargs):
    """Add `new_uuid` argument to the pipeline.

    Makes sure that a `new_uuid` argument is available to other
    pipeline entries.

    If the backend provides `get_user_uuid` method (as is the case with
    the ADFS backends), it is used to generate the UUID. Otherwise, the
    UUID is generated with `uuid.uuid1` function.
    """
    if user and getattr(user, 'uuid'):
        return {
            'new_uuid': user.uuid,
        }
    if callable(getattr(backend, 'get_user_uuid', None)):
        new_uuid = backend.get_user_uuid(details, response)
    else:
        new_uuid = uuid.uuid1()

    return {
        'new_uuid': new_uuid,
    }


def get_username(strategy, user=None, *args, **kwargs):
    """Sets the `username` argument.

    If the user exists already, use the existing username. Otherwise
    generate username from the `new_uuid` using the
    `helusers.utils.uuid_to_username` function.
    """
    storage = strategy.storage

    if not user:
        user_uuid = kwargs.get('new_uuid')
        if not user_uuid:
            return

        final_username = uuid_to_username(user_uuid)
    else:
        final_username = storage.user.get_username(user)

    return {
        'username': final_username
    }


def require_email(details, backend, user=None, *args, **kwargs):
    """Enforce email address.

    Stop authentication and redirect to the `email_needed` view if the
    `details` received from the social auth doesn't include an email
    address.
    """
    if user:
        return

    # Suomi.fi returns PRC(VRK) information, which often doesn't inclue email address
    if backend.name == 'suomifi':
        return

    email = details.get('email')
    if not email:
        get_params = urlencode({
            'reauth_uri': reverse('social:begin', kwargs={'backend': backend.name}) + (
                '?auth_type=rerequest' if backend.name == 'facebook' else '')
        })
        redirect_to = reverse('email_needed') + '?' + get_params

        return redirect(redirect_to)


def associate_by_email(strategy, details, user=None, *args, **kwargs):
    """Deny duplicate email.

    Stop authentication if the email address already exists in the user
    database and the user has authenticated through one of the social
    login methods. If the email exists in one of the users, but the
    user has only authenticated using password, connect the social
    login to the user.
    """
    if user:
        return

    email = details.get('email')
    if not email:
        return

    backend = kwargs['backend']

    User = get_user_model()  # noqa
    existing_users = User.objects.filter(email__iexact=email).order_by('-date_joined')
    if not existing_users:
        return

    user = existing_users[0]

    trusted_email_domains = backend.setting('TRUSTED_EMAIL_DOMAINS', [])
    explicitly_trusted = False
    if trusted_email_domains:
        email_domain = email.split('@')[1]
        if email_domain in trusted_email_domains or trusted_email_domains == '*':
            explicitly_trusted = True

    social_set = user.social_auth.all()
    # If the account doesn't have any social logins yet, or if we
    # explicitly trust the social media provider, allow the signup.
    if explicitly_trusted or not social_set:
        return {
            'user': user,
        }

    providers = [a.provider for a in social_set]
    strategy.request.other_logins = LoginMethod.objects.filter(provider_id__in=providers)

    error_view = AuthenticationErrorView(request=strategy.request)
    return error_view.get(strategy.request)


def update_ad_groups(details, backend, user=None, *args, **kwargs):
    """Update users AD groups.

    Updates the users `ADGroup`s if the user authenticated through an ADFS
    backend.
    """
    if not isinstance(backend, BaseADFS) or not user or 'ad_groups' not in details:
        return

    user.update_ad_groups(details['ad_groups'])
