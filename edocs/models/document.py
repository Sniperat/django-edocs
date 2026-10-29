import random
import uuid
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from edocs.conf import edocs_settings
from edocs.signals import document_fully_signed


class Document(models.Model):
    """
    Central electronic document model.
    Maintains docx/pdf files, cryptographic hash, 4-digit security code,
    multi-signer state, and optional generic relation to host models.
    """
    guid = models.UUIDField(
        _("Takrorlanmas ID (GUID)"),
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True
    )
    name = models.CharField(_("Nomi"), max_length=255, blank=True)
    document_name = models.CharField(_("Hujjat nomi"), max_length=350, blank=True)
    code = models.CharField(_("Shablon kodi"), max_length=100, blank=True, db_index=True)

    template = models.ForeignKey(
        "edocs.DocumentTemplate",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_documents",
        verbose_name=_("Hujjat shabloni")
    )

    docx_file = models.FileField(
        upload_to=edocs_settings.DOCX_UPLOAD_TO,
        null=True,
        blank=True,
        verbose_name=_("Word fayl (.docx)")
    )
    pdf_file = models.FileField(
        upload_to=edocs_settings.PDF_UPLOAD_TO,
        null=True,
        blank=True,
        verbose_name=_("PDF fayl (.pdf)")
    )

    file_hash = models.CharField(
        _("PDF fayl heshi (SHA-256)"),
        max_length=64,
        blank=True,
        db_index=True
    )
    security_code = models.CharField(
        _("Xavfsizlik kodi"),
        max_length=4,
        blank=True,
        db_index=True
    )

    is_signed = models.BooleanField(_("To'liq imzolanganmi"), default=False, db_index=True)
    signers_count = models.PositiveIntegerField(_("Imzolaganlar soni"), default=0)

    download_url = models.CharField(_("Yuklab olish havolasi"), max_length=500, blank=True)
    view_url = models.CharField(_("Ko'rish havolasi"), max_length=500, blank=True)

    extra_data = models.JSONField(_("Qo'shimcha ma'lumotlar"), default=dict, blank=True)

    # Generic relation to any host model (Contract, Act, Invoice, etc.)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="edocs_documents"
    )
    object_id = models.CharField(max_length=255, null=True, blank=True)
    related_object = GenericForeignKey("content_type", "object_id")

    created_at = models.DateTimeField(_("Yaratilgan sana"), auto_now_add=True)
    updated_at = models.DateTimeField(_("O'zgartirilgan sana"), auto_now=True)

    class Meta:
        verbose_name = _("Elektron hujjat")
        verbose_name_plural = _("Elektron hujjatlar")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name or self.code} ({self.guid})"

    def save(self, *args, **kwargs):
        if not self.security_code:
            self.security_code = str(random.randint(1000, 9999))
        super().save(*args, **kwargs)

    def get_current_signer(self):
        """Returns the DocumentSigner instance whose turn it is to sign."""
        return self.document_signers.filter(signed=False).order_by("order").first()

    def is_current_signer(self, signer_obj) -> bool:
        """Checks whether the given signer/user is the next in line to sign."""
        current = self.get_current_signer()
        if not current:
            return False
        return current.signer == signer_obj

    def mark_signed_step(self, signer_obj, pkcs7: str, cert_info: dict, verification_info: dict = None):
        """
        Advances the signing sequence for the current pending signer.
        Updates document counts, marks completion if last one, and emits signals.
        """
        pending = self.document_signers.filter(signed=False).order_by("order").first()
        if not pending:
            raise ValueError("Barcha imzolovchilar allaqachon imzolab bo'lgan.")

        if signer_obj and pending.signer and pending.signer != signer_obj:
            raise ValueError("Hozirda imzolash navbati boshqa imzolovchida.")

        now = timezone.now()
        pending.signed = True
        pending.sign_date = now
        pending.pkcs7 = pkcs7
        pending.certificate_info = cert_info or {}
        pending.verification_info = verification_info or {}
        pending.save()

        # Update document aggregates
        signed_count = self.document_signers.filter(signed=True).count()
        total_count = self.document_signers.count()

        self.signers_count = signed_count
        if signed_count >= total_count or pending.last_one:
            self.is_signed = True
            self.save(update_fields=["signers_count", "is_signed", "updated_at"])
            document_fully_signed.send(sender=self.__class__, document=self, related_object=self.related_object)
        else:
            self.save(update_fields=["signers_count", "updated_at"])

        return pending
