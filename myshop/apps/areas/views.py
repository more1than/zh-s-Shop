from .serializers import AreaSerializer, SubsSerializer
from rest_framework_extensions.cache.mixins import CacheResponseMixin

from areas.models import Area
from rest_framework.viewsets import ReadOnlyModelViewSet


class AreaViewSet(CacheResponseMixin, ReadOnlyModelViewSet):
    pagination_class = None  # 禁用分页

    def get_queryset(self):
        if self.action == "list":
            return Area.objects.filter(parent=None)
        else:
            return Area.objects.all()

    def get_serializer_class(self):
        if self.action == "list":
            return AreaSerializer
        else:
            return SubsSerializer
