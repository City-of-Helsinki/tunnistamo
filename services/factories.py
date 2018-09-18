import factory
from django.contrib.auth import get_user_model

from services.models import Service
from users.factories import ApplicationFactory, OIDCClientFactory

User = get_user_model()


class ServiceFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: 'Test Service {}'.format(n))
    description = factory.Faker('paragraph')
    url = factory.Faker('url')
    application = factory.LazyAttribute(lambda o: ApplicationFactory() if o.target == 'application' else None)
    client = factory.LazyAttribute(lambda o: OIDCClientFactory() if o.target == 'client' else None)

    class Params:
        target = None

    class Meta:
        model = Service
