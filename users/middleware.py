from corsheaders.middleware import CorsMiddleware

from .models import AllowedOrigin
from .utils import generate_origin

CORS_HEADERS = [
    'Access-Control-Allow-Origin',
    'Access-Control-Expose-Headers',
    'Access-Control-Max-Age',
    'Access-Control-Allow-Credentials',
    'Access-Control-Allow-Methods',
    'Access-Control-Allow-Headers'
]


def validate_allowed_origin(uri, origin_match=False):
    if uri is None or uri == '':
        return False
    try:
        AllowedOrigin.objects.get(key=generate_origin(uri))
    except AllowedOrigin.DoesNotExist:
        return False
    return True


class CustomDatabaseWhitelistCorsMiddleware(CorsMiddleware):

    def origin_found_in_white_lists(self, origin, url):
        return (
            super().origin_found_in_white_lists(origin, url) or
            validate_allowed_origin(origin))

    def process_response(self, request, response):
        """
        Remove all CORS headers from previous middleware
        and views before applying own logic
        """
        for header in CORS_HEADERS:
            if header in response:
                del response[header]
        return super().process_response(request, response)
