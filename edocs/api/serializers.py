from rest_framework import serializers
from edocs.models.document import Document
from edocs.models.signer import DocumentSigner


class DocumentSignerSerializer(serializers.ModelSerializer):
    signer_name = serializers.SerializerMethodField()

    class Meta:
        model = DocumentSigner
        fields = [
            "id",
            "order",
            "signer_title",
            "signer_name",
            "tin",
            "signed",
            "sign_date",
            "last_one",
            "certificate_info",
        ]

    def get_signer_name(self, obj):
        if not obj.signer:
            return ""
        if hasattr(obj.signer, "get_full_name"):
            return obj.signer.get_full_name()
        return str(obj.signer)


class DocumentDetailSerializer(serializers.ModelSerializer):
    signers = DocumentSignerSerializer(source="document_signers", many=True, read_only=True)
    pdf_url = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "guid",
            "name",
            "document_name",
            "code",
            "file_hash",
            "security_code",
            "is_signed",
            "signers_count",
            "pdf_url",
            "view_url",
            "created_at",
            "signers",
        ]

    def get_pdf_url(self, obj):
        if obj.pdf_file:
            return obj.pdf_file.url
        return ""


class SignRequestSerializer(serializers.Serializer):
    pkcs7 = serializers.CharField(required=True, allow_blank=False, trim_whitespace=True)
    certificate_info = serializers.JSONField(required=False, default=dict)


class ActionNoteSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, default="")
