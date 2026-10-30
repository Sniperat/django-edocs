from __future__ import annotations

import base64
import hashlib
from datetime import datetime
from typing import Any

from django.utils import timezone

from edocs.models.document import Document
from edocs.models.signer import DocumentSigner


def simulate_mock_signing(
    document: Document,
    signer_obj=None,
    signer_name: str = "",
    cert_info: dict[str, Any] | None = None,
) -> tuple[Document, DocumentSigner]:
    """
    Simulates a 1-click E-IMZO signing operation without requiring a physical USB key.
    Useful for local testing, integration tests, and sandbox / playground environments.
    """
    if document.is_signed:
        raise ValueError("Hujjat allaqachon to'liq imzolangan.")

    pending_signer = document.document_signers.filter(signed=False).order_by("order").first()
    if not pending_signer:
        pending_signer = DocumentSigner.objects.create(
            document=document,
            signer=signer_obj,
            order=0,
            last_one=True,
        )

    now = timezone.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")

    fio = (
        signer_name
        or (pending_signer.signer.get_full_name() if hasattr(pending_signer.signer, "get_full_name") else "")
        or getattr(pending_signer.signer, "username", "")
        or "Administrator"
    )
    pinfl = (
        getattr(pending_signer.signer, "pinfl", "")
        or getattr(pending_signer, "tin", "")
        or "12345678901234"
    )
    tin = getattr(pending_signer, "tin", "") or "301234567"

    if not cert_info:
        cert_info = {
            "CN": fio,
            "name": fio,
            "TIN": tin,
            "PINFL": pinfl,
            "O": "O'zbekiston Respublikasi Qishloq Xo'jaligi Vazirligi",
            "serialNumber": hashlib.sha256(f"{document.guid}:{now_str}".encode()).hexdigest()[:16].upper(),
            "validFrom": now.strftime("%Y-%m-%d"),
            "validTo": "2030-12-31",
        }

    dummy_payload = f"MOCK_PKCS7:{document.guid}:{pinfl}:{now_str}".encode()
    mock_pkcs7 = base64.b64encode(dummy_payload).decode("utf-8")

    verification_result = {
        "status": 1,
        "message": "Imzo muvaffaqiyatli tekshirildi (django-edocs test engine)",
        "verified_at": now_str,
        "document_hash": document.file_hash,
        "subjectCertificateInfo": {
            "serialNumber": cert_info.get("serialNumber", "00000000"),
            "subjectName": {
                "CN": cert_info.get("CN", fio),
                "TIN": cert_info.get("TIN", tin),
                "UID": cert_info.get("PINFL", pinfl),
                "O": cert_info.get("O", "Tashkilot"),
            },
            "validFrom": cert_info.get("validFrom", now.strftime("%Y-%m-%d")),
            "validTo": cert_info.get("validTo", "2030-12-31"),
        },
    }

    actual_signer = signer_obj or pending_signer.signer
    document.mark_signed_step(
        signer_obj=actual_signer,
        pkcs7=mock_pkcs7,
        cert_info=cert_info,
        verification_info=verification_result,
    )

    return document, pending_signer
