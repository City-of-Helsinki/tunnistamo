from django.db.models import Exists, OuterRef
from django.db.models.functions import Greatest
from django_filters import rest_framework as filters
from django_filters.widgets import BooleanWidget
from oauth2_provider.models import AccessToken
from oidc_provider.models import UserConsent
from rest_framework import serializers, viewsets

from services.models import Service
from tunnistamo.pagination import DefaultPagination
from tunnistamo.utils import TranslatableSerializer


class ServiceSerializer(TranslatableSerializer):
    # these are required because of TranslatableSerializer
    id = serializers.IntegerField(label='ID', read_only=True)
    image = serializers.ImageField(allow_null=True, max_length=100, required=False)

    class Meta:
        model = Service
        fields = ('id', 'name', 'url', 'description', 'image')

    def to_representation(self, instance):
        data = super().to_representation(instance)

        if hasattr(instance, 'consent_given'):
            data['consent_given'] = instance.consent_given

        return data


class ServiceFilter(filters.FilterSet):
    consent_given = filters.Filter(method='filter_consent_given', widget=BooleanWidget())

    class Meta:
        model = Service
        fields = ('consent_given',)

    def filter_consent_given(self, queryset, name, value):
        if 'consent_given' in queryset.query.annotations.keys():
            queryset = queryset.filter(consent_given=value)

        return queryset


class ServiceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ServiceSerializer
    queryset = Service.objects.all()
    pagination_class = DefaultPagination
    filterset_class = ServiceFilter

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user

        if user.is_authenticated:
            user_consents = UserConsent.objects.filter(client__service=OuterRef('pk'), user=user)
            user_access_tokens = AccessToken.objects.filter(application__service=OuterRef('pk'), user=user)
            queryset = queryset.annotate(
                consent_given=Greatest(Exists(user_consents), Exists(user_access_tokens))
            )

        return queryset
