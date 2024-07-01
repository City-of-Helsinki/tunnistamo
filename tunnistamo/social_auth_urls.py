from django.urls import re_path
from social_django import views

app_name = 'social'

urlpatterns = [
    # authentication / association
    re_path(r'^login/(?P<backend>[^/]+)/$', views.auth, name='begin'),
    # The "complete" endpoint addresses are customized to keep the same path as with django-allauth
    # re_path(r'^complete/(?P<backend>[^/]+){0}$'.format(extra), views.complete, name='complete'),
    re_path(r'^adfs/helsinki/login/callback/$', views.complete, name='complete_helsinki_adfs',
            kwargs={'backend': 'helsinki_adfs'}),
    re_path(r'^adfs/espoo/login/callback/$', views.complete, name='complete_espoo_adfs',
            kwargs={'backend': 'espoo_adfs'}),
    re_path(r'^(?P<backend>[^/]+)/login/callback/$', views.complete, name='complete'),
    # disconnection
    re_path(r'^disconnect/(?P<backend>[^/]+)/$', views.disconnect, name='disconnect'),
    re_path(r'^disconnect/(?P<backend>[^/]+)/(?P<association_id>\d+)/$', views.disconnect,
            name='disconnect_individual'),
]
