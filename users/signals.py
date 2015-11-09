from django.dispatch import receiver
from allauth.account.signals import user_logged_in as allauth_user_logged_in
from djangosaml2.signals import post_authenticated as saml_user_logged_in

@receiver(allauth_user_logged_in)
def handle_allauth_login(sender, request, user, **kwargs):
    methods = set(request.session.get('login_methods', []))
    login = kwargs.get('sociallogin')
    if not login:
        return

    provider = login.account.provider
    methods.add(provider)
    request.session['login_methods'] = list(methods)
    print(methods)


@receiver(saml_user_logged_in)
def handle_saml_login(sender, **kwargs):
    print(kwargs)
