import logging

from django.conf import settings
from django.http import HttpResponse
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from social_core.exceptions import AuthException
from social_django.utils import load_backend, load_strategy, psa

logger = logging.getLogger(__name__)


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


@require_POST
@never_cache
@csrf_exempt
@psa()
def backchannel_logout(request, backend=None):
    try:
        if not hasattr(request.backend, 'backchannel_logout'):
            message = 'Backchannel logout is not implemented for backend "{}" '.format(
                request.backend.name
            )
            logger.warning(message)

            return HttpResponse(message, status=500)

        logger.info(f'Starting backchannel logout for backend "{request.backend.name}"')
        request.backend.backchannel_logout()

        return request.backend.strategy.html('')
    except AuthException as e:
        logger.warning(f'Error in backchannel logout for backend "{request.backend.name}": {str(e)}')
        return HttpResponse(str(e), status=400)
