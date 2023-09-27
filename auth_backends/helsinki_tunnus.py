from auth_backends.helsinki_tunnistus_suomifi import HelsinkiTunnistus


class HelsinkiTunnus(HelsinkiTunnistus):
    """A subclass of HelsinkiTunnistus that only changes the name

    New backend is needed to have a second client in Helsinki tunnistus Keycloak"""
    name = 'helsinki_tunnus'
