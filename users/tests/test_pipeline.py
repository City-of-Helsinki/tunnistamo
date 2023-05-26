import pytest
from django.contrib import auth
from django.urls import reverse
from django.utils.crypto import get_random_string
from social_core.exceptions import AuthFailed
from social_django.utils import load_backend, load_strategy

from tunnistamo.tests.conftest import create_rsa_key, reload_social_django_utils
from users.pipeline import update_ad_groups
from users.tests.conftest import DummyFixedOidcBackend


@pytest.fixture
def dummy_backend(settings):
    create_rsa_key()

    settings.AUTHENTICATION_BACKENDS = settings.AUTHENTICATION_BACKENDS + (
        'users.tests.conftest.DummyFixedOidcBackend',
    )
    settings.SOCIAL_AUTH_DUMMYFIXEDOIDCBACKEND_OIDC_ENDPOINT = 'https://dummy.example.com'
    settings.SOCIAL_AUTH_DUMMYFIXEDOIDCBACKEND_KEY = 'tunnistamo'
    settings.EMAIL_EXEMPT_AUTH_BACKENDS = [DummyFixedOidcBackend.name]

    reload_social_django_utils()


def request_social_complete(client):
    state_value = get_random_string()
    session = client.session
    session[f'{DummyFixedOidcBackend.name}_state'] = state_value
    session.save()

    complete_url = reverse('social:complete', kwargs={
        'backend': DummyFixedOidcBackend.name
    })

    return client.get(complete_url, data={'state': state_value}, follow=False)


@pytest.mark.django_db
def test_second_social_login_same_provider_different_uid(client, settings, dummy_backend):
    # Log the user in by completing dummy backend auth
    settings.SOCIAL_AUTH_DUMMYFIXEDOIDCBACKEND_SUB_VALUE = 'first_sub_value'
    request_social_complete(client)
    user = auth.get_user(client)

    # Change the sub value and complete dummy backend auth again
    settings.SOCIAL_AUTH_DUMMYFIXEDOIDCBACKEND_SUB_VALUE = 'second_sub_value'

    # The social login should fail because it shouldn't be possible to
    # attach a second social login to the already logged-in user with the same backend
    # but with a different user in the backend.
    with pytest.raises(AuthFailed):
        request_social_complete(client)

    assert user.social_auth.count() == 1
    assert not auth.get_user(client).is_authenticated


@pytest.mark.django_db
@pytest.mark.parametrize('ad_groups,expected', (
    (None, []),
    ('', []),
    ([], []),
    ('group1', ['group1']),
    (['group1'], ['group1']),
    (['group1', 'group2'], ['group1', 'group2']),
), ids=repr)
def test_update_ad_groups_pipeline_part_should_work_with_variety_of_values_from_ad(
    user, assertCountEqual, ad_groups, expected
):
    backend_name = 'helsinki_adfs'
    strategy = load_strategy()
    uri = reverse('social:complete', kwargs={'backend': backend_name})
    backend = load_backend(strategy, backend_name, uri)
    details = {'ad_groups': ad_groups}

    update_ad_groups(details, backend, user)

    assertCountEqual(user.ad_groups.all().values_list('name', flat=True), expected)
