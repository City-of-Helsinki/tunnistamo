from django.dispatch import receiver
from allauth.account.signals import user_logged_in as allauth_user_logged_in
from djangosaml2.signals import post_authenticated as saml_user_logged_in
from django.utils import timezone


@receiver(allauth_user_logged_in)
def handle_allauth_login(sender, request, user, **kwargs):
    methods = set(request.session.get('login_methods', []))
    login = kwargs.get('sociallogin')
    if not login:
        return

    provider = login.account.provider
    methods.add(provider)
    request.session['login_methods'] = list(methods)
    if login.token.expires_at:
        now = timezone.now()
        delta = login.token.expires_at - now
        assert delta.total_seconds() > 0
        request.session.set_expiry(delta.total_seconds())
    else:
        request.session.set_expiry(3600)


@receiver(saml_user_logged_in)
def handle_saml_login(sender, request, **kwargs):
    request.session.set_expiry(3600)
