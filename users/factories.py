from datetime import timedelta

import factory
from django.contrib.auth import get_user_model
from django.utils.timezone import now
from faker import Faker
from oauth2_provider.models import AccessToken
from oidc_provider.models import Client, ResponseType, UserConsent
from oidc_provider.tests.app.utils import create_fake_client, create_fake_token

from users.models import Application, UserLoginEntry

User = get_user_model()


def access_token_factory(**kwargs):
    access_token = kwargs.pop('access_token', 'test_access_token')
    token = create_fake_token(
        user=kwargs.get('user', UserFactory()),
        client=kwargs.get('client', create_fake_client('id_token')),
        scopes=kwargs.get('scopes', []),
    )
    token.access_token = access_token
    token.save()
    return token


class UserFactory(factory.django.DjangoModelFactory):
    username = factory.Sequence(lambda n: 'test_user_{}'.format(n))
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    email = factory.Faker('email')

    class Meta:
        model = User


class ApplicationFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: 'Test Application {}'.format(n))
    redirect_uris = "http://example.com"
    client_type = Application.CLIENT_CONFIDENTIAL
    authorization_grant_type = Application.GRANT_AUTHORIZATION_CODE
    skip_authorization = True

    class Meta:
        model = Application


class OIDCClientFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: 'Test Client {}'.format(n))
    client_id = factory.Faker('uuid4')
    client_secret = factory.Faker('uuid4')
    client_type = 'confidential'
    redirect_uris = ['http://example.com']
    require_consent = False

    @factory.post_generation
    def response_types(self, create, extracted, **kwargs):
        if not create:
            return
        if not extracted:
            extracted = ['code']
        for response_type in extracted:
            self.response_types.add(ResponseType.objects.get(value=response_type))

    class Meta:
        model = Client


def fake_dict():
    fake = Faker()
    return fake.pydict(10, True, 'str', 'float')


class UserLoginEntryFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory(UserFactory)
    service = factory.SubFactory('services.factories.ServiceFactory', target='client')
    timestamp = factory.LazyFunction(now)
    ip_address = factory.Faker('ipv4')
    geo_location = factory.LazyFunction(fake_dict)

    class Meta:
        model = UserLoginEntry


class UserConsentFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory(UserFactory)
    date_given = factory.LazyFunction(now)
    client = factory.SubFactory(OIDCClientFactory)
    expires_at = factory.LazyAttribute(lambda o: o.date_given + timedelta(days=1))
    scope = ['consents', 'login_entries']

    class Meta:
        model = UserConsent


class OAuth2AccessTokenFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory(UserFactory)
    application = factory.SubFactory(ApplicationFactory)
    expires = factory.LazyAttribute(lambda o: now() + timedelta(days=1))
    scope = 'read write'
    token = factory.Faker('uuid4')

    class Meta:
        model = AccessToken
