from django.conf.urls import url

import suomifi_provider.views as suomifi_views

urlpatterns = [
    url(r'^suomifi/metadata/', suomifi_views.metadata, name="suomifi_metadata"),
    url(r'^suomifi/login/', suomifi_views.login, name="suomifi_login"),
    url(r'^suomifi/logout/', suomifi_views.logout, name="suomifi_logout"),
    url(r'^suomifi/acs/', suomifi_views.assertion_consumer_service, name="suomifi_acs"),
    url(r'^suomifi/sls/', suomifi_views.single_logout_service, name="suomifi_sls"),
]
