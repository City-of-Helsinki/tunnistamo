import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_openid_configuration_is_consistent_between_paths(client):
    root_config_url = reverse('root-provider-info')
    oidc_provider_config_url = reverse('oidc_provider:provider-info')

    root_config = client.get(root_config_url).json()
    oidc_provider_config = client.get(oidc_provider_config_url).json()

    assert root_config == oidc_provider_config
