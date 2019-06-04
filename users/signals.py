from crequest.middleware import CrequestMiddleware
from django.db.models.signals import post_save
from django.dispatch import receiver
from oauth2_provider.models import AccessToken
from oidc_provider.models import Token

from services.models import Service
from users.models import UserLoginEntry


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
