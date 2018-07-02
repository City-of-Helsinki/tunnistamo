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
