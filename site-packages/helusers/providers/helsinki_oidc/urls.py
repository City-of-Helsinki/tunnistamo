from allauth.socialaccount.providers.oauth2.urls import default_urlpatterns
from .provider import HelsinkiOIDCProvider

urlpatterns = default_urlpatterns(HelsinkiOIDCProvider)
