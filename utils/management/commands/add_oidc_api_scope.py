from django.core.management.base import BaseCommand
from django.db import transaction
from oidc_provider.models import Client

from oidc_apis.models import Api, ApiScope


class Command(BaseCommand):
    help = "Add OpenID Connect API Scope"

    def add_arguments(self, parser):
        parser.add_argument(
            "-an", "--api_name", type=str, help="API Domain", required=True
        )
        parser.add_argument(
            "-c", "--client_ids", nargs="+", type=str, help="Client IDs", required=True
        )
        parser.add_argument("-n", "--name", type=str, help="Name", required=True)
        parser.add_argument(
            "-d", "--description", type=str, help="Description", required=True
        )

    @transaction.atomic
    def handle(self, *args, **kwargs):
        api_scope_args = {}
        api_scope_args["name"] = kwargs["name"]
        api_scope_args["description"] = kwargs["description"]
        api = Api.objects.filter(name=kwargs["api_name"])
        if not api:
            print("No API with that domain and name found")
            return False
        if api.count() > 1:
            print("More than one API with that name, can't create scope")
            return False
        api_scope_args["api"] = api.first()

        clients = Client.objects.filter(client_id__in=kwargs["client_ids"])

        if not clients.count() == len(kwargs["client_ids"]):
            print("Could not find all clients with the given client ids")
            return False

        api_scope = ApiScope(**api_scope_args)
        api_scope.clean_fields()
        if not ApiScope.objects.filter(identifier=api_scope.identifier).count():
            api_scope.save()
            api_scope.allowed_apps.set(clients)
