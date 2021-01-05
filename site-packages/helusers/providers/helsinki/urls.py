from allauth.socialaccount.providers.oauth2.urls import default_urlpatterns
from .provider import HelsinkiProvider

urlpatterns = default_urlpatterns(HelsinkiProvider)
