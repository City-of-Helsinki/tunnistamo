from django.conf.urls import url, include
from .provider import ADFSProvider
from .views import oauth2_login, oauth2_callback


urlpatterns = [url('^' + ADFSProvider.id + '/', include([
    url('^(?P<realm>[-\w]+)/login/$', oauth2_login,
        name=ADFSProvider.id + "_login"),
    url('^(?P<realm>[-\w]+)/login/callback/$', oauth2_callback,
        name=ADFSProvider.id + "_callback"),
]))]
