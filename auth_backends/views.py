from django.conf import settings
from django.http import HttpResponse
from django.urls import reverse
from social_django.utils import load_backend, load_strategy


def suomifi_metadata_view(request):
    complete_url = reverse('auth_backends:suomifi_metadata')
    saml_backend = load_backend(
        load_strategy(request),
        'suomifi',
        redirect_uri=complete_url,
    )
    metadata, errors = saml_backend.generate_metadata_xml()
    if not errors:
        return HttpResponse(content=metadata, content_type='text/xml')


def suomifi_logout_view(request, uuid=None):
    saml_backend = load_backend(
        load_strategy(request),
        'suomifi',
        redirect_uri=getattr(settings, 'LOGIN_URL'),
    )
    return saml_backend.process_logout_message()
