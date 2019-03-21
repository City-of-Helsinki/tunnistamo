from django.utils.http import quote
from social_django.middleware import SocialAuthExceptionMiddleware


class TunnistamoSocialAuthExceptionMiddleware(SocialAuthExceptionMiddleware):

    # Override get_redirect_uri to point the user back to backend selection
    # instead of non-functioning login page in case of authentication error
    def get_redirect_uri(self, request, exception):
        strategy = getattr(request, 'social_strategy', None)
        if strategy.session.get('next') is None:
            return super().get_redirect_uri(self, request, exception)
        url = '/login/?next=' + quote(strategy.session.get('next'))
        return url

    # Override raise_exception() to allow redirect also when debug is enabled
    def raise_exception(self, request, exception):
        strategy = getattr(request, 'social_strategy', None)
        if strategy is not None:
            return strategy.setting('RAISE_EXCEPTIONS')
