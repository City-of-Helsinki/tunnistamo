from allauth.socialaccount.providers.oauth2.urls import default_urlpatterns
from .provider import YleTunnusProvider

urlpatterns = default_urlpatterns(YleTunnusProvider)
