from typing import Any, Iterable, Optional, Protocol

from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils.text import slugify


class Lockable(Protocol):
    locked: bool


class SlugMixin(models.Model):
    name = models.CharField(max_length=255, db_collation="case_insensitive")
    slug = models.SlugField(max_length=255)

    class Meta:
        abstract = True

    def __str__(self) -> str:
        return self.name

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self.slug:
            self.slug = slugify(str(self.name))
        super().save(*args, **kwargs)


class ScopedMixin(models.Model):

    organization = models.ForeignKey("Organization", on_delete=models.CASCADE, blank=True)
    project = models.ForeignKey("Project", on_delete=models.CASCADE, blank=True, null=True)
    application = models.ForeignKey("Application", on_delete=models.CASCADE, blank=True, null=True)

    class Meta:
        abstract = True

    def clean(self) -> None:
        try:
            if self.application:
                self.project = self.application.project
        except ObjectDoesNotExist:  # pragma: no cover
            pass
        try:
            if self.project:
                self.organization = self.project.organization
        except ObjectDoesNotExist:  # pragma: no cover
            pass
        super().clean()

    def save(
        self,
        force_insert: bool = False,
        force_update: bool = False,
        using: Optional[str] = None,
        update_fields: Optional[Iterable[str]] = None,
    ) -> None:
        try:
            if self.application:
                self.project = self.application.project
        except ObjectDoesNotExist:  # pragma: no cover
            pass
        try:
            if self.project:
                self.organization = self.project.organization
        except ObjectDoesNotExist:  # pragma: no cover
            pass
        super().save(force_insert, force_update, using, update_fields)
