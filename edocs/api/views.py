import hashlib
import os
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, render
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from edocs.api.serializers import ActionNoteSerializer, DocumentDetailSerializer, SignRequestSerializer
from edocs.models.document import Document
from edocs.services.eimzo import EImzoService
from edocs.services.engine import DocumentEngine


class DocumentChallengeAPIView(APIView):
    """
    Returns document challenge payload, hash, and user permissions for E-IMZO signing.
    URL: /api/edocs/<uuid:guid>/challenge/
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, guid):
        document = get_object_or_404(Document, guid=guid)

        canonical_json, base64_payload = DocumentEngine.build_signing_payload(document)

        if not document.file_hash:
            document.file_hash = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
            document.save(update_fields=["file_hash"])

        current_signer = document.get_current_signer()

        # Check permissions for current user
        can_sign = False
        can_reject = False
        can_cancel = False

        related = document.host_object

        if current_signer and current_signer.signer == request.user:
            can_sign = not document.is_signed

        if related and hasattr(related, "can_reject"):
            can_reject = related.can_reject(request.user)
        elif current_signer and current_signer.signer == request.user:
            can_reject = not document.is_signed

        if related and hasattr(related, "can_cancel"):
            can_cancel = related.can_cancel(request.user)
        else:
            first_signer = document.document_signers.order_by("order").first()
            if first_signer and first_signer.signer == request.user:
                can_cancel = not document.is_signed

        serializer = DocumentDetailSerializer(document)

        return Response({
            "success": True,
            "guid": str(document.guid),
            "challenge": base64_payload,
            "document_hash": document.file_hash,
            "security_code": document.security_code,
            "can_sign": can_sign,
            "can_reject": can_reject,
            "can_cancel": can_cancel,
            "is_rejected": getattr(related, "rejected", False) if related else False,
            "document": serializer.data,
        })


class DocumentSignAPIView(APIView):
    """
    Verifies PKCS#7 signature and attaches it to the current pending signer.
    URL: /api/edocs/<uuid:guid>/sign/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, guid):
        document = get_object_or_404(Document, guid=guid)

        serializer = SignRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        pkcs7 = serializer.validated_data["pkcs7"]
        cert_info = serializer.validated_data.get("certificate_info", {})

        # Verify signature with E-IMZO
        verification = EImzoService.verify_pkcs7(
            pkcs7=pkcs7,
            document_hash=document.file_hash,
            certificate_info=cert_info
        )

        try:
            document.mark_signed_step(
                signer_obj=request.user,
                pkcs7=pkcs7,
                cert_info=cert_info,
                verification_info=verification
            )
        except ValueError as e:
            return Response({"success": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "success": True,
            "message": "Hujjat muvaffaqiyatli imzolandi.",
            "is_signed": document.is_signed,
            "signers_count": document.signers_count,
        })


class DocumentRejectAPIView(APIView):
    """
    Rejects the document.
    URL: /api/edocs/<uuid:guid>/reject/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, guid):
        document = get_object_or_404(Document, guid=guid)
        serializer = ActionNoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        note = serializer.validated_data.get("note", "")
        related = document.host_object

        if related and hasattr(related, "reject_me"):
            try:
                related.reject_me(request.user, note=note)
            except ValueError as e:
                return Response({"success": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"success": False, "message": "Ushbu hujjatni rad etish mumkin emas."}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"success": True, "message": "Hujjat rad etildi."})


class DocumentCancelAPIView(APIView):
    """
    Cancels the document.
    URL: /api/edocs/<uuid:guid>/cancel/
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, guid):
        document = get_object_or_404(Document, guid=guid)
        serializer = ActionNoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        note = serializer.validated_data.get("note", "")
        related = document.host_object

        if related and hasattr(related, "cancel_me"):
            try:
                related.cancel_me(request.user, note=note)
            except ValueError as e:
                return Response({"success": False, "message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"success": False, "message": "Ushbu hujjatni bekor qilish mumkin emas."}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"success": True, "message": "Hujjat bekor qilindi."})


class DocumentPreviewAPIView(APIView):
    """
    Streams PDF binary content for inline browser preview.
    URL: /api/edocs/<uuid:guid>/preview/
    """
    permission_classes = [AllowAny]

    def get(self, request, guid):
        document = get_object_or_404(Document, guid=guid)
        if not document.pdf_file or not os.path.exists(document.pdf_file.path):
            raise Http404("PDF fayl mavjud emas.")

        return FileResponse(
            open(document.pdf_file.path, "rb"),
            content_type="application/pdf",
            filename=f"{document.guid}.pdf"
        )


class DocumentPublicVerifyAPIView(APIView):
    """
    Public verification endpoint (e.g. when scanning QR code).
    URL: /api/edocs/verify/<uuid:guid>/
    """
    permission_classes = [AllowAny]

    def get(self, request, guid):
        document = get_object_or_404(Document, guid=guid)
        serializer = DocumentDetailSerializer(document)

        # If accessed via browser (Accept: text/html), render HTML page
        if "text/html" in request.META.get("HTTP_ACCEPT", ""):
            return render(request, "edocs/verify.html", {"document": document, "signers": document.document_signers.all()})

        return Response({"success": True, "document": serializer.data})
