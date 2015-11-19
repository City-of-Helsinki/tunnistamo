from django.conf import settings
from django.conf.urls import patterns, include, url
from django.contrib import admin
from django.http import HttpResponse
from django.conf.urls.static import static
from django.contrib.staticfiles import views as static_views
from django.views.defaults import permission_denied
from allauth.account.views import LogoutView
from .api import UserView, GetJWTView
from users.views import LoginView


def show_login(request):
    html = "<html><body>"
    if request.user.is_authenticated:
        html += "%s" % request.user
    else:
        html += "not logged in"
    html += "</body></html>"
    return HttpResponse(html)


urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
    url(r'^saml2/', include('djangosaml2.urls')),
    url(r'^accounts/profile/', show_login),
    url(r'^accounts/', include('allauth.urls')),
    url(r'^oauth2/applications/', permission_denied),
    url(r'^oauth2/', include('oauth2_provider.urls', namespace='oauth2_provider')),
    url(r'^user/(?P<username>[\w.@+-]+)/?$', UserView.as_view()),
    url(r'^user/$', UserView.as_view()),
    url(r'^jwt-token/$', GetJWTView.as_view()),
    url(r'^login/$', LoginView.as_view()),
    url(r'^logout/$', LogoutView.as_view())
)

if settings.DEBUG:
    urlpatterns += [url(r'^static/(?P<path>.*)$', static_views.serve)]
