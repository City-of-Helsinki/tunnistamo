from django.conf import settings
from django.utils import translation
from django.utils.translation.trans_real import translation as trans_real_translation
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
        # Return OIDC scopes first and API scopes second, and both of those are also ordered alphabetically by ID.
        # Because why not.
        oidc_scopes = self._create_oidc_scopes_data()
        api_scopes = ApiScopeSerializer(ApiScope.objects.order_by('identifier'), many=True).data
        all_scopes = oidc_scopes + api_scopes

        self.paginator.paginate_queryset(all_scopes, self.request, view=self)
        response = self.paginator.get_paginated_response(all_scopes)

        return response

    @property
    def paginator(self):
        if not hasattr(self, '_paginator'):
            self._paginator = DefaultPagination()
        return self._paginator

    @classmethod
    def _create_oidc_scopes_data(cls):
        if hasattr(cls, '_oidc_scopes_data'):
            return cls._oidc_scopes_data

        ret = []

        for claim_cls in CombinedScopeClaims.combined_scope_claims:
            for name in dir(claim_cls):
                if name.startswith('info_'):
                    scope_identifier = name.split('info_')[1]
                    scope_data = getattr(claim_cls, name)
                    ret.append({
                        'id': scope_identifier,
                        'name': cls._create_translated_field_from_string(scope_data[0]),
                        'description': cls._create_translated_field_from_string(scope_data[1]),
                    })

        ret.sort(key=lambda x: x['id'])
        cls._oidc_scopes_data = ret

        return ret

    @classmethod
    def _create_translated_field_from_string(cls, field):
        with translation.override(ENGLISH_LANGUAGE_CODE):
            value_in_english = str(field)

        ret = {ENGLISH_LANGUAGE_CODE: value_in_english}

        for language in [lc for lc in LANGUAGE_CODES if lc != ENGLISH_LANGUAGE_CODE]:
            translated_value = trans_real_translation(language)._catalog.get(value_in_english)
            if translated_value:
                ret[language] = translated_value

        return ret
