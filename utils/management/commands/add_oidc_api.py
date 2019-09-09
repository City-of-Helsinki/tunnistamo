from django.core.management.base import BaseCommand
from django.db import transaction
from oidc_provider.models import Client

from oidc_apis.models import Api, ApiDomain


class Command(BaseCommand):
    help = "Add OpenID Connect API"

    def add_arguments(self, parser):
        parser.add_argument("-n", "--name", type=str, help="Name of API", required=True)
        parser.add_argument(
            "-d", "--domain", type=str, help="Domain Identifier", required=True
        )
        parser.add_argument(
            "-s", "--scopes", nargs="+", type=str, help="API Scopes", required=True
        )
        parser.add_argument(
            "-c", "--client_id", type=str, help="Client ID", required=True
        )

    @transaction.atomic
    def handle(self, *args, **kwargs):
        api_args = {}

        name = kwargs["name"]
        api_args["required_scopes"] = kwargs["scopes"]

        domain, created = ApiDomain.objects.get_or_create(identifier=kwargs["domain"])

        client = Client.objects.filter(client_id=kwargs["client_id"]).first()

        if not client:
            print("Could not find a Client with that ID")
            return False
        kwargs.pop("client_id")
        api_args["oidc_client"] = client

        api, created = Api.objects.get_or_create(
            domain=domain, name=name, defaults=api_args
        )
