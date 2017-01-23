from urllib.parse import urlencode

from allauth.account.models import EmailAddress
from allauth.account.utils import user_email
from allauth.exceptions import ImmediateHttpResponse
from allauth.socialaccount import app_settings
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.utils import email_address_exists
from django.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from django.urls import reverse

from .models import LoginMethod


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        """
        Intervene social logins.

        Invoked just after a user successfully authenticates via a
        social provider, but before the login is actually processed.

        :type request: django.http.HttpRequest
        :type sociallogin: allauth.socialaccount.models.SocialLogin
        """
        if sociallogin.account.provider == 'helsinki_adfs':
            if not sociallogin.is_existing:
                link_old_helsinki_saml_users(request, sociallogin)
        elif sociallogin.account.provider == 'facebook':
            if not sociallogin.email_addresses:
                handle_facebook_without_email(sociallogin)

        trusted_providers = get_trusted_providers()
        if sociallogin.account.provider in trusted_providers:
            if not sociallogin.is_existing:
                link_by_trusted_email(request, sociallogin)

        return super(SocialAccountAdapter, self).pre_social_login(
            request, sociallogin)

    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)

        if sociallogin.account.provider == 'helsinki_adfs':
            user.primary_sid = data.get('primary_sid')
            user.department_name = data.get('department_name')

        if callable(getattr(user, 'set_username_from_uuid', None)):
            user.set_username_from_uuid()

        return user

    def clean_username(self, username, shallow=False):
        return username.lower()

    def is_auto_signup_allowed(self, request, sociallogin):
        # Always trust ADFS logins
        if sociallogin.account.provider == 'helsinki_adfs':
            return True
        # Parent checks if email is new or reserved
        parent = super(SocialAccountAdapter, self)
        return parent.is_auto_signup_allowed(request, sociallogin)

    def is_open_for_signup(self, request, sociallogin):
        email = user_email(sociallogin.user)
        # If we have a user with that email already, we don't allow
        # a signup through a new provider. Revisit this in the future.
        if email_address_exists(email):
            User = get_user_model()
            try:
                user = User.objects.get(email__iexact=email)
                social_set = user.socialaccount_set.all()
                # If the account doesn't have any social logins yet,
                # allow the signup.
                if not social_set:
                    return True
                providers = [a.provider for a in social_set]
                request.other_logins = LoginMethod.objects.filter(provider_id__in=providers)
            except User.DoesNotExist:
                request.other_logins = []
            return False
        else:
            return True


def link_old_helsinki_saml_users(request, sociallogin):
    """
    Handle linking old Helsinki SAML users to a new ADFS account.

    Check is this really a new login or is there already a previously
    created User with the UUID value: If there is, then it's an account
    which is created by the previous SAML signup and it should be
    connected to this social login instance.

    :type request: django.http.HttpRequest
    :type sociallogin: allauth.socialaccount.models.SocialLogin
    """
    assert sociallogin.account.provider == 'helsinki_adfs'
    assert not sociallogin.is_existing, "Not yet linked to user"
    uuid = sociallogin.account.uid
    user = get_user_model().objects.filter(uuid=uuid).first()
    if user:
        sociallogin.connect(request, user)


def handle_facebook_without_email(sociallogin):
    if 'rerequest' not in sociallogin.state['auth_params']:
        login_uri = reverse('facebook_login')

        # Preserve state otherwise, but override auth_params to pass in
        # "auth_type=rerequest".  This should ensure that login process
        # will continue correctly (with correct next URL, scope etc.)
        # after the rerequest.
        state = dict(sociallogin.state)
        state['auth_params'] = 'auth_type=rerequest'

        # Pass state via GET parameters
        state_params = urlencode(state)
        get_params = urlencode({'reauth_uri': login_uri + '?' + state_params})
        redirect_to = reverse('email_needed') + '?' + get_params
    else:
        redirect_to = reverse('socialaccount_login_cancelled')
    raise ImmediateHttpResponse(redirect(redirect_to))


def link_by_trusted_email(request, sociallogin):
    """
    Link social login to existing User by trusted email address.

    :type request: django.http.HttpRequest
    :type sociallogin: allauth.socialaccount.models.SocialLogin
    """
    assert not sociallogin.is_existing, "Not yet linked to user"
    for email_address in sociallogin.email_addresses:
        if email_address.verified:
            email = email_address.email
            # Note: get_users_for finds only verified email addresses
            users = EmailAddress.objects.get_users_for(email=email)
            for user in users:
                sociallogin.connect(request, user)
            unverified_emails = EmailAddress.objects.filter(
                email__iexact=email, verified=False)
            for unverified_email in unverified_emails:
                remove_email(unverified_email)


def remove_email(email_obj):
    """
    Remove email address and clean it from the user.

    :type email_obj: EmailAddress
    """
    email = email_obj.email
    user = email_obj.user
    if user.email and user.email.lower() == email.lower():
        other_emails = EmailAddress.objects.filter(
            user=user).exclude(email__iexact=email)
        if other_emails:
            user.email = other_emails.first().email
        else:
            user.email = ''
        user.save()
    email_obj.delete()


def get_trusted_providers():
    trusted_providers = set()
    for provider_name, provider_settings in app_settings.PROVIDERS.items():
        if provider_settings.get('TRUSTED', False):
            trusted_providers.add(provider_name)
    return trusted_providers
