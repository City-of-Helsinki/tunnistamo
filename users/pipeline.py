import logging
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import render
from django.urls import reverse
from helusers.utils import uuid_to_username

from auth_backends.adfs.base import BaseADFS
from users.models import LoginMethod
from users.views import AuthenticationErrorView

logger = logging.getLogger(__name__)


def get_user_uuid(details, backend, response, user=None, *args, **kwargs):
    """Add `uuid` argument to the pipeline.

    Makes `uuid` argument available to other pipeline entries.

    If the backend provides `get_user_uuid` method (as is the case with
    the ADFS backends and Keycloak suomi.fi backend), it is used to
    generate the UUID. Otherwise, the UUID is generated with `uuid.uuid1`
    function.

    The argument is named same as the django-helusers `uuid` field.
    This allows syncing the helusers `uuid`-field with uuid generated
    here using SOCIAL_AUTH_backend_name_USER_FIELDS.
    """

    if user and getattr(user, 'uuid'):
        return {
            'uuid': user.uuid,
        }
    if callable(getattr(backend, 'get_user_uuid', None)):
        new_uuid = backend.get_user_uuid(details, response)
    else:
        new_uuid = uuid.uuid1()

    return {
        'uuid': new_uuid,
    }


def get_username(strategy, user=None, *args, **kwargs):
    """Sets the `username` argument.

    If the user exists already, use the existing username. Otherwise
    generate username from the `new_uuid` using the
    `helusers.utils.uuid_to_username` function.
    """
    storage = strategy.storage

    if not user:
        user_uuid = kwargs.get('uuid')
        if not user_uuid:
            return

        final_username = uuid_to_username(user_uuid)
    else:
        final_username = storage.user.get_username(user)

    return {
        'username': final_username
    }


def require_email(strategy, details, backend, user=None, *args, **kwargs):
    """Enforce email address.

    Stop authentication and render the `email_needed` template if the
    `details` received from the social auth doesn't include an email
    address.
    """
    logger.debug(f"enforcing email; user:{user}; details:{details}, backend: {backend.name}")
    if user:
        logger.debug(f"user: {user} already exists. Will not check email.")
        return
    # Suomi.fi returns PRC(VRK) information, which often doesn't inclue email address
    if backend.name == 'suomifi':
        return
    if details.get('email'):
        return

    reauth_uri = reverse('social:begin', kwargs={'backend': backend.name})
    if backend.name == 'facebook':
        reauth_uri += '?auth_type=rerequest'

    return render(strategy.request, 'email_needed.html', {'reauth_uri': reauth_uri}, status=401)


def associate_by_email(strategy, details, user=None, *args, **kwargs):
    """Deny duplicate email addresses for new users except in specific cases

    If the incoming email is associated with existing user, authentication
    is denied. Exceptions are:
    * the existing user does not have associated social login
    * the incoming email belongs to a trusted domain
    * the duplicate email address check has been disabled in the settings

    In the first two cases, the incoming social login is associated with the existing user.
    In the third case a separate new user is created.
    """
    logger.debug(f"starting association by email; user:{user}; details:{details}")

    if user:
        return
    if settings.ALLOW_DUPLICATE_EMAILS:
        return
    email = details.get('email')
    if not email:
        return

    backend = kwargs['backend']

    User = get_user_model()  # noqa
    existing_users = User.objects.filter(email__iexact=email).order_by('-date_joined')
    if not existing_users:
        return

    logger.debug(f"found existing users with email '{email}': {existing_users}")

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

    logger.debug(f"'{email}' already in use by existing user and email domain not trusted")

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


def check_existing_social_associations(backend, strategy, user=None, social=None, *args, **kwargs):
    """Deny adding additional social auths

    social_core.pipeline.social_auth.associate_user would automatically
    add additional social auths for the user, if they succesfully
    authenticated to another IdP while holding a session with Tunnistamo.
    We don't want this to happen, as there is no interface for managing
    additional IdPs.
    """
    logger.debug(f"starting check for existing social assoc; user:{user}; backend: {backend.name}; social:{social}")
    if user and not social:
        social_set = user.social_auth.all()
        providers = [a.provider for a in social_set]
        logger.debug(f"social does not exist; providers: {providers}")
        if providers and backend.name not in providers:
            strategy.request.other_logins = LoginMethod.objects.filter(provider_id__in=providers)
            error_view = AuthenticationErrorView(request=strategy.request)
            return error_view.get(strategy.request)


def save_social_auth_backend(backend, user=None, *args, **kwargs):
    if user:
        user.last_login_backend = backend.name
        user.save()
