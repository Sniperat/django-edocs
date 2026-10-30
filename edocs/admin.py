from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from edocs.models.document import Document
from edocs.models.signer import DocumentSigner
from edocs.models.template import DocumentTemplate


class DocumentSignerInline(admin.TabularInline):
    model = DocumentSigner
    extra = 0
    fields = [
        "order",
        "signer",
        "signer_title",
        "tin",
        "signed",
        "sign_date",
        "last_one",
    ]
    readonly_fields = ["signed", "sign_date"]


@admin.register(DocumentTemplate)
class DocumentTemplateAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "file_link", "is_active", "created_at"]
    list_filter = ["is_active", "created_at"]
    search_fields = ["name", "code", "description"]
    readonly_fields = ["created_at", "updated_at"]

    def file_link(self, obj):
        if obj.file:
            return format_html('<a href="{}" target="_blank">DOCX yuklab olish</a>', obj.file.url)
        return "-"
    file_link.short_description = _("Shablon fayli")


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = [
        "guid",
        "name",
        "code",
        "security_code",
        "signed_badge",
        "signers_count",
        "files_link",
        "created_at",
    ]
    list_filter = ["is_signed", "code", "created_at"]
    search_fields = ["guid", "name", "code", "security_code", "file_hash"]
    readonly_fields = [
        "guid",
        "file_hash",
        "security_code",
        "signers_count",
        "is_signed",
        "created_at",
        "updated_at",
    ]
    inlines = [DocumentSignerInline]

    def signed_badge(self, obj):
        if obj.is_signed:
            return mark_safe('<span style="color: green; font-weight: bold;">✔ Imzolangan</span>')
        return mark_safe('<span style="color: orange; font-weight: bold;">⏳ Kutilmoqda</span>')
    signed_badge.short_description = _("Status")

    def files_link(self, obj):
        links = []
        if obj.docx_file:
            links.append(format_html('<a href="{}" target="_blank">DOCX</a>', obj.docx_file.url))
        if obj.pdf_file:
            links.append(format_html('<a href="{}" target="_blank">PDF</a>', obj.pdf_file.url))
        return mark_safe(" | ".join(links)) if links else "-"
    files_link.short_description = _("Fayllar")
