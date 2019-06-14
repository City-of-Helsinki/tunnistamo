import pytest
from django.conf import settings
from django.test import override_settings

DEFAULT_CSP_SETTINGS = {
    'policy': None,
    'report_only': False,
    'report_groups': {},
}

ENABLED_CSP_SETTINGS = {
    'policy': 'default-src: \'self\'; report-uri: \'https://foo.bar/csp\'; report_to: \'grp\'',
    'report_only': False,
    'report_groups': {
        'grp': {
            'dummy': 'json'
        }
    },
}

REPORT_ONLY_CSP_SETTINGS = ENABLED_CSP_SETTINGS.copy()
REPORT_ONLY_CSP_SETTINGS['report_only'] = True
NO_REPORT_GROUPS_CSP_SETTINGS = ENABLED_CSP_SETTINGS.copy()
NO_REPORT_GROUPS_CSP_SETTINGS['report_groups'] = None


def response_has_no_csp(response):
    return (
        response.status_code == 200 and
        response.get('Content-Security-Policy') is None and
        response.get('Content-Security-Policy-Report-Only') is None
    )


@pytest.mark.django_db
@override_settings()
def test_nonexistent_settings(client):
    del settings.CONTENT_SECURITY_POLICY
    response = client.get('/login/')
    assert response_has_no_csp(response)


@pytest.mark.django_db
@override_settings(CONTENT_SECURITY_POLICY=DEFAULT_CSP_SETTINGS)
def test_default_settings(client):
    response = client.get('/login/')
    assert response_has_no_csp(response)


@pytest.mark.django_db
@override_settings()
def test_no_policy(client):
    del settings.CONTENT_SECURITY_POLICY['policy']
    response = client.get('/login/')
    assert response_has_no_csp(response)


@pytest.mark.django_db
@override_settings(CONTENT_SECURITY_POLICY=ENABLED_CSP_SETTINGS)
def test_valid_policy(client):
    response = client.get('/login/')
    assert response.status_code == 200
    assert response['Content-Security-Policy'] == ENABLED_CSP_SETTINGS['policy']
    assert response.get('Content-Security-Policy-Report-Only') is None
    assert response['Report-To'] == '{"grp": {"dummy": "json"}}'


@pytest.mark.django_db
@override_settings(CONTENT_SECURITY_POLICY=REPORT_ONLY_CSP_SETTINGS)
def test_valid_report_policy(client):
    response = client.get('/login/')
    assert response.status_code == 200
    assert response['Content-Security-Policy-Report-Only'] == ENABLED_CSP_SETTINGS['policy']
    assert response.get('Content-Security-Policy') is None
    assert response['Report-To'] == '{"grp": {"dummy": "json"}}'


@pytest.mark.django_db
@override_settings(CONTENT_SECURITY_POLICY=NO_REPORT_GROUPS_CSP_SETTINGS)
def test_valid_nongroup_policy(client):
    response = client.get('/login/')
    assert response.status_code == 200
    assert response.get('Report-To') is None
