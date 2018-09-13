import base64
import datetime

from django.utils.dateparse import parse_datetime


def get_basic_auth_header(user, password):
    """
    Return a dict containing the correct headers to set to make HTTP Basic Auth request
    """
    user_pass = "{0}:{1}".format(user, password)
    auth_string = base64.b64encode(user_pass.encode("utf-8"))
    auth_headers = {
        "HTTP_AUTHORIZATION": "Basic " + auth_string.decode("utf-8"),
    }

    return auth_headers


def check_datetimes_somewhat_equal(dt1, dt2, tolerance=datetime.timedelta(seconds=10)):
    if not isinstance(dt1, datetime.datetime):
        dt1 = parse_datetime(dt1)
    if not isinstance(dt2, datetime.datetime):
        dt2 = parse_datetime(dt2)

    assert (dt2 - dt1) < tolerance, 'gap {} is longer than {}'.format(dt2 - dt1, tolerance)
