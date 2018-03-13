import logging

from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.exceptions import APIException, PermissionDenied
from rest_framework.mixins import CreateModelMixin, DestroyModelMixin, ListModelMixin
from rest_framework.permissions import IsAuthenticated, BasePermission
from rest_framework.viewsets import GenericViewSet

from tunnistamo.api_common import OidcTokenAuthentication, DeviceGeneratedJWTAuthentication

from .helmet_requests import (
    HelmetConnectionException, HelmetGeneralException, HelmetImproperlyConfiguredException, validate_patron
)
from .models import UserIdentity

logger = logging.getLogger(__name__)

User = get_user_model()


class NotImplementedResponse(APIException):
    status_code = 501
    default_detail = 'Not implemented.'


class ThirdPartyAuthenticationFailed(APIException):
    status_code = 401


def validate_credentials_helmet(identifier, secret):
    try:
        result = validate_patron(identifier, secret)
    except HelmetImproperlyConfiguredException as e:
        logger.error(e)
        raise NotImplementedResponse()
    except HelmetConnectionException as e:
        logger.warning('Cannot validate patron from helmet, got connection exception: {}'.format(e))
        raise ThirdPartyAuthenticationFailed({
            'code': 'authentication_service_unavailable',
            'detail': 'Connection to authentication service timed out',
        })
    except HelmetGeneralException as e:
        logger.warning('Cannot validate patron from helmet, got general exception: {}'.format(e))
        raise ThirdPartyAuthenticationFailed({
            'code': 'unidentified_error',
            'detail': 'Unidentified error',
        })
    if not result:
        raise ThirdPartyAuthenticationFailed({
            'code': 'invalid_credentials',
            'detail': 'Invalid user credentials',
        })


class IdentityScopeAuthentication(OidcTokenAuthentication):
    scopes_needed = ['external_identity']


class UserIdentitySerializer(serializers.ModelSerializer):
    secret = serializers.CharField(write_only=True)

    class Meta:
        model = UserIdentity
        fields = ('id', 'identifier', 'service', 'secret')

    def create(self, validated_data):
        instance, _ = self.Meta.model.objects.update_or_create(
            service=validated_data['service'],
            user=validated_data['user'],
            defaults={'identifier': validated_data['identifier']}
        )
        return instance


class UserIdentityViewSet(ListModelMixin, CreateModelMixin, DestroyModelMixin, GenericViewSet):
    queryset = UserIdentity.objects.all()
    serializer_class = UserIdentitySerializer
    authentication_classes = (OidcTokenAuthentication, DeviceGeneratedJWTAuthentication)
    permission_classes = (IsAuthenticated,)

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        data = serializer.validated_data
        secret = data.pop('secret')

        validate_credentials_helmet(data['identifier'], secret)

        serializer.save(user=self.request.user)

    def perform_destroy(self, instance):
        if instance.user != self.request.user:
            raise PermissionDenied()
        instance.delete()
