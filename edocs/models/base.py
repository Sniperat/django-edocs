from django.db import models
from django.utils.translation import gettext_lazy as _
from edocs.conf import edocs_settings
from edocs.signals import document_rejected, document_cancelled


class AbstractDocumentBase(models.Model):
    """
    Abstract model to easily attach an electronic document and signing workflow
    to any business model in the host Django project (e.g., Contract, Act, Invoice).
    """
    STATUS_CHOICES = (
        ("new", _("Yangi")),
        ("pending", _("Imzolanishi kutilmoqda")),
        ("signed", _("Imzolangan")),
        ("rejected", _("Rad etilgan")),
        ("cancelled", _("Bekor qilingan")),
    )

    document = models.OneToOneField(
        "edocs.Document",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_attached",
        verbose_name=_("Elektron hujjat")
    )
    status = models.CharField(
        _("Hujjat holati"),
        max_length=50,
        choices=STATUS_CHOICES,
        default="new",
        db_index=True
    )
    rejected = models.BooleanField(_("Rad etilganmi"), default=False, db_index=True)
    archived = models.BooleanField(_("Arxivlanganmi"), default=False, db_index=True)
    is_changeable = models.BooleanField(_("O'zgartirish mumkinmi"), default=True)

    who_rejected = models.ForeignKey(
        edocs_settings.SIGNER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_rejected",
        verbose_name=_("Rad etgan shaxs")
    )
    note = models.TextField(_("Rad etish / Bekor qilish sababi"), null=True, blank=True)

    class Meta:
        abstract = True

    @property
    def is_signed(self) -> bool:
        return bool(self.document and self.document.is_signed)

    @property
    def signers_count(self) -> int:
        return self.document.signers_count if self.document else 0

    def can_reject(self, signer_obj) -> bool:
        """
        Check if the given signer has permission to reject this document.
        By default, only the pending signer in sequence can reject before signing.
        Can be overridden in subclasses for custom business logic.
        """
        if not self.document or self.document.is_signed or self.rejected or self.archived:
            return False
        current_signer = self.document.get_current_signer()
        if not current_signer or not current_signer.signer:
            return False
        return current_signer.signer == signer_obj

    def can_cancel(self, signer_obj) -> bool:
        """
        Check if the given signer has permission to cancel this document.
        By default, only the creator/first signer can cancel while unsigned.
        Can be overridden in subclasses for custom business logic.
        """
        if not self.document or self.document.is_signed or self.rejected or self.archived:
            return False
        first_signer = self.document.document_signers.order_by("order").first()
        if not first_signer or not first_signer.signer:
            return False
        return first_signer.signer == signer_obj

    def reject_me(self, signer_obj, note: str = ""):
        """Executes document rejection."""
        if not self.can_reject(signer_obj):
            raise ValueError(_("Sizda ushbu hujjatni rad etish huquqi yo'q."))

        self.status = "rejected"
        self.rejected = True
        self.is_changeable = False
        self.who_rejected = signer_obj
        if note:
            self.note = note
        self.save()

        document_rejected.send(
            sender=self.__class__,
            document=self.document,
            signer=signer_obj,
            note=note,
            related_object=self
        )

    def cancel_me(self, signer_obj, note: str = ""):
        """Executes document cancellation."""
        if not self.can_cancel(signer_obj):
            raise ValueError(_("Sizda ushbu hujjatni bekor qilish huquqi yo'q."))

        self.status = "cancelled"
        self.rejected = True
        self.archived = True
        self.is_changeable = False
        self.who_rejected = signer_obj
        if note:
            self.note = note
        self.save()

        document_cancelled.send(
            sender=self.__class__,
            document=self.document,
            signer=signer_obj,
            note=note,
            related_object=self
        )
