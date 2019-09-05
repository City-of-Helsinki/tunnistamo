from urllib.parse import urlparse

from django.conf import settings
from django.contrib.gis.geoip2 import GeoIP2
from geoip2.errors import AddressNotFoundError


def get_geo_location_data_for_ip(ip_address):
    if not hasattr(settings, 'GEOIP_PATH'):
        return None

    g = GeoIP2()
    try:
        location = g.city(ip_address)
    except AddressNotFoundError:
        location = None

    return location


def generate_origin(uri):
    """Calculates a normalized origin from an arbitrary URI, to be used in
    CORS origin verifications.
    """
    try:
        parsed = urlparse(uri)
        return "{}://{}".format(parsed.scheme, parsed.netloc)
    except ValueError:
        return None
