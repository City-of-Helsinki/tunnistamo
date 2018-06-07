import pytest
from django.urls import reverse
from django.utils.crypto import get_random_string
from django.utils.http import urlquote


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
    }) + '?next=http%3A//example.com/'
    assert github_login_url == reverse('social:begin', kwargs={
        'backend': 'github'
    }) + '?next=http%3A//example.com/'


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
    }), urlquote(params['next']))


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
    }), urlquote(params['next']))


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
