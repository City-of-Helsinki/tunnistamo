import factory

from users.factories import OIDCClientFactory

from .models import Api, ApiDomain, ApiScope


def create_oidc_client_for_api(api):
    domain_identifier = api.domain.identifier.rstrip('/')
    return OIDCClientFactory(client_id='{}/{}'.format(domain_identifier, api.name))


class ApiDomainFactory(factory.django.DjangoModelFactory):
    identifier = factory.Faker('url')

    class Meta:
        model = ApiDomain


class ApiFactory(factory.django.DjangoModelFactory):
    domain = factory.SubFactory(ApiDomainFactory)
    name = factory.Faker('word')
    oidc_client = factory.LazyAttribute(create_oidc_client_for_api)

    class Meta:
        model = Api


class ApiScopeFactory(factory.django.DjangoModelFactory):
    api = factory.SubFactory(ApiFactory)
    specifier = ''
    identifier = factory.LazyAttribute(ApiScope._generate_identifier)
    name = factory.Faker('word')
    description = factory.Faker('sentence')

    class Meta:
        model = ApiScope
