from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.utils import email_address_exists
from allauth.account.utils import user_email


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def is_open_for_signup(self, request, sociallogin):
        email = user_email(sociallogin.user)
        # If we have a user with that email already, we don't allow
        # a signup through a new provider. Revisit this in the future.
        if email_address_exists(email):
            return False
        else:
            return True
