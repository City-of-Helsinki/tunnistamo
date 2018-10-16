import logging

from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.exceptions import APIException, PermissionDenied
from rest_framework.mixins import CreateModelMixin, DestroyModelMixin, ListModelMixin
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from tunnistamo.api_common import (
    DeviceGeneratedJWTAuthentication, OidcTokenAuthentication, ScopePermission, get_scope_specifiers
)

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
    authentication_classes = (DeviceGeneratedJWTAuthentication, OidcTokenAuthentication)
    permission_classes = (IsAuthenticated, ScopePermission)
    required_scopes = ('identities',)

    def get_queryset(self):
        if not self.request:
            return self.queryset.none()

        qs = self.queryset.filter(user=self.request.user)
        scope_specifiers = self.get_read_scope_specifiers()

        if scope_specifiers is None:
            return qs.none()
        elif scope_specifiers:
            qs = qs.filter(service__in=scope_specifiers)

        return qs

    def list(self, request, *args, **kwargs):
        response = super(UserIdentityViewSet, self).list(request, *args, **kwargs)
        nonce = getattr(request.auth, 'nonce')
        if nonce is not None:
            response['X-Nonce'] = nonce
        return response

    def perform_create(self, serializer):
        data = serializer.validated_data
        secret = data.pop('secret')

        scope_specifiers = self.get_write_scope_specifiers()
        if scope_specifiers and data['service'] not in scope_specifiers:
            raise PermissionDenied()

        validate_credentials_helmet(data['identifier'], secret)

        serializer.save(user=self.request.user)

    def perform_destroy(self, instance):
        if instance.user != self.request.user:
            raise PermissionDenied()

        scope_specifiers = self.get_write_scope_specifiers()
        if scope_specifiers and instance.service not in scope_specifiers:
            raise PermissionDenied()

        instance.delete()

    def get_read_scope_specifiers(self):
        return get_scope_specifiers(self.request, 'identities', 'read')

    def get_write_scope_specifiers(self):
        return get_scope_specifiers(self.request, 'identities', 'write')
