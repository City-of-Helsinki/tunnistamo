import json
import logging

from jwcrypto import jwk
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.mixins import CreateModelMixin, DestroyModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from tunnistamo.api_common import OidcTokenAuthentication, ScopePermission

from .models import UserDevice

logger = logging.getLogger(__name__)


def generate_secret_key():
    key = jwk.JWK()
    # Generate 256-bit AES key for encryption
    key = key.generate(kty='oct', alg='A256KW', use='enc')
    return json.loads(key.export())


class PublicKeySerializer(serializers.Serializer):
    kty = serializers.ChoiceField(['EC'])
    use = serializers.ChoiceField(['sig'])
    crv = serializers.ChoiceField(['P-256'])
    x = serializers.CharField()
    y = serializers.CharField()
    alg = serializers.ChoiceField(['ES256'])

    def to_representation(self, instance):
        return instance


class UserDeviceSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.uuid')
    public_key = PublicKeySerializer()

    class Meta:
        model = UserDevice
        fields = (
            'id', 'user', 'public_key', 'secret_key', 'app_version',
            'os', 'os_version', 'device_model', 'auth_counter'
        )
        read_only_fields = ('user', 'secret_key', 'auth_counter')

    def create(self, validated_data):
        validated_data['secret_key'] = generate_secret_key()
        return UserDevice.objects.create(**validated_data)


class UserDeviceViewSet(CreateModelMixin, DestroyModelMixin, GenericViewSet):
    queryset = UserDevice.objects.all()
    serializer_class = UserDeviceSerializer
    authentication_classes = (OidcTokenAuthentication,)
    permission_classes = (IsAuthenticated, ScopePermission)
    required_scopes = ('devices',)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_destroy(self, instance):
        if instance.user != self.request.user:
            raise PermissionDenied()
        instance.delete()
