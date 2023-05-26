import logging
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model, logout
from django.shortcuts import render
from django.urls import reverse
from helusers.utils import uuid_to_username
from social_core.backends.azuread import AzureADOAuth2
from social_core.exceptions import AuthFailed
from social_django.models import UserSocialAuth

from auth_backends.adfs.base import BaseADFS
from auth_backends.adfs.helsinki import HelsinkiADFS
from auth_backends.helsinki_azure_ad import HelsinkiAzureADTenantOAuth2
from auth_backends.tunnistamo import Tunnistamo
from users.models import LoginMethod, TunnistamoSession
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
    # Some backends do not have email available for all their users, allow config to
    # bypass this check. (unused suomi.fi backend is one such)
    if backend.name in settings.EMAIL_EXEMPT_AUTH_BACKENDS:
        logger.debug(f"backend '{backend.name}' exempt from email checks")
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

    Updates the users `ADGroup`s if the user authenticated through an AD
    backend.
    """
    if not isinstance(backend, (BaseADFS, Tunnistamo, AzureADOAuth2)) or not user or 'ad_groups' not in details:
        return

    if not details['ad_groups']:
        details['ad_groups'] = []
    elif isinstance(details['ad_groups'], str):
        details['ad_groups'] = [details['ad_groups']]

    user.update_ad_groups(details['ad_groups'])


def check_existing_social_associations(backend, strategy, user=None, social=None, request=None, *args, **kwargs):
    """Deny adding additional social auths

    social_core.pipeline.social_auth.associate_user would automatically
    add additional social auths for the user, if they succesfully
    authenticated again to an IdP while holding a session with Tunnistamo.
    We don't want this to happen, as there is no interface for managing
    additional IdPs.
    """
    logger.debug(f"starting check for existing social assoc; user:{user}; backend: {backend.name}; social:{social}")
    if not user or social:
        return

    social_set = user.social_auth.all()
    providers = [a.provider for a in social_set]
    if not providers:
        return

    logger.debug(f"social does not exist; providers: {providers}")

    # This is an exception to the only-one-social-auth -rule because we want to
    # allow the user to use both on-prem AD and Azure AD simultaneously.
    if (
        (backend.name == 'helsinkiazuread' and 'helsinki_adfs' in providers) or
        (backend.name == 'helsinki_adfs' and 'helsinkiazuread' in providers)
    ):
        logger.debug('User is an AD user. Ok to have both on-prem AD and Azure AD in social auth.')
        return

    if backend.name not in providers:
        # Disallow attaching a different social auth backend to an existing user and
        # show the user which backend they used previously.
        logger.debug('User has used a different social auth provider before. Show error page.')
        strategy.request.other_logins = LoginMethod.objects.filter(provider_id__in=providers)
        error_view = AuthenticationErrorView(request=strategy.request)
        return error_view.get(strategy.request)
    else:
        # Disallow attaching a social auth from an existing social auth provider but
        # with a different user.
        logger.debug('User logged in with a same social auth provider as before but'
                     ' with a different user. Log out and fail the login.')
        # Save the existing next value from the session and add it back after log out
        # so that InterruptedSocialAuthMiddleware can redirect back to the OIDC client
        next_url = strategy.session.get('next')
        logout(request)
        if next_url:
            strategy.session_set('next', next_url)

        raise AuthFailed(backend, 'Duplicate login')


def save_social_auth_backend(backend, user=None, *args, **kwargs):
    if user:
        user.last_login_backend = backend.name
        user.save()


def create_tunnistamo_session(strategy, user=None, social=None, *args, **kwargs):
    """Create a Tunnistamo Session and add social auth entry to it

    Creates a new Tunnistamo Session if an existing session is not found and
    adds the current social auth entry to the Tunnistamo Session elements.
    """
    if not user or not social:
        return

    tunnistamo_session = TunnistamoSession.objects.get_or_create_from_request(
        strategy.request, user=user
    )

    tunnistamo_session.add_element(social)

    return {
        'tunnistamo_session': tunnistamo_session,
    }


def add_loa_to_tunnistamo_session(backend, social=None, tunnistamo_session=None, *args, **kwargs):
    """Add loa to Tunnistamo Session data

    Adds "loa" key to Tunnistamo Session data if Tunnistamo_Session has been created
    in an earlier pipeline phase and the backend in use has a `get_loa` method.
    """
    if not tunnistamo_session:
        return

    if backend.name in settings.TRUSTED_LOA_BACKENDS and hasattr(backend, 'get_loa'):
        tunnistamo_session.set_data("loa", backend.get_loa())


# TODO: Tests for this
def associate_between_helsinki_on_prem_ad_and_azure_ad(backend, details, user=None, *args, **kwargs):
    """Associates social logins between on-prem AD and Azure AD

    If the user logs in using Azure AD and there is an existing social login with
    the on-prem AD for the same AD user, we can use the same Tunnistamo user for both.
    Same thing the other way round."""
    if user:
        return

    if isinstance(backend, HelsinkiAzureADTenantOAuth2):
        existing_provider = 'helsinki_adfs'
        existing_sid_field = 'primary_sid'
        current_sid_field = 'onprem_sid'
    elif isinstance(backend, HelsinkiADFS):
        existing_provider = 'helsinkiazuread'
        existing_sid_field = 'onprem_sid'
        current_sid_field = 'primary_sid'
    else:
        return

    if not details.get(current_sid_field):
        return

    filter_args = {
        "provider": existing_provider,
        f"extra_data__{existing_sid_field}": details[current_sid_field],
    }
    existing_social_auth = UserSocialAuth.objects.filter(**filter_args).first()
    if existing_social_auth:
        logger.debug('Found existing AD user. Associating this login with the old.')
        return {
            'user': existing_social_auth.user,
        }
