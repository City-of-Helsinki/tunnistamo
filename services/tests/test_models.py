import pytest
from django.core.exceptions import ValidationError

from services.factories import ServiceFactory
from users.factories import ApplicationFactory, OIDCClientFactory


@pytest.fixture(autouse=True)
def auto_mark_django_db(db):
    pass


def test_create_with_application():
    ServiceFactory(target='application')


def test_create_with_client():
    ServiceFactory(target='client')


def test_create_with_both_application_and_client(settings):
    settings.LANGUAGE_CODE = 'en'
    with pytest.raises(ValidationError) as e:
        ServiceFactory(application=ApplicationFactory(), client=OIDCClientFactory())
    assert 'Cannot set both application and client.' in str(e)
