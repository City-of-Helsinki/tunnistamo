import pytest
from httpretty import httpretty as httpretty_class


@pytest.fixture()
def httpretty():
    httpretty_class.reset()
    httpretty_class.enable()
    httpretty_class.allow_net_connect = False
    yield httpretty_class
    httpretty_class.disable()
