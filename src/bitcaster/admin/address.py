import logging
from typing import TYPE_CHECKING, Any, Optional, TypeVar

from admin_extra_buttons.mixins import ExtraButtonsMixin
from adminfilters.autocomplete import LinkedAutoCompleteFilter
from adminfilters.mixin import AdminAutoCompleteSearchMixin, AdminFiltersMixin
from django.contrib import admin
from django.contrib.admin.options import InlineModelAdmin
from django.db.models import QuerySet
from django.http import HttpRequest

from bitcaster.models import Address, Validation

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from bitcaster.types.django import AnyModel

    AddressT = TypeVar("AddressT", bound=Address)


class InlineValidation(admin.TabularInline["Validation", "AddressAdmin"]):
    model = Validation
    extra = 0


class AddressAdmin(AdminFiltersMixin, AdminAutoCompleteSearchMixin, ExtraButtonsMixin, admin.ModelAdmin[Address]):
    search_fields = ("name",)
    list_display = ("user", "name", "value", "type")
    list_filter = (
        ("user__roles__organization", LinkedAutoCompleteFilter.factory(parent=None)),
        ("user", LinkedAutoCompleteFilter.factory(parent=None)),
        "type",
    )
    autocomplete_fields = ("user",)

    inlines = [InlineValidation]

    def get_queryset(self, request: HttpRequest) -> QuerySet[Address]:
        return super().get_queryset(request).select_related("user")

    def get_changeform_initial_data(self, request: HttpRequest) -> dict[str, Any]:
        return {
            "user": request.user.id,
            "name": "Address-1",
        }

    def get_inlines(
        self, request: HttpRequest, obj: Optional[Address] = None
    ) -> "list[type[InlineModelAdmin[Address, AnyModel]]]":
        if obj is None:
            return []
        return super().get_inlines(request, obj)
