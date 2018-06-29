from allauth.account.signals import user_logged_in as allauth_user_logged_in
from crequest.middleware import CrequestMiddleware
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from oauth2_provider.models import AccessToken
from oidc_provider.models import Token

from services.models import Service
from users.models import UserLoginEntry


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


@receiver(post_save, sender=AccessToken)
def handle_oauth2_access_token_save(sender, instance, **kwargs):
    request = CrequestMiddleware.get_request()

    if not (request and instance.application):
        return

    try:
        service = Service.objects.get(application=instance.application)
    except Service.DoesNotExist:
        return

    UserLoginEntry.objects.create_from_request(request, service, user=instance.user)


@receiver(post_save, sender=Token)
def handle_oidc_token_save(sender, instance, **kwargs):
    request = CrequestMiddleware.get_request()

    if not request:
        return

    try:
        service = Service.objects.get(client=instance.client)
    except Service.DoesNotExist:
        return

    UserLoginEntry.objects.create_from_request(request, service, user=instance.user)
