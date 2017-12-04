import pytest

from django.utils.crypto import get_random_string

from users.models import User


@pytest.mark.django_db
def test_user_primary_sid(user_factory):
    user = User.objects.create(
        username=get_random_string,
        email='{}@example.com'.format(get_random_string)
    )

    assert user.primary_sid is not None
