import json
import os
import pytest
from edocs.models import Document
from edocs.services.eimzo import EImzoService
from edocs.services.engine import CustomDocxTemplate, DocumentEngine
from edocs.services.qr import QRCodeService


def test_custom_docx_template_xml_patching():
    tpl = CustomDocxTemplate.__new__(CustomDocxTemplate)

    # 1. Test dollar-brace conversion to jinja2
    sample_xml = "<w:p><w:t>Shartnoma raqami: ${doc_number}</w:t></w:p>"
    patched = tpl.patch_xml(sample_xml)
    assert "{{doc_number}}" in patched
    assert "${doc_number}" not in patched

    # 2. Test dynamic loops conversion
    loop_xml = "<w:p><w:t>${for item in items}</w:t></w:p>"
    patched_loop = tpl.patch_xml(loop_xml)
    assert "{%for item in items" in patched_loop

    # 3. Test signers placeholder left alignment and RichText conversion
    signers_xml = '<w:p><w:jc w:val="right"/><w:t>${signers}</w:t></w:p>'
    patched_signers = tpl.patch_xml(signers_xml)
    assert "signers" in patched_signers
    assert '<w:jc w:val="left"/>' in patched_signers


def test_qr_code_generation():
    qr_path = QRCodeService.generate_document_qr(
        guid="test-guid-1234",
        view_url="https://test.uz/verify/test-guid-1234",
        security_code="9876",
    )
    assert os.path.exists(qr_path)
    assert qr_path.endswith(".png")
    assert os.path.getsize(qr_path) > 500  # Valid PNG image


@pytest.mark.django_db
def test_build_signing_payload():
    doc = Document.objects.create(
        name="Test Payload Doc",
        code="contract_grain",
        security_code="5566",
        extra_data={"contract_sum": "50000000"},
    )
    canonical_json, base64_payload = DocumentEngine.build_signing_payload(doc)

    assert canonical_json is not None
    assert base64_payload is not None

    parsed = json.loads(canonical_json)
    assert parsed["guid"] == str(doc.guid)
    assert parsed["security_code"] == "5566"
    assert parsed["data"]["contract_sum"] == "50000000"


def test_eimzo_service_fallback_verification():
    res = EImzoService.verify_pkcs7(
        pkcs7="DUMMY_BASE64_PKCS7_SIGNATURE",
        document_hash="test_sha256_hash",
        certificate_info={"CN": "Test Foydalanuvchi", "TIN": "301234567"},
    )
    assert res["status"] == 1
    assert "subjectCertificateInfo" in res
    assert res["subjectCertificateInfo"]["subjectName"]["CN"] == "Test Foydalanuvchi"
