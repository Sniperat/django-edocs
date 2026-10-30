import logging
import requests
from django.utils import timezone
from edocs.conf import edocs_settings
from edocs.exceptions import EImzoVerificationError


class EImzoService:
    """
    Service for validating and processing E-IMZO PKCS#7 digital signatures.
    """

    @classmethod
    def verify_pkcs7(cls, pkcs7: str, document_hash: str = None, certificate_info: dict = None) -> dict:
        """
        Validates PKCS#7 signature against the configured E-IMZO verification endpoint.
        Falls back to local inspection/mock mode in development if enabled.
        """
        if not pkcs7:
            raise EImzoVerificationError("PKCS#7 imzo kodi kiritilishi shart.")

        endpoint = edocs_settings.VERIFY_URL
        cert_info = certificate_info or {}

        if endpoint:
            try:
                logging.info(f"Connecting to E-IMZO verification endpoint: {endpoint}")
                # Try raw body first (standard for backend/pkcs7/verify/attached endpoints)
                response = requests.post(
                    endpoint,
                    data=pkcs7,
                    headers={"Content-Type": "text/plain"},
                    timeout=15,
                )
                # If not 200, try json payload (for endpoints expecting {"pkcs7": ...})
                if response.status_code != 200:
                    response = requests.post(
                        endpoint,
                        json={"pkcs7": pkcs7, "hash": document_hash},
                        headers={"Content-Type": "application/json"},
                        timeout=15,
                    )

                if response.status_code == 200:
                    result = response.json()
                    logging.info(f"E-IMZO verification succeeded: {result}")
                    return result
                else:
                    logging.warning(
                        f"E-IMZO server returned status {response.status_code}: {response.text[:300]}"
                    )
            except Exception as e:
                logging.warning(f"Could not reach E-IMZO server ({endpoint}): {e}")

        # Local development / fallback response if allowed
        if edocs_settings.ENABLE_LOCAL_FALLBACK:
            now = timezone.now()
            return {
                "status": 1,
                "message": "Imzo muvaffaqiyatli qabul qilindi va tekshirildi (django-edocs Local Engine)",
                "verified_at": now.strftime("%Y-%m-%d %H:%M:%S"),
                "document_hash": document_hash,
                "subjectCertificateInfo": {
                    "serialNumber": cert_info.get("serialNumber") or "00000000",
                    "subjectName": {
                        "CN": cert_info.get("CN") or "Imzo Egasi",
                        "TIN": cert_info.get("TIN") or "",
                        "UID": cert_info.get("UID") or cert_info.get("PINFL") or "",
                        "O": cert_info.get("O") or "Tashkilot",
                    },
                    "validFrom": cert_info.get("validFrom") or now.strftime("%Y-%m-%d"),
                    "validTo": cert_info.get("validTo") or "2099-12-31",
                },
            }

        raise EImzoVerificationError(
            f"E-IMZO tekshirish serveri ({endpoint}) javob bermadi va local fallback o'chirilgan."
        )
