import logging
from typing import Any, Optional

from admin_extra_buttons.decorators import button, view
from adminfilters.autocomplete import LinkedAutoCompleteFilter
from django import forms
from django.conf import settings
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.template import Context, Template
from django.template.response import TemplateResponse
from django_svelte_jsoneditor.widgets import SvelteJSONEditorWidget
from reversion.admin import VersionAdmin
from tinymce.widgets import TinyMCE

from bitcaster.models import Message

from .base import BaseAdmin

logger = logging.getLogger(__name__)


class MessageForm(forms.ModelForm[Message]):
    subject = forms.CharField(required=False)
    content = forms.CharField(widget=forms.Textarea, required=False)
    html_content = forms.CharField(
        required=False,
        widget=TinyMCE(
            attrs={"class": "aaaa"},
            mce_attrs={"setup": "setupTinyMCE", "height": "400px"},
        ),
    )
    context = forms.JSONField(widget=SvelteJSONEditorWidget(), required=False)

    class Meta:
        model = Message
        fields = ("subject", "content", "html_content", "context")

    @property
    def media(self) -> forms.Media:
        orig = super().media
        extra = "" if settings.DEBUG else ".min"
        js = [
            "vendor/jquery/jquery%s.js" % extra,
            "jquery.init.js",
        ]
        return orig + forms.Media(js=["admin/js/%s" % url for url in js])


class MessageChangeForm(forms.ModelForm[Message]):
    class Meta:
        model = Message
        fields = ("name", "channel", "event")


class MessageCreationForm(forms.ModelForm[Message]):

    class Meta:
        model = Message
        fields = ("name", "channel", "event")


class MessageAdmin(BaseAdmin, VersionAdmin[Message]):
    search_fields = ("name",)
    list_display = ("name", "channel", "event")
    list_filter = (
        ("channel__organization", LinkedAutoCompleteFilter.factory(parent=None)),
        ("channel", LinkedAutoCompleteFilter.factory(parent="channel__organization")),
        ("event", LinkedAutoCompleteFilter.factory(parent="channel__organization")),
    )
    autocomplete_fields = ("channel", "event")
    change_form_template = "admin/message/change_form.html"
    form = MessageChangeForm
    add_form = MessageCreationForm

    def get_form(self, request: HttpRequest, obj: Optional["Message"] = None, **kwargs: dict[str, Any]) -> forms.Form:
        defaults: dict[str, Any] = {}
        if obj is None:
            defaults["form"] = self.add_form
        defaults.update(kwargs)
        return super().get_form(request, obj, **defaults)

    def get_queryset(self, request: HttpRequest) -> QuerySet[Message]:
        return super().get_queryset(request).select_related("channel", "event")

    @view()
    def render(self, request: HttpRequest, pk: str) -> "HttpResponse":

        form = MessageForm(request.POST)
        obj = self.get_object(request, pk)
        if form.is_valid():
            tpl = Template(form.cleaned_data["content"])
            try:
                ctx = {**form.cleaned_data["context"], "event": obj.event, "channel": obj.channel, "user": request.user}
                res = tpl.render(Context(ctx))
            except Exception as e:
                res = f"<!DOCTYPE HTML>{str(e)}"  # type: ignore
        else:
            res = f"<!DOCTYPE HTML>{form.errors.as_text()}"  # type: ignore

        return HttpResponse(res)

    @button()
    def edit(self, request: HttpRequest, pk: str) -> "HttpResponse":
        obj = self.get_object(request, pk)
        context = self.get_common_context(request, pk)
        if request.method == "POST":
            form = MessageForm(request.POST, instance=obj)
            if form.is_valid():
                form.save()
                return HttpResponseRedirect("..")
        else:
            form = MessageForm(
                initial={"context": {"event": "<sys>", "channel": "<sys>", "recipient": "<sys>"}}, instance=obj
            )
        context["form"] = form
        return TemplateResponse(request, "admin/message/edit.html", context)
