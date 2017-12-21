from django.conf.urls import url
from social_django import views

app_name = 'social'

urlpatterns = [
    # authentication / association
    url(r'^login/(?P<backend>[^/]+)/$', views.auth, name='begin'),
    # The "complete" endpoint addresses are customized to keep the same path as with django-allauth
    # url(r'^complete/(?P<backend>[^/]+){0}$'.format(extra), views.complete, name='complete'),
    url(r'^adfs/helsinki/login/callback/$', views.complete, name='complete_helsinki_adfs',
        kwargs={'backend': 'helsinki_adfs'}),
    url(r'^adfs/espoo/login/callback/$', views.complete, name='complete_espoo_adfs',
        kwargs={'backend': 'espoo_adfs'}),
    url(r'^(?P<backend>[^/]+)/login/callback/$', views.complete, name='complete'),
    # disconnection
    url(r'^disconnect/(?P<backend>[^/]+)/$', views.disconnect, name='disconnect'),
    url(r'^disconnect/(?P<backend>[^/]+)/(?P<association_id>\d+)/$', views.disconnect,
        name='disconnect_individual'),
]
