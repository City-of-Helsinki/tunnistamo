import factory
from django.contrib.auth import get_user_model
from oidc_provider.tests.app.utils import create_fake_client, create_fake_token

User = get_user_model()


def access_token_factory(**kwargs):
    access_token = kwargs.pop('access_token', 'test_access_token')
    token = create_fake_token(
        user=kwargs.get('user', UserFactory()),
        client=kwargs.get('client', create_fake_client('token')),
        scopes=kwargs.get('scopes', []),
    )
    token.access_token = access_token
    token.save()
    return token


class UserFactory(factory.django.DjangoModelFactory):
    username = factory.Faker('user_name')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    email = factory.Faker('email')

    class Meta:
        model = User
