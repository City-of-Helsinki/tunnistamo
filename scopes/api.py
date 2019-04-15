from django.conf import settings
from django.utils import translation
from django.utils.functional import cached_property
from rest_framework import serializers
from rest_framework.schemas import AutoSchema
from rest_framework.views import APIView

from oidc_apis.models import ApiScope
from oidc_apis.scopes import CombinedScopeClaims
from tunnistamo.pagination import DefaultPagination
from tunnistamo.utils import TranslatableSerializer

ENGLISH_LANGUAGE_CODE = 'en'
LANGUAGE_CODES = [l[0] for l in settings.LANGUAGES]
assert ENGLISH_LANGUAGE_CODE in LANGUAGE_CODES


class ApiScopeSerializer(TranslatableSerializer):
    id = serializers.CharField(source='identifier')

    class Meta:
        model = ApiScope
        fields = ('id', 'name', 'description')


class AutoSchemaWithPaginationParams(AutoSchema):
    def get_pagination_fields(self, path, method):
        return DefaultPagination().get_schema_fields(method)


class ScopeListView(APIView):
    """
    List scopes related to OIDC authentication.
    """
    schema = AutoSchemaWithPaginationParams()

    def get(self, request, format=None):
        scopes = ScopeDataBuilder().get_scopes_data()
        self.paginator.paginate_queryset(scopes, self.request, view=self)
        response = self.paginator.get_paginated_response(scopes)

        return response

    @property
    def paginator(self):
        if not hasattr(self, '_paginator'):
            self._paginator = DefaultPagination()
        return self._paginator


class ScopeDataBuilder:
    """
    A builder for scope data to be used in the API.

    Implemented as a class to provide better control of caching. A ScopeDataBuilder instance caches
    ApiScopes (which are in the db), so in practice there should be an own instance per request
    to cope with possible modifications.
    """
    def get_scopes_data(self, only=None):
        """
        Get full data of OIDC and API scopes

        Returns OIDC scopes first and API scopes second, and both of those are also ordered alphabetically by ID.
        Because why not.

        :param only: If given, include only these scopes (ids).
        :type only: List[str]
        """
        if only:
            return [s for s in self.scopes_data if s['id'] in only]
        else:
            return self.scopes_data

    @cached_property
    def scopes_data(self):
        return self._get_oidc_scopes_data() + self._get_api_scopes_data()

    @classmethod
    def _get_oidc_scopes_data(cls):
        ret = []

        for claim_cls in CombinedScopeClaims.combined_scope_claims:
            for name in dir(claim_cls):
                if name.startswith('info_'):
                    scope_identifier = name.split('info_')[1]
                    result = {
                        'id': scope_identifier,
                        'name': {},
                        'description': {},
                    }
                    # The following loop produces scope name and description strings for every language
                    # listed in LANGUAGE_CODES regardless whether the string is translated or not. If
                    # translation is not found the string fallbacks to default language.
                    initial_language = translation.get_language()
                    for language in LANGUAGE_CODES:
                        translation.activate(language)
                        scope_data = getattr(claim_cls, name)
                        result['name'][language] = str(scope_data[0])
                        result['description'][language] = str(scope_data[1])
                    translation.activate(initial_language)
                    ret.append(result)
            ret.sort(key=lambda x: x['id'])
        return ret

    @classmethod
    def _get_api_scopes_data(cls):
        return ApiScopeSerializer(ApiScope.objects.order_by('identifier'), many=True).data
