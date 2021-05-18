import pytest
from django.contrib.auth.middleware import AuthenticationMiddleware
from django.contrib.auth.models import AnonymousUser
from django.contrib.sessions.middleware import SessionMiddleware
from django.utils import timezone
from oidc_provider.models import Token
from social_django.models import UserSocialAuth

from tunnistamo.tests.conftest import social_login
from users.models import TunnistamoSession


@pytest.mark.django_db
def test_session_gets_created_when_logging_in(client, user_factory):
    user = user_factory()

    assert TunnistamoSession.objects.count() == 0
    client.force_login(user)
    assert TunnistamoSession.objects.count() == 1


@pytest.mark.django_db
def test_django_session_key_in_tunnistamo_session(client, user):
    client.force_login(user)
    assert TunnistamoSession.objects.count() == 1
    tunnistamo_session = TunnistamoSession.objects.first()

    assert tunnistamo_session.get_data('django_session_key') == client.session.session_key


@pytest.mark.django_db
def test_correct_django_session_key_in_tunnistamo_session(client, user_factory):
    user1 = user_factory()
    user2 = user_factory()

    client.force_login(user1)

    assert TunnistamoSession.objects.count() == 1
    tunnistamo_session1 = TunnistamoSession.objects.first()
    assert tunnistamo_session1.user == user1
    assert tunnistamo_session1.get_data('django_session_key') == client.session.session_key

    client.force_login(user2)

    assert TunnistamoSession.objects.count() == 2
    tunnistamo_session2 = TunnistamoSession.objects.exclude(
        pk=tunnistamo_session1.pk
    ).first()
    assert tunnistamo_session2.user == user2
    assert tunnistamo_session2.get_data('django_session_key') == client.session.session_key


@pytest.mark.django_db
def test_social_auth_element_exists_after_social_login(settings):
    social_login(settings)

    assert TunnistamoSession.objects.count() == 1
    tunnistamo_session = TunnistamoSession.objects.first()

    assert UserSocialAuth.objects.count() == 1
    social_auth = UserSocialAuth.objects.first()

    social_auth_element = tunnistamo_session.elements.first()
    assert social_auth_element.content_object == social_auth


@pytest.mark.django_db
def test_loa_in_tunnistamo_data_after_social_login(settings):
    social_login(settings)

    assert TunnistamoSession.objects.count() == 1
    tunnistamo_session = TunnistamoSession.objects.first()

    assert tunnistamo_session.get_data('loa') == 'substantial'


@pytest.mark.django_db
def test_tunnistamo_session_set_data_save(user):
    tunnistamo_session = TunnistamoSession(user=user, created_at=timezone.now())

    assert TunnistamoSession.objects.count() == 0

    tunnistamo_session.set_data('key', 'value', save=False)
    assert TunnistamoSession.objects.count() == 0

    tunnistamo_session.set_data('key', 'value', save=True)
    assert TunnistamoSession.objects.count() == 1


@pytest.mark.django_db
def test_tunnistamo_session_set_and_get_data(user, tunnistamosession_factory):
    tunnistamo_session = tunnistamosession_factory(user=user)

    tunnistamo_session.set_data('key', 'value')
    assert tunnistamo_session.get_data('key') == 'value'


@pytest.mark.django_db
def test_tunnistamo_session_get_data_default_value(user, tunnistamosession_factory):
    tunnistamo_session = tunnistamosession_factory(user=user)

    assert tunnistamo_session.get_data('non_existent') is None
    assert tunnistamo_session.get_data('non_existent', default='default') == 'default'


@pytest.mark.django_db
def test_tunnistamo_session_add_element_cannot_add_same_twice(user, tunnistamosession_factory):
    tunnistamo_session = tunnistamosession_factory(user=user)

    social_auth = UserSocialAuth.objects.create(
        user=user,
        provider='dummy',
        uid='test_uid'
    )

    assert tunnistamo_session.elements.count() == 0

    tunnistamo_session.add_element(social_auth)
    assert tunnistamo_session.elements.count() == 1

    tunnistamo_session.add_element(social_auth)
    assert tunnistamo_session.elements.count() == 1


@pytest.mark.django_db
def test_tunnistamo_session_add_element_cannot_add_unsaved_instance(user, tunnistamosession_factory):
    tunnistamo_session = tunnistamosession_factory(user=user)

    social_auth = UserSocialAuth(
        user=user,
        provider='dummy',
        uid='test_uid'
    )

    assert tunnistamo_session.elements.count() == 0
    with pytest.raises(TypeError):
        tunnistamo_session.add_element(social_auth)
    assert tunnistamo_session.elements.count() == 0


@pytest.mark.django_db
def test_tunnistamo_session_add_element_cannot_add_non_model(user, tunnistamosession_factory):
    tunnistamo_session = tunnistamosession_factory(user=user)

    assert tunnistamo_session.elements.count() == 0
    with pytest.raises(TypeError):
        tunnistamo_session.add_element('a string')
    assert tunnistamo_session.elements.count() == 0


def _create_request_with_anonymous_user(rf):
    request = rf.get('/')
    SessionMiddleware().process_request(request)
    AuthenticationMiddleware().process_request(request)
    request.session.save()

    return request


@pytest.mark.django_db
def test_tunnistamo_session_get_elements_by_model(user, tunnistamosession_factory, oidcclient_factory):
    tunnistamo_session = tunnistamosession_factory(user=user)

    social_auth = UserSocialAuth.objects.create(
        user=user,
        provider='dummy',
        uid='test_uid'
    )
    tunnistamo_session.add_element(social_auth)

    client = oidcclient_factory(redirect_uris=[])
    token = Token.objects.create(client=client, expires_at=timezone.now())
    tunnistamo_session.add_element(token)

    assert tunnistamo_session.elements.count() == 2
    assert tunnistamo_session.get_elements_by_model(social_auth).count() == 1
    assert tunnistamo_session.get_elements_by_model(UserSocialAuth).count() == 1


@pytest.mark.django_db
def test_tunnistamo_session_get_content_object_by_model_returns_latest(user, tunnistamosession_factory):
    tunnistamo_session = tunnistamosession_factory(user=user)

    social_auth = UserSocialAuth.objects.create(
        user=user,
        provider='dummy',
        uid='test_uid'
    )
    tunnistamo_session.add_element(social_auth)

    social_auth2 = UserSocialAuth.objects.create(
        user=user,
        provider='dummy2',
        uid='test_uid'
    )
    tunnistamo_session.add_element(social_auth2)

    assert tunnistamo_session.elements.count() == 2
    assert tunnistamo_session.get_content_object_by_model(UserSocialAuth) == social_auth2


@pytest.mark.django_db
def test_tunnistamo_session_get_content_object_by_model_deleted(user, tunnistamosession_factory):
    tunnistamo_session = tunnistamosession_factory(user=user)

    social_auth = UserSocialAuth.objects.create(
        user=user,
        provider='dummy',
        uid='test_uid'
    )
    tunnistamo_session.add_element(social_auth)

    social_auth.delete()

    assert tunnistamo_session.elements.count() == 1
    assert tunnistamo_session.get_content_object_by_model(UserSocialAuth) is None


@pytest.mark.django_db
@pytest.mark.parametrize('user_value', (None, AnonymousUser()))
def test_manager_get_or_create_from_request_no_session_for_anonymous_user(rf, user_value):
    request = _create_request_with_anonymous_user(rf)

    tunnistamo_session = TunnistamoSession.objects.get_or_create_from_request(
        request,
        user=user_value,
    )

    assert tunnistamo_session is None


@pytest.mark.django_db
def test_manager_get_or_create_from_request_with_user(rf, user_factory):
    request = _create_request_with_anonymous_user(rf)

    user = user_factory()
    request.user = user

    tunnistamo_session = TunnistamoSession.objects.get_or_create_from_request(request)

    assert tunnistamo_session is not None
    assert tunnistamo_session.user == user


@pytest.mark.django_db
def test_manager_get_or_create_from_request_with_given_user(rf, user_factory):
    request = _create_request_with_anonymous_user(rf)

    user = user_factory()

    tunnistamo_session = TunnistamoSession.objects.get_or_create_from_request(
        request,
        user=user,
    )

    assert tunnistamo_session is not None
    assert tunnistamo_session.user == user


@pytest.mark.django_db
def test_manager_get_or_create_from_request_user_override(rf, user_factory):
    request = _create_request_with_anonymous_user(rf)

    user1 = user_factory()
    user2 = user_factory()

    request.user = user1

    tunnistamo_session = TunnistamoSession.objects.get_or_create_from_request(
        request,
        user=user2,
    )

    assert tunnistamo_session is not None
    assert tunnistamo_session.user == user2


@pytest.mark.django_db
def test_manager_get_or_create_from_request_session_id_not_in_django_session(rf, user_factory):
    request = _create_request_with_anonymous_user(rf)

    user = user_factory()
    request.user = user

    tunnistamo_session = TunnistamoSession.objects.get_or_create_from_request(request)
    assert tunnistamo_session is not None
    assert tunnistamo_session.user == user
    tunnistamo_session_id = request.session.get('tunnistamo_session_id')
    assert tunnistamo_session_id is not None

    del request.session['tunnistamo_session_id']

    tunnistamo_session = TunnistamoSession.objects.get_or_create_from_request(request)
    assert tunnistamo_session is not None
    assert tunnistamo_session.user == user
    assert request.session.get('tunnistamo_session_id') != tunnistamo_session_id


@pytest.mark.django_db
@pytest.mark.parametrize('add_element', (True, False))
def test_manager_get_by_element(user, tunnistamosession_factory, add_element):
    tunnistamo_session = tunnistamosession_factory(user=user)
    social_auth = UserSocialAuth.objects.create(
        user=user,
        provider='dummy',
        uid='test_uid'
    )

    if add_element:
        tunnistamo_session.add_element(social_auth)
        assert TunnistamoSession.objects.get_by_element(social_auth) == tunnistamo_session
    else:
        assert TunnistamoSession.objects.get_by_element(social_auth) is None
