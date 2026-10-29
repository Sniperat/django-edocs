from django.db import models
from django.utils.translation import gettext_lazy as _
from edocs.conf import edocs_settings


class DocumentSigner(models.Model):
    """
    Represents an individual signer in the multi-party signing sequence.
    Stores PKCS#7 signature, verified certificate info, and status.
    """
    document = models.ForeignKey(
        "edocs.Document",
        on_delete=models.CASCADE,
        related_name="document_signers",
        verbose_name=_("Hujjat")
    )
    signer = models.ForeignKey(
        edocs_settings.SIGNER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="edocs_to_sign",
        verbose_name=_("Imzolovchi")
    )
    signer_title = models.CharField(_("Lavozimi / Roli"), max_length=255, blank=True)
    tin = models.CharField(_("STIR / JSHSHIR"), max_length=20, blank=True)
    order = models.PositiveIntegerField(_("Imzolash navbati"), default=0, db_index=True)
    signed = models.BooleanField(_("Imzolanganmi"), default=False, db_index=True)
    sign_date = models.DateTimeField(_("Imzo qo'yilgan sana"), null=True, blank=True)
    last_one = models.BooleanField(_("Oxirgi imzolovchimi"), default=False)

    # Cryptographic / E-IMZO data
    pkcs7 = models.TextField(_("PKCS#7 imzo kodi"), blank=True, null=True)
    signed_hash = models.CharField(_("Imzolangan hesh"), max_length=64, blank=True)
    certificate_info = models.JSONField(_("Sertifikat ma'lumotlari"), default=dict, blank=True)
    verification_info = models.JSONField(_("E-IMZO tekshiruv natijasi"), default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Hujjat imzolovchisi")
        verbose_name_plural = _("Hujjat imzolovchilari")
        ordering = ["order", "id"]

    def __str__(self):
        status_text = "Imzolangan" if self.signed else "Kutilmoqda"
        return f"{self.document.name or self.document.guid} - #{self.order} ({status_text})"

    def save(self, *args, **kwargs):
        self.signed = self.sign_date is not None
        super().save(*args, **kwargs)
