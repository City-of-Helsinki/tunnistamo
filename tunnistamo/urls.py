import oauth2_provider.urls
import oidc_provider.urls
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
from django.urls import include, path, re_path
from django.utils import translation
from django.views.decorators.csrf import csrf_exempt
from django.views.defaults import permission_denied
from rest_framework.documentation import include_docs_urls
from rest_framework.routers import SimpleRouter
from rest_framework.schemas import SchemaGenerator

import auth_backends.urls
from devices.api import UserDeviceViewSet
from identities.api import UserIdentityViewSet
from oidc_apis.views import get_api_tokens_view
from scopes.api import ScopeListView
from services.api import ServiceViewSet
from services.views import ReportView
from tunnistamo import social_auth_urls
from users.api import TunnistamoAuthorizationView, UserConsentViewSet, UserLoginEntryViewSet
from users.views import (
    AuthoritativeLogoutRedirectView, LoginView, TunnistamoOidcAuthorizeView, TunnistamoOidcEndSessionView,
    TunnistamoOidcProviderInfoView, TunnistamoOidcTokenView, TunnistamoTokenIntrospectionView, userinfo
)

from .api import GetJWTView, UserView


def show_login(request):
    html = "<html><body>"
    if request.user.is_authenticated:
        html += "<div>%s</div>" % request.user
        if request.user.ad_groups.exists():
            html += "<h3>AD groups</h3>"
            html += "<ul>"
            for group in request.user.ad_groups.all():
                html += "<li>%s</li>" % str(group)
            html += "</ul>"
    else:
        html += "not logged in"
    html += "</body></html>"
    return HttpResponse(html)


class AllEnglishSchemaGenerator(SchemaGenerator):
    def get_schema(self, *args, **kwargs):
        with translation.override('en'):
            return super().get_schema(*args, **kwargs)


router = SimpleRouter()
router.register('user_identity', UserIdentityViewSet)
router.register('user_device', UserDeviceViewSet)
router.register('user_login_entry', UserLoginEntryViewSet)
router.register('service', ServiceViewSet)
router.register('user_consent', UserConsentViewSet)

v1_scope_path = path('scope/', ScopeListView.as_view(), name='scope-list')
v1_api_path = path('v1/', include((router.urls + [v1_scope_path], 'v1')))


urlpatterns = [
    path('admin/report/', staff_member_required(ReportView.as_view())),
    path('admin/', admin.site.urls),
    path('api-tokens/', get_api_tokens_view),
    path('accounts/profile/', show_login),
    path('accounts/login/', LoginView.as_view()),
    path('accounts/logout/', AuthoritativeLogoutRedirectView.as_view()),
    path('accounts/', include(auth_backends.urls, namespace='auth_backends')),
    path('accounts/', include(social_auth_urls, namespace='social')),
    path('oauth2/applications/', permission_denied),
    path('oauth2/authorize/', TunnistamoAuthorizationView.as_view(), name="oauth2_authorize"),
    path('oauth2/', include(oauth2_provider.urls, namespace='oauth2_provider')),
    re_path(r'^openid/authorize/?$', TunnistamoOidcAuthorizeView.as_view(), name='authorize'),
    re_path(r'^openid/end-session/?$', TunnistamoOidcEndSessionView.as_view(), name='end-session'),
    re_path(r'^openid/token/?$', csrf_exempt(TunnistamoOidcTokenView.as_view()), name='token'),
    re_path(r'^openid/userinfo/?$', csrf_exempt(userinfo), name='userinfo'),
    re_path(r'^openid/introspect/?$', TunnistamoTokenIntrospectionView.as_view(), name='token-introspection'),
    # This should shadow the openid-configuration path in the oidc_provider.urls so that
    # the same TunnistamoOidcProviderInfoView is used in both root, and openid paths.
    re_path(r'^openid/\.well-known/openid-configuration/?$', TunnistamoOidcProviderInfoView.as_view()),
    path('openid/', include(oidc_provider.urls, namespace='oidc_provider')),
    re_path(r'^\.well-known/openid-configuration/?$', TunnistamoOidcProviderInfoView.as_view(),
            name='root-provider-info'),
    re_path(r'^user/(?P<username>[\w.@+-]+)/?$', UserView.as_view()),
    path('user/', UserView.as_view()),
    path('jwt-token/', GetJWTView.as_view()),
    path('login/', LoginView.as_view()),
    path('logout/', AuthoritativeLogoutRedirectView.as_view()),
    v1_api_path,
    path('docs/', include_docs_urls(title='Tunnistamo API v1', patterns=[v1_api_path],
                                    generator_class=AllEnglishSchemaGenerator)),
]

if settings.DEBUG:
    static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


#
# Kubernetes liveness & readiness probes
#
def healthz(*args, **kwargs):
    return HttpResponse(status=200)


def readiness(*args, **kwargs):
    return HttpResponse(status=200)


urlpatterns += [
    path('healthz', healthz),
    path('readiness', readiness),
]
