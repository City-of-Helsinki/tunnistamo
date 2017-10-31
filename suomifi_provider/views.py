from allauth.socialaccount import providers
from allauth.socialaccount.helpers import render_authentication_error, complete_social_login
from allauth.socialaccount.models import SocialLogin, SocialToken
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseServerError
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.settings import OneLogin_Saml2_Settings

from suomifi_provider.provider import SuomiFiProvider


def get_saml_settings(request):
    provider = providers.registry.by_id(SuomiFiProvider.id, request)
    settings_dict = provider.get_saml_settings_dict(request)

    return OneLogin_Saml2_Settings(settings=settings_dict, sp_validation_only=True)


def init_saml_auth(request):
    request_data = {
        'https': 'on' if request.is_secure() else 'off',
        'http_host': request.META['HTTP_HOST'],
        'script_name': request.META['PATH_INFO'],
        'server_port': request.META['SERVER_PORT'],
        'get_data': request.GET.copy(),
        'post_data': request.POST.copy()
    }

    saml_settings = get_saml_settings(request)
    auth = OneLogin_Saml2_Auth(request_data, old_settings=saml_settings)

    return auth


def metadata(request):
    saml_settings = get_saml_settings(request)
    metadata_xml = saml_settings.get_sp_metadata()
    errors = saml_settings.validate_metadata(metadata_xml)

    if len(errors) == 0:
        resp = HttpResponse(content=metadata_xml, content_type='text/xml')
    else:
        resp = HttpResponseServerError(content=', '.join(errors))

    return resp


def login(request):
    auth = init_saml_auth(request)
    login_url = auth.login()

    return HttpResponseRedirect(login_url)


def logout(request):
    auth = init_saml_auth(request)

    name_id = None
    session_index = None
    if 'samlNameId' in request.session:
        name_id = request.session['samlNameId']
    if 'samlSessionIndex' in request.session:
        session_index = request.session['samlSessionIndex']

    logout_url = auth.logout(name_id=name_id, session_index=session_index)

    return HttpResponseRedirect(logout_url)


class SamlAuthException(Exception):
    pass


@csrf_exempt
def assertion_consumer_service(request):
    auth = init_saml_auth(request)

    auth.process_response()
    errors = auth.get_errors()

    if not errors:
        # TODO: These are needed for the single logout
        request.session['samlNameId'] = auth.get_nameid()
        request.session['samlSessionIndex'] = auth.get_session_index()

        response_data = auth.get_attributes()

        provider = providers.registry.by_id(SuomiFiProvider.id, request)
        app = provider.get_app(request)

        login = provider.sociallogin_from_response(request, response_data)
        token = SocialToken(app=app, token="NO TOKEN", expires_at=None)
        login.token = token
        login.state = SocialLogin.state_from_request(request)

        if 'RelayState' in request.POST and request.POST.get('RelayState') != request.build_absolute_uri(
                reverse("suomifi_login")):
            login.state['next'] = request.POST.get('RelayState')

        result = complete_social_login(request, login)
    else:
        auth_exception = SamlAuthException(", ".join(errors))
        result = render_authentication_error(request, SuomiFiProvider.id, exception=auth_exception)

    return result


@csrf_exempt
def single_logout_service(request):
    auth = init_saml_auth(request)

    # TODO: Check this
    delete_session_cb = lambda: request.session.flush()
    url = auth.process_slo(delete_session_cb=delete_session_cb)
    errors = auth.get_errors()

    if len(errors) == 0:
        if url is not None:
            return HttpResponseRedirect(url)

    return HttpResponseRedirect("/")
