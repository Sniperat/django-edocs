from django.db import models
from django.utils.translation import gettext_lazy as _
from edocs.conf import edocs_settings


class DocumentTemplate(models.Model):
    """
    Stores Word (.docx) templates with Jinja2 / dollar-brace tags.
    Templates can be uploaded via Django Admin or generated dynamically.
    """
    name = models.CharField(_("Shablon nomi"), max_length=255)
    code = models.CharField(_("Shablon kodi"), max_length=100, unique=True, db_index=True)
    file = models.FileField(
        _("Word shablon (.docx)"),
        upload_to=edocs_settings.TEMPLATES_UPLOAD_TO,
        null=True,
        blank=True
    )
    description = models.TextField(_("Tavsifi / O'zgaruvchilar"), null=True, blank=True)
    is_active = models.BooleanField(_("Faolmi"), default=True)
    created_at = models.DateTimeField(_("Yaratilgan sana"), auto_now_add=True)
    updated_at = models.DateTimeField(_("O'zgartirilgan sana"), auto_now=True)

    class Meta:
        verbose_name = _("Hujjat shabloni")
        verbose_name_plural = _("Hujjat shablonlari")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.code})"
