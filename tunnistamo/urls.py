import allauth.urls
import oauth2_provider.urls
import oidc_provider.urls
from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.contrib.staticfiles import views as static_views
from django.http import HttpResponse
from django.views.defaults import permission_denied

from oidc_apis.views import get_api_tokens_view
from users.views import EmailNeededView, LoginView, LogoutView

from .api import GetJWTView, UserView
from .oidc import patch_oidc_provider_user_consent_handling

patch_oidc_provider_user_consent_handling()


def show_login(request):
    html = "<html><body>"
    if request.user.is_authenticated:
        html += "%s" % request.user
    else:
        html += "not logged in"
    html += "</body></html>"
    return HttpResponse(html)


urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^api-tokens/?$', get_api_tokens_view),
    url(r'^accounts/profile/', show_login),
    url(r'^accounts/login/', LoginView.as_view()),
    url(r'^accounts/logout/', LogoutView.as_view()),
    url(r'^accounts/', include(allauth.urls)),
    url(r'^oauth2/applications/', permission_denied),
    url(r'^oauth2/', include(oauth2_provider.urls, namespace='oauth2_provider')),
    url(r'^openid/', include(oidc_provider.urls, namespace='oidc_provider')),
    url(r'^user/(?P<username>[\w.@+-]+)/?$', UserView.as_view()),
    url(r'^user/$', UserView.as_view()),
    url(r'^jwt-token/$', GetJWTView.as_view()),
    url(r'^login/$', LoginView.as_view()),
    url(r'^logout/$', LogoutView.as_view()),
    url(r'^email-needed/$', EmailNeededView.as_view(), name='email_needed'),
]

if settings.DEBUG:
    urlpatterns += [url(r'^static/(?P<path>.*)$', static_views.serve)]
