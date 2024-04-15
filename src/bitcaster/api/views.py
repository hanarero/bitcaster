from typing import Any

from django.http import HttpRequest
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_extensions.mixins import NestedViewSetMixin

from ..models import Application, Channel, Event, Organization, Project, User
from .serializers import (
    ApplicationSerializer,
    ChannelSerializer,
    EventSerializer,
    OrganizationSerializer,
    ProjectSerializer,
    UserSerializer,
)


class SelectedOrganizationViewSet(viewsets.ReadOnlyModelViewSet):
    def selected_organization(self) -> Organization:
        return Organization.objects.get(id=self.kwargs["slug"])


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.DjangoObjectPermissions]
    lookup_field = "slug"


class OrganizationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    permission_classes = [permissions.DjangoObjectPermissions]
    lookup_field = "slug"

    def get_view_name(self) -> str:
        from rest_framework.views import get_view_name

        return get_view_name(self)


class ProjectViewSet(NestedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Project.objects.all().order_by("-pk")
    serializer_class = ProjectSerializer
    permission_classes = [permissions.DjangoObjectPermissions]
    lookup_field = "slug"
    # lookup_url_kwarg = "slug"


class ApplicationViewSet(NestedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Application.objects.all().order_by("-pk")
    serializer_class = ApplicationSerializer
    permission_classes = [permissions.DjangoObjectPermissions]
    lookup_field = "slug"


class ChannelViewSet(NestedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Channel.objects.all().order_by("-pk")
    serializer_class = ChannelSerializer
    permission_classes = [permissions.DjangoObjectPermissions]


class EventViewSet(NestedViewSetMixin, viewsets.ReadOnlyModelViewSet):
    queryset = Event.objects.all().order_by("-pk")
    serializer_class = EventSerializer
    permission_classes = [permissions.DjangoObjectPermissions]

    @action(detail=True)
    def channels(self, request: HttpRequest, **kwargs: Any) -> Response:
        obj = self.get_object()
        qs = obj.channels.all()
        serializer = ChannelSerializer(qs, many=True)
        return Response(serializer.data)
