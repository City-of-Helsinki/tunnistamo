from crequest.middleware import CrequestMiddleware
from django.contrib.auth import user_logged_in
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from oauth2_provider.models import AccessToken, get_application_model
from oidc_provider.models import Client

from services.models import Service
from users.models import AllowedOrigin, Application, TunnistamoSession, UserLoginEntry
from users.utils import generate_origin


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


# FIXME: create consistent API for both Client and Application models
def _process_uris(uris):
    if isinstance(uris, list):
        return uris
    return uris.splitlines()


def generate_and_save_allowed_origins_from_client_configurations(sender, instance, **kwargs):
    uri_texts = list()
    for manager in [get_application_model().objects, Client.objects]:
        for obj in manager.all():
            for field in ['redirect_uris', 'post_logout_redirect_uris']:
                value = getattr(obj, field, None)
                if value is None or len(value) == 0:
                    continue
                uri_texts.append(value)

    valid_origins = set((generate_origin(u) for uri_text in uri_texts for u in _process_uris(uri_text)))
    persisted_origins = set(AllowedOrigin.objects.values_list('key', flat=True))

    origins_to_add = valid_origins - persisted_origins
    origins_to_delete = persisted_origins - valid_origins

    AllowedOrigin.objects.filter(key__in=origins_to_delete).delete()
    AllowedOrigin.objects.bulk_create((AllowedOrigin(key=key) for key in origins_to_add))


post_save.connect(generate_and_save_allowed_origins_from_client_configurations, sender=Application)
post_save.connect(generate_and_save_allowed_origins_from_client_configurations, sender=Client)
post_delete.connect(generate_and_save_allowed_origins_from_client_configurations, sender=Application)
post_delete.connect(generate_and_save_allowed_origins_from_client_configurations, sender=Client)


@receiver(user_logged_in)
def create_tunnistamo_session_after_login(sender, user, request, **kwargs):
    # During login the Django session might be flushed and therefore doesn't
    # have a session_key yet. Saving the session will generate a key.
    if not request.session.session_key:
        request.session.save()

    tunnistamo_session = TunnistamoSession.objects.get_or_create_from_request(
        request,
        user=user,
    )

    # Save django session key to the tunnistamo session
    if not tunnistamo_session.get_data('django_session_key'):
        tunnistamo_session.set_data(
            'django_session_key',
            request.session.session_key,
            save=True
        )
