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


class ServiceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ServiceSerializer
    queryset = Service.objects.all()
    pagination_class = DefaultPagination
