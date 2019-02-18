import factory

from devices.models import InterfaceDevice, UserDevice
from users.factories import UserFactory


class UserDeviceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserDevice

    user = factory.SubFactory(UserFactory)
    public_key = {'foo': 'bar'}
    secret_key = {'foo': 'bar'}
    app_version = '0.1.0'
    os = UserDevice.OS_ANDROID
    os_version = '8.1'


class InterfaceDeviceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = InterfaceDevice
