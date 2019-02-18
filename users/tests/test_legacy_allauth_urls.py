import pytest
from django.urls import reverse
from social_django.utils import load_backend, load_strategy


@pytest.mark.parametrize('backend_name, expected_url', (
    ('helsinki_adfs', '/accounts/adfs/helsinki/login/callback/'),
    ('github', '/accounts/github/login/callback/'),
    ('facebook', '/accounts/facebook/login/callback/'),
    ('google', '/accounts/google/login/callback/'),
))
def test_reverse_urls(backend_name, expected_url):
    """Tests that the redirect_uris stay the same as with the django allauth. Can be removed
    when all of the urls are changed."""
    strategy = load_strategy()
    uri = reverse('social:complete', kwargs={'backend': backend_name})
    backend = load_backend(strategy, backend_name, uri)

    assert backend.get_redirect_uri() == expected_url
