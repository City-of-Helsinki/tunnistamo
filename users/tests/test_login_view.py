from urllib.parse import quote_plus

import pytest
from django.urls import reverse
from django.utils.crypto import get_random_string


@pytest.mark.django_db
def test_login_view_next_url(client, assertCountEqual, loginmethod_factory, application_factory):
    loginmethod_factory(provider_id='facebook')
    loginmethod_factory(provider_id='github')

    params = {
        "next": "http://example.com/",
    }

    response = client.get('/login/', params)

    facebook_login_url = response.context['login_methods'][0].login_url
    github_login_url = response.context['login_methods'][1].login_url

    assert facebook_login_url == reverse('social:begin', kwargs={
        'backend': 'facebook'
    }) + '?next=http%3A%2F%2Fexample.com%2F'
    assert github_login_url == reverse('social:begin', kwargs={
        'backend': 'github'
    }) + '?next=http%3A%2F%2Fexample.com%2F'


@pytest.mark.django_db
def test_login_view_all_loginmethods(client, assertCountEqual, loginmethod_factory, application_factory):
    lm1 = loginmethod_factory(provider_id='facebook')
    lm2 = loginmethod_factory(provider_id='github')

    response = client.get('/login/')

    assertCountEqual(response.context['login_methods'], [lm1, lm2])


@pytest.mark.django_db
def test_login_view_one_loginmethod_redirect(client, loginmethod_factory):
    loginmethod_factory(provider_id='facebook')

    response = client.get('/login/')

    assert response.status_code == 302
    assert response['location'] == reverse('social:begin', kwargs={
        'backend': 'facebook'
    })


@pytest.mark.django_db
def test_login_view_ignore_unknown_app(client, loginmethod_factory, application_factory):
    loginmethod_factory(provider_id='facebook')

    params = {
        "next": "http://example.com/?client_id={}".format(get_random_string()),
    }

    response = client.get('/login/', params)

    assert response.status_code == 302
    assert response['location'] == '{}?next={}'.format(reverse('social:begin', kwargs={
        'backend': 'facebook'
    }), quote_plus(params['next']))


@pytest.mark.django_db
def test_login_view_loginmethods_per_app(client, loginmethod_factory, application_factory):
    loginmethod_factory(provider_id='facebook')
    lm2 = loginmethod_factory(provider_id='github')

    redirect_uris = ['http://example.com/']
    login_methods = [lm2]

    app = application_factory(redirect_uris=redirect_uris)
    app.login_methods.set(login_methods)
    app.save()

    params = {
        "next": "http://example.com/?client_id={}".format(app.client_id),
    }

    response = client.get('/login/', params)

    assert response.status_code == 302
    assert response['location'] == '{}?next={}'.format(reverse('social:begin', kwargs={
        'backend': 'github'
    }), quote_plus(params['next']))


@pytest.mark.django_db
def test_login_view_loginmethods_per_app_empty(client, loginmethod_factory, application_factory):
    loginmethod_factory(provider_id='facebook')
    loginmethod_factory(provider_id='github')

    redirect_uris = ['http://example.com/']

    app = application_factory(redirect_uris=redirect_uris)
    app.login_methods.set([])
    app.save()

    params = {
        "next": "http://example.com/?client_id={}".format(app.client_id),
    }

    response = client.get('/login/', params)

    assert response.context['login_methods'] == []


@pytest.mark.django_db
def test_login_view_loginmethods_per_oidcclient(client, assertCountEqual, loginmethod_factory, oidcclient_factory,
                                                oidcclientoptions_factory):
    lm1 = loginmethod_factory(provider_id='facebook')
    lm2 = loginmethod_factory(provider_id='github')
    lm3 = loginmethod_factory(provider_id='google')

    redirect_uris = ['http://example.com/']

    oidc_client = oidcclient_factory(redirect_uris=redirect_uris)
    oidc_client.save()

    params = {
        "next": "http://example.com/?client_id={}".format(oidc_client.client_id),
    }

    response = client.get('/login/', params)

    assertCountEqual(response.context['login_methods'], [lm1, lm2, lm3])

    login_methods = [lm2, lm3]

    oidcclient_options = oidcclientoptions_factory(oidc_client=oidc_client)
    oidcclient_options.login_methods.set(login_methods)
    oidcclient_options.save()

    response = client.get('/login/', params)

    assertCountEqual(response.context['login_methods'], login_methods)


@pytest.fixture
def oidc_client(
    loginmethod_factory, oidcclient_factory, oidcclientoptions_factory
):
    oidc_client = oidcclient_factory(redirect_uris=['https://example.com/'])
    oidc_client_options = oidcclientoptions_factory(oidc_client=oidc_client)
    oidc_client_options.login_methods.set([
        loginmethod_factory(provider_id='facebook'),
        loginmethod_factory(provider_id='github'),
        loginmethod_factory(provider_id='google'),
    ]),

    return oidc_client


@pytest.mark.django_db
def test_login_view_one_valid_idp_hint_should_redirect(client, oidc_client):
    login_method = oidc_client.options.login_methods.first()

    params = {
        'next': f'/openid/authorize?client_id={oidc_client.client_id}',
        'idp_hint': login_method.provider_id,
    }

    response = client.get('/login/', params)

    assert response.status_code == 302
    assert response['Location'].startswith(
        reverse('social:begin', kwargs={'backend': login_method.provider_id})
    )


@pytest.mark.django_db
def test_login_view_two_valid_idp_hints(
    client, oidc_client, assertCountEqual
):
    login_methods = oidc_client.options.login_methods.all()[:2]

    params = {
        'next': f'/openid/authorize?client_id={oidc_client.client_id}',
        'idp_hint': ','.join([login_method.provider_id for login_method in login_methods]),
    }

    response = client.get('/login/', params)

    assertCountEqual(response.context['login_methods'], login_methods)


@pytest.mark.django_db
def test_login_view_not_allowed_provider_in_idp_hint_should_not_be_included(
    client, oidc_client, loginmethod_factory, assertCountEqual
):
    login_methods = list(oidc_client.options.login_methods.all())
    not_allowed_login_method = loginmethod_factory(provider_id='helsinki_adfs')

    params = {
        'next': f'/openid/authorize?client_id={oidc_client.client_id}',
        'idp_hint': ','.join([
            login_method.provider_id for login_method in login_methods + [not_allowed_login_method]
        ]),
    }

    response = client.get('/login/', params)

    assertCountEqual(response.context['login_methods'], login_methods)


@pytest.mark.django_db
def test_login_view_unknown_provider_in_idp_hint_should_not_be_included_and_no_error(
    client, oidc_client, loginmethod_factory, assertCountEqual
):
    login_methods = oidc_client.options.login_methods.all()

    idp_hint = ','.join([login_method.provider_id for login_method in login_methods])
    idp_hint += ',unknown_provider_id'

    params = {
        'next': f'/openid/authorize?client_id={oidc_client.client_id}',
        'idp_hint': idp_hint,
    }

    response = client.get('/login/', params)

    assertCountEqual(response.context['login_methods'], login_methods)


@pytest.mark.django_db
def test_login_view_single_non_allowed_provider_in_idp_hint_should_show_all_login_methods_in_client(
    client, oidc_client, loginmethod_factory, assertCountEqual
):
    login_methods = oidc_client.options.login_methods.all()
    not_allowed_login_method = loginmethod_factory(provider_id='helsinki_adfs')

    params = {
        'next': f'/openid/authorize?client_id={oidc_client.client_id}',
        'idp_hint': not_allowed_login_method.provider_id,
    }

    response = client.get('/login/', params)

    assertCountEqual(response.context['login_methods'], login_methods)


@pytest.mark.django_db
def test_login_view_unknown_idp_hint_should_show_all_login_methods_in_client(
    client, oidc_client, assertCountEqual
):
    login_methods = oidc_client.options.login_methods.all()

    params = {
        'next': f'/openid/authorize?client_id={oidc_client.client_id}',
        'idp_hint': 'unknown_provider_id',
    }

    response = client.get('/login/', params)

    assertCountEqual(response.context['login_methods'], login_methods)
