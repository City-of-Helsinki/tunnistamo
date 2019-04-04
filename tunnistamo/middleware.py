from django.http import HttpResponseForbidden
from django.utils.http import quote
from oidc_provider.lib.errors import BearerTokenError
from social_django.middleware import SocialAuthExceptionMiddleware


class TunnistamoSocialAuthExceptionMiddleware(SocialAuthExceptionMiddleware):
    # Override get_redirect_uri to point the user back to backend selection
    # instead of non-functioning login page in case of authentication error
    def get_redirect_uri(self, request, exception):
        strategy = getattr(request, 'social_strategy', None)
        if strategy.session.get('next') is None:
            return super().get_redirect_uri(request, exception)
        url = '/login/?next=' + quote(strategy.session.get('next'))
        return url

    # Override raise_exception() to allow redirect also when debug is enabled
    def raise_exception(self, request, exception):
        strategy = getattr(request, 'social_strategy', None)
        if strategy is not None:
            return strategy.setting('RAISE_EXCEPTIONS')


class TunnistamoOIDCExceptionMiddleware(object):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        if isinstance(exception, BearerTokenError):
            response = HttpResponseForbidden()
            auth_fields = [
                'error="{}"'.format(exception.code),
                'error_description="{}"'.format(exception.description)
            ]
            if 'scope' in request.POST:
                auth_fields = ['Bearer realm="{}"'.format(request.POST['scope'])] + auth_fields
            response.__setitem__('WWW-Authenticate', ', '.join(auth_fields))
            return response
