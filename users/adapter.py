from django.contrib.auth import get_user_model

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.utils import email_address_exists
from allauth.account.utils import user_email

from .models import LoginMethod


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(self, request, sociallogin):
        email = user_email(sociallogin.user)
        # If we have a user with that email already, we don't allow
        # a signup through a new provider. Revisit this in the future.
        if email_address_exists(email):
            User = get_user_model()
            try:
                user = User.objects.get(email__iexact=email)
                social_set = user.socialaccount_set.all()
                providers = [a.provider for a in social_set]
                request.other_logins = LoginMethod.objects.filter(provider_id__in=providers)
            except User.DoesNotExist:
                request.other_logins = []
            return False
        else:
            return True
