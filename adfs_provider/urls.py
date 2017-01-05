from django.conf.urls import include, url

from .views import ADFSOAuth2Adapter, HelsinkiADFSOAuth2Adapter, \
    EspooADFSOAuth2Adapter


def get_urlpatterns(adapter_cls):
    assert issubclass(adapter_cls, ADFSOAuth2Adapter)
    return [
        url('^adfs/' + adapter_cls.realm + '/', include([
            url('^login/$', adapter_cls.get_login_view(),
                name=(adapter_cls.provider_id + "_login")),
            url('^login/callback/$', adapter_cls.get_callback_view(),
                name=(adapter_cls.provider_id + "_callback")),
        ])),
    ]

urlpatterns = get_urlpatterns(HelsinkiADFSOAuth2Adapter)
urlpatterns += get_urlpatterns(EspooADFSOAuth2Adapter)
