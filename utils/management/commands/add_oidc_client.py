from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max
from django.utils.crypto import get_random_string
from oidc_provider.models import Client, ResponseType

from users.models import LoginMethod, OidcClientOptions, OptionsBase, get_provider_ids


class Command(BaseCommand):
    help = "Add OpenID Connect Client"

    def add_arguments(self, parser):
        parser.add_argument(
            "-n", "--name", type=str, help="Name of client", required=True
        )
        parser.add_argument(
            "-t",
            "--response_types",
            nargs="+",
            type=str,
            help="Response type",
            required=True,
        )
        parser.add_argument(
            "-u",
            "--redirect_uris",
            nargs="+",
            type=str,
            help="Redirect URIs",
            required=True,
        )
        parser.add_argument(
            "-i", "--client_id", type=str, help="Client ID", required=True
        )
        parser.add_argument(
            "-s", "--site_type", type=str, help="Site Type", required=True
        )
        parser.add_argument(
            "-o", "--scopes", type=str, help="Scopes", required=False,
        )
        parser.add_argument(
            "-m",
            "--login_methods",
            nargs="+",
            type=str,
            help="Login Methods",
            required=True,
        )
        parser.add_argument(
            "-c", "--confidential", action="store_true", help="Make client public"
        )

    @transaction.atomic
    def handle(self, *args, **kwargs):
        client_args = {
            "client_secret": get_random_string(length=50)
        }
        client_m2m_args = {}
        options_args = {}
        options_m2m_args = {}

        required_params = [
            "name",
            "response_types",
            "redirect_uris",
            "redirect_uris",
            "client_id",
            "login_methods",
        ]
        site_type_choices = [None, ""] + [
            site_type[0] for site_type in OptionsBase.SITE_TYPES
        ]
        valid_login_method_providers = [
            provider_id[0] for provider_id in get_provider_ids()
        ]

        self._check_params(kwargs, required_params)

        client_args["name"] = kwargs["name"]
        client_args["_scope"] = kwargs.get("scopes", "") or ""
        client_args["client_type"] = (
            "confidential" if kwargs.get("confidential", False) else "public"
        )
        client_args["redirect_uris"] = kwargs["redirect_uris"]
        client_args["client_id"] = kwargs["client_id"]

        client_m2m_args["response_types"] = self._check_response_types(
            kwargs["response_types"]
        )

        if kwargs.get("site_type") not in site_type_choices:
            raise CommandError('Type choices must be one of "%s"' % site_type_choices)
        options_args["site_type"] = (
            "development" if not kwargs.get("site_type") else kwargs["site_type"]
        )

        login_method_providers = kwargs.get("login_methods")
        for login_method_provider in login_method_providers:
            if login_method_provider not in valid_login_method_providers:
                raise CommandError(
                    '"login_methods" must be one or more of "%s"'
                    % valid_login_method_providers
                )
        options_m2m_args["login_methods"] = [
            self._create_or_get_login_method(login_method)
            for login_method in kwargs["login_methods"]
        ]

        client, created = Client.objects.get_or_create(
            client_id=kwargs["client_id"], defaults=client_args
        )
        self._set_m2m_entries(client, client_m2m_args)

        options, created = OidcClientOptions.objects.get_or_create(
            oidc_client=client, defaults=options_args
        )
        self._set_m2m_entries(options, options_m2m_args)

    @staticmethod
    def _create_or_get_login_method(login_method_provider):
        login_method = LoginMethod.objects.filter(
            provider_id=login_method_provider
        ).first()
        if not login_method:
            max_order = LoginMethod.objects.aggregate(Max("order"))
            next_order = max_order["order_max"] if max_order.get("order_max") else 1
            login_method = LoginMethod.objects.create(
                provider_id=login_method_provider,
                name=login_method_provider.capitalize(),
                order=next_order,
            )
        return login_method

    @staticmethod
    def _check_params(params, required_params):
        for required_param in required_params:
            missing_args = []
            if required_param not in params.keys():
                missing_args.append(required_param)
            if missing_args:
                raise CommandError(
                    "Missing the following required params: %s", missing_args
                )

    def _check_response_types(self, response_types):
        valid_response_types = ResponseType.objects.all()
        valid_response_type_objects = {
            response_type.value: response_type for response_type in valid_response_types
        }
        response_type_objects = []

        for response_type in response_types:
            response_type_object = valid_response_type_objects.get(response_type)
            if not response_type_object:
                raise CommandError(
                    '"response_types" must be one or more of "%s"'
                    % valid_response_type_objects.keys()
                )
            response_type_objects.append(response_type_object)
        return response_type_objects

    def _set_m2m_entries(self, obj, entries):
        for arg, value in entries.items():
            m2m_entry = getattr(obj, arg)
            m2m_entry.set(value)
