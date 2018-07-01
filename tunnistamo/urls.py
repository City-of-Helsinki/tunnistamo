import oauth2_provider.urls
import oidc_provider.urls
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path, re_path
from django.views.defaults import permission_denied
from rest_framework.routers import SimpleRouter

from devices.api import UserDeviceViewSet
from identities.api import UserIdentityViewSet
from oidc_apis.views import get_api_tokens_view
from tunnistamo import social_auth_urls
from users.api import UserLoginEntryViewSet
from users.views import EmailNeededView, LoginView, LogoutView

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


router = SimpleRouter()
router.register('user_identity', UserIdentityViewSet)
router.register('user_device', UserDeviceViewSet)
router.register('user_login_entry', UserLoginEntryViewSet)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api-tokens/', get_api_tokens_view),
    path('accounts/profile/', show_login),
    path('accounts/login/', LoginView.as_view()),
    path('accounts/logout/', LogoutView.as_view()),
    path('accounts/', include(social_auth_urls, namespace='social')),
    path('oauth2/applications/', permission_denied),
    path('oauth2/', include(oauth2_provider.urls, namespace='oauth2_provider')),
    path('openid/', include(oidc_provider.urls, namespace='oidc_provider')),
    re_path(r'^user/(?P<username>[\w.@+-]+)/?$', UserView.as_view()),
    path('user/', UserView.as_view()),
    path('jwt-token/', GetJWTView.as_view()),
    path('login/', LoginView.as_view()),
    path('logout/', LogoutView.as_view()),
    path('email-needed/', EmailNeededView.as_view(), name='email_needed'),
    path('v1/', include((router.urls, 'v1'))),
]

if settings.DEBUG:
    static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
