from urllib.parse import urlencode

from allauth.account.utils import user_email
from allauth.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.utils import email_address_exists
from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from django.urls import reverse

from .models import LoginMethod


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        if sociallogin.account.provider == 'helsinki_adfs':
            if not sociallogin.is_existing:
                # Check is this really a new login or is there already a
                # previously created User with the UUID value: If there
                # is, then it's an account which is created by the
                # previous SAML signup and it should be connected to
                # this social login instance.
                uuid = sociallogin.account.uid
                user = get_user_model().objects.filter(uuid=uuid).first()
                if user:
                    sociallogin.connect(request, user)
        elif sociallogin.account.provider == 'facebook':
            if not sociallogin.email_addresses:
                handle_facebook_without_email(sociallogin)

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


def handle_facebook_without_email(sociallogin):
    if 'rerequest' not in sociallogin.state['auth_params']:
        login_uri = reverse('facebook_login')
        auth_params = urlencode({'auth_params': 'auth_type=rerequest'})
        get_params = urlencode({'reauth_uri': login_uri + '?' + auth_params})
        redirect_to = reverse('email_needed') + '?' + get_params
    else:
        redirect_to = reverse('socialaccount_login_cancelled')
    raise ImmediateHttpResponse(redirect(redirect_to))
