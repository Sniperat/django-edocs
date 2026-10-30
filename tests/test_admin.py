import pytest
from django.contrib.admin.sites import AdminSite
from django.core.files.uploadedfile import SimpleUploadedFile
from edocs.admin import DocumentAdmin, DocumentTemplateAdmin
from edocs.models import Document, DocumentTemplate


@pytest.mark.django_db
def test_document_admin_helpers():
    site = AdminSite()
    admin = DocumentAdmin(Document, site)

    doc_pending = Document.objects.create(name="Hujjat 1", is_signed=False)
    badge = admin.signed_badge(doc_pending)
    assert "Kutilmoqda" in badge
    assert admin.files_link(doc_pending) == "-"

    doc_signed = Document.objects.create(name="Hujjat 2", is_signed=True)
    badge_signed = admin.signed_badge(doc_signed)
    assert "Imzolangan" in badge_signed

    doc_with_files = Document.objects.create(
        name="Hujjat 3",
        docx_file=SimpleUploadedFile("doc.docx", b"content"),
        pdf_file=SimpleUploadedFile("doc.pdf", b"content"),
    )
    links = admin.files_link(doc_with_files)
    assert "DOCX" in links
    assert "PDF" in links
    assert "href=" in links


@pytest.mark.django_db
def test_document_template_admin_helpers():
    site = AdminSite()
    admin = DocumentTemplateAdmin(DocumentTemplate, site)

    tpl_empty = DocumentTemplate.objects.create(name="Shablon", code="SHAB_1")
    assert admin.file_link(tpl_empty) == "-"

    tpl_with_file = DocumentTemplate.objects.create(
        name="Shablon 2",
        code="SHAB_2",
        file=SimpleUploadedFile("template.docx", b"content"),
    )
    link = admin.file_link(tpl_with_file)
    assert "DOCX yuklab olish" in link
    assert "href=" in link
