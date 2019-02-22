from django.urls import re_path

from . import views

app_name = 'auth_backends'

urlpatterns = [
    # Suomi.fi specific endpoints
    re_path(r'^suomifi/logout/callback/$', views.suomifi_logout_view, name='suomifi_logout_callback'),
    re_path(r'^suomifi/metadata/$', views.suomifi_metadata_view, name='suomifi_metadata'),
]
