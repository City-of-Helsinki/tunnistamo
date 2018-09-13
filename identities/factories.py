import factory

from identities.models import UserIdentity
from users.factories import UserFactory


class UserIdentityFactory(factory.django.DjangoModelFactory):
    service = UserIdentity.SERVICE_HELMET
    user = factory.SubFactory(UserFactory)
    identifier = factory.Faker('ean13')

    class Meta:
        model = UserIdentity
