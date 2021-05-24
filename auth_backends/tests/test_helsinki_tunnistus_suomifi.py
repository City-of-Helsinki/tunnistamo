import pytest

from auth_backends.helsinki_tunnistus_suomifi import HelsinkiTunnistus


def test_get_loa_low_without_social_auth():
    backend = HelsinkiTunnistus()

    assert backend.get_loa(None) == 'low'


@pytest.mark.django_db
@pytest.mark.parametrize('id_token_loa_value', (None, 'low', 'substantial'))
def test_get_loa(user_factory, usersocialauth_factory, id_token_loa_value):
    backend = HelsinkiTunnistus()

    user = user_factory()
    social_auth = usersocialauth_factory(provider=backend.name, user=user)

    if id_token_loa_value:
        social_auth.extra_data['id_token'] = {
            'loa': id_token_loa_value,
        }

    expected_loa_value = id_token_loa_value if id_token_loa_value else 'low'

    assert backend.get_loa(social=social_auth) == expected_loa_value