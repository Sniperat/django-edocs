import base64
import hashlib
import json
import logging
import os
import re
import subprocess
import uuid
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from docx.shared import Inches, Pt, RGBColor
from docxtpl import DocxTemplate, InlineImage, RichText

from edocs.conf import edocs_settings
from edocs.exceptions import DocumentGenerationError
from edocs.models.document import Document
from edocs.models.signer import DocumentSigner
from edocs.models.template import DocumentTemplate
from edocs.services.qr import QRCodeService
from edocs.signals import document_created


class DecimalAndDateEncoder(json.JSONEncoder):
    """Encodes Decimal, datetime, and date objects into JSON serializable format."""
    def default(self, o):
        if isinstance(o, Decimal):
            return float(o)
        if hasattr(o, "isoformat"):
            return o.isoformat()
        return super().default(o)


class CustomDocxTemplate(DocxTemplate):
    """
    Enhanced DocxTemplate supporting both Jinja2 ({{ var }}) and dollar-brace (${var}) syntax.
    Handles MS Word XML run splits, automatic dynamic table loops, and converts None/null to "".
    """

    def __getattr__(self, name):
        if name == "docx" or name.startswith("_"):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
        docx = self.__dict__.get("docx")
        if docx is None:
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
        return getattr(docx, name)

    @staticmethod
    def _finalize_val(x):
        if x is None:
            return ""
        if isinstance(x, str) and x.strip().lower() in ("none", "null"):
            return ""
        return x

    def render(self, context, jinja_env=None, autoescape=False):
        self.current_context = context or {}
        import jinja2
        if not jinja_env:
            jinja_env = jinja2.Environment(autoescape=autoescape, finalize=self._finalize_val)
        else:
            if not getattr(jinja_env, "finalize", None):
                jinja_env.finalize = self._finalize_val
        return super().render(context, jinja_env=jinja_env, autoescape=autoescape)

    def patch_xml(self, src_xml):
        # 1. Clean XML tags between '$' and '{'
        src_xml = re.sub(r"(?<=\$)(<[^>]*>)+(?=\{)", "", src_xml, flags=re.DOTALL)

        # 1b. Strip split XML tags inside ${ ... }
        def strip_dollar_tags(m):
            return re.sub(r"</w:t>.*?(<w:t>|<w:t [^>]*>)", "", m.group(0), flags=re.DOTALL)

        src_xml = re.sub(
            r"\$(?:<[^>]*>)*\{((?:(?!\}|<w:p[ >]|</w:p>).)*?)\}",
            strip_dollar_tags,
            src_xml,
            flags=re.DOTALL,
        )

        # 2. Strip leading whitespace before ${signers} or ${imzolar}
        src_xml = re.sub(r"[\s\xa0]+(?=\$\{(?:signers|imzolar))", "", src_xml)

        # 3. Convert ${...} to {{...}} or {%...%}
        def replacer(match):
            content = match.group(1)
            stripped = content.strip()
            statement_prefixes = (
                "for ", "tr for ", "tc for ", "endfor", "tr endfor", "tc endfor", "if ", "endif", "else", "elif "
            )
            if any(stripped.startswith(kw) or stripped == kw.strip() for kw in statement_prefixes):
                return "{%" + stripped + " %}"
            if stripped in ("signers", "imzolar") or stripped.startswith("signers") or stripped.startswith("imzolar") or stripped.startswith("r "):
                tag_name = stripped[2:].strip() if stripped.startswith("r ") else stripped
                return "{{r " + tag_name + "}}"
            return "{{" + content + "}}"

        pattern = r"\$\{((?:(?![\${}]|<w:p[ >]|</w:p>).)*?)\}(?!\})"
        src_xml = re.sub(pattern, replacer, src_xml, flags=re.DOTALL)

        # 4. Convert standard {{ signers }} to {{r signers}}
        src_xml = re.sub(r"\{\{\s*(signers[a-zA-Z0-9_]*|imzolar[a-zA-Z0-9_]*)\s*\}\}", r"{{r \1}}", src_xml)

        # 5. Fix signer paragraph alignment to left
        def fix_signer_paragraph(m):
            p_xml = m.group(0)
            if any(tag in p_xml for tag in ("{{r signers", "{{r imzolar")):
                if "<w:jc " in p_xml:
                    p_xml = re.sub(r'<w:jc\s+w:val="[^"]*"\s*/>', '<w:jc w:val="left"/>', p_xml)
                elif "<w:pPr>" in p_xml or "<w:pPr " in p_xml:
                    p_xml = re.sub(r"(<w:pPr[^>]*>)", r'\1<w:jc w:val="left"/>', p_xml)
                else:
                    p_xml = re.sub(r"(<w:p[^>]*>)", r'\1<w:pPr><w:jc w:val="left"/></w:pPr>', p_xml)

                if "<w:ind " in p_xml:
                    p_xml = re.sub(r'<w:ind\s+[^>]*/>', '<w:ind w:left="0" w:right="0" w:firstLine="0"/>', p_xml)
            return p_xml

        src_xml = re.sub(r"<w:p\b[^>]*>.*?</w:p>", fix_signer_paragraph, src_xml, flags=re.DOTALL)

        # 6. Apply base patch_xml
        src_xml = super().patch_xml(src_xml)

        # 7. Automatically wrap table rows containing list properties in {% for ... %} loop
        src_xml = self.patch_table_row_loops(src_xml)
        return src_xml

    def patch_table_row_loops(self, xml: str) -> str:
        """
        Scans XML for <w:tr> blocks containing list property access (e.g. {{ items.name }})
        and wraps them in a Jinja2 row replication loop {% for _row in (items or []) %}.
        Skips scalar attributes and rows already inside loops.
        """
        current_ctx = self.__dict__.get("current_context", {}) or {}

        def _patch_tr(m):
            tr_xml = m.group(0)
            if any(k in tr_xml for k in ("{% for ", "{%tr for ", "{% for", "{%tr for", "endfor")):
                return tr_xml

            matches = re.findall(r"\{\{\s*([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)\s*\}\}", tr_xml)
            if not matches:
                return tr_xml

            list_candidates = {}
            for list_name, prop_name in matches:
                # If current_ctx has this name, ensure it is actually a list or tuple
                if current_ctx:
                    val = current_ctx.get(list_name)
                    if not isinstance(val, (list, tuple)):
                        continue
                list_candidates[list_name] = list_candidates.get(list_name, 0) + 1

            if not list_candidates:
                return tr_xml

            best_list_name = max(list_candidates.items(), key=lambda x: x[1])[0]

            def replace_item_refs(match_item):
                l_name, p_name = match_item.group(1), match_item.group(2)
                if l_name == best_list_name:
                    return f"{{{{ _row.{p_name} }}}}"
                return match_item.group(0)

            updated_tr = re.sub(r"\{\{\s*([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)\s*\}\}", replace_item_refs, tr_xml)
            wrapped_tr = f"{{% for _row in ({best_list_name} or []) %}}{updated_tr}{{% endfor %}}"
            return wrapped_tr

        return re.sub(r"<w:tr\b[^>]*>.*?</w:tr>", _patch_tr, xml, flags=re.DOTALL)


class DocumentEngine:
    """
    Main orchestrator for generating, rendering, hashing, and converting electronic documents.
    """

    @classmethod
    def generate_document(
        cls,
        template_code: str,
        context_data: dict,
        related_object=None,
        signers: list = None,
        document_name: str = "",
    ) -> Document:
        """
        Creates and saves a new Document instance populated from a template.
        Wrapped in transaction.atomic to prevent orphan rows on render failures.
        """
        template = DocumentTemplate.objects.filter(code=template_code, is_active=True).first()
        if not template or not template.file:
            raise DocumentGenerationError(f"Faol shablon topilmadi: {template_code}")

        with transaction.atomic():
            doc_instance = Document.objects.create(
                name=document_name or template.name,
                document_name=document_name or template.name,
                code=template_code,
                template=template,
                extra_data=context_data,
                related_object=related_object,
            )

            # Generate QR code
            verify_base_url = edocs_settings.VERIFY_FRONTEND_URL.rstrip("/")
            if verify_base_url:
                view_url = f"{verify_base_url}/{doc_instance.guid}"
            else:
                view_url = f"/api/edocs/verify/{doc_instance.guid}/"

            doc_instance.view_url = view_url
            qr_file_path = QRCodeService.generate_document_qr(
                str(doc_instance.guid),
                view_url=view_url,
                security_code=doc_instance.security_code
            )

            # Prepare Word document
            tpl = CustomDocxTemplate(template.file.path)
            render_context = dict(context_data)
            render_context["qrcode"] = InlineImage(tpl, qr_file_path, width=Inches(1.2))
            render_context["guid"] = str(doc_instance.guid)
            render_context["security_code"] = doc_instance.security_code

            # Add signer place-markers
            render_context["signers"] = RichText("Imzo qo'yilishi kutilmoqda")

            media_root = Path(getattr(settings, "MEDIA_ROOT", "/tmp"))
            docx_dir = media_root / "edocs" / "docx"
            docx_dir.mkdir(parents=True, exist_ok=True)
            docx_path = docx_dir / f"{doc_instance.guid}.docx"

            try:
                tpl.render(render_context)
                tpl.save(str(docx_path))
                doc_instance.docx_file.name = f"edocs/docx/{doc_instance.guid}.docx"
            except Exception as e:
                raise DocumentGenerationError(f"Word shablonni to'ldirishda xatolik: {e}")

            # Convert to PDF
            pdf_path = cls.convert_to_pdf(docx_path)
            if pdf_path and os.path.exists(pdf_path):
                doc_instance.pdf_file.name = f"edocs/pdf/{doc_instance.guid}.pdf"
                with open(pdf_path, "rb") as f:
                    doc_instance.file_hash = hashlib.sha256(f.read()).hexdigest()

            doc_instance.save()

            # Update related_object status and document reference if applicable
            if related_object:
                updated_fields = []
                if hasattr(related_object, "status") and getattr(related_object, "status", None) == "new":
                    related_object.status = "pending"
                    updated_fields.append("status")
                if hasattr(related_object, "document"):
                    related_object.document = doc_instance
                    updated_fields.append("document")
                if updated_fields:
                    related_object.save(update_fields=updated_fields)

            # Create signers queue if provided
            if signers:
                total = len(signers)
                for idx, signer_info in enumerate(signers):
                    signer_obj = signer_info.get("signer") if isinstance(signer_info, dict) else signer_info
                    title = signer_info.get("title", "") if isinstance(signer_info, dict) else ""
                    tin = signer_info.get("tin", "") if isinstance(signer_info, dict) else ""

                    DocumentSigner.objects.create(
                        document=doc_instance,
                        signer=signer_obj,
                        signer_title=title,
                        tin=tin,
                        order=idx,
                        last_one=(idx == total - 1)
                    )

            document_created.send(sender=Document, document=doc_instance, related_object=related_object)
            return doc_instance

    @classmethod
    def convert_to_pdf(cls, docx_path: Path) -> Path:
        """
        Converts a .docx file to .pdf using headless LibreOffice.
        """
        output_dir = docx_path.parent.parent / "pdf"
        output_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            edocs_settings.LIBREOFFICE_PATH,
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(output_dir),
            str(docx_path)
        ]

        try:
            logging.info(f"Converting DOCX to PDF: {' '.join(cmd)}")
            subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
            pdf_path = output_dir / f"{docx_path.stem}.pdf"
            return pdf_path
        except Exception as e:
            logging.error(f"LibreOffice conversion failed: {e}")
            return None

    @classmethod
    def build_signing_payload(cls, document: Document) -> tuple[str, str]:
        """
        Produces canonical JSON string and Base64 string for E-IMZO signing.
        """
        payload = {
            "guid": str(document.guid),
            "code": document.code,
            "security_code": document.security_code,
            "file_hash": document.file_hash or "",
            "created_at": document.created_at.strftime("%Y-%m-%d %H:%M:%S") if document.created_at else "",
            "data": document.extra_data or {},
        }
        canonical_json = json.dumps(payload, sort_keys=True, cls=DecimalAndDateEncoder, ensure_ascii=False)
        base64_payload = base64.b64encode(canonical_json.encode("utf-8")).decode("utf-8")
        return canonical_json, base64_payload
