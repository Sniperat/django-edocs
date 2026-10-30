from __future__ import annotations

import logging
import os
import re
from datetime import datetime
from typing import Any

from docx import Document as PythonDocx
from docxtpl import DocxTemplate

logger = logging.getLogger(__name__)

RESERVED_VARIABLES = {
    "qrcode",
    "guid",
    "security_code",
    "signers",
    "imzolar",
    "request",
    "user",
}


def generate_mock_value_for_key(key: str) -> Any:
    """
    Generates meaningful, realistic test values based on variable name heuristics.
    Supports Uzbek, Russian, and English naming conventions.
    """
    lowered = key.lower()
    today = datetime.now()

    if any(k in lowered for k in ("date", "sana", "kun", "day")):
        return today.strftime("%d.%m.%Y")
    if any(k in lowered for k in ("time", "vaqt", "soat")):
        return today.strftime("%H:%M")
    if any(k in lowered for k in ("year", "yil", "god")):
        return str(today.year)
    if any(k in lowered for k in ("tin", "stir", "inn")):
        return "301234567"
    if any(k in lowered for k in ("pinfl", "jshshir", "pnfl")):
        return "12345678901234"
    if any(k in lowered for k in ("phone", "tel", "telefon", "mobile")):
        return "+998 90 123 45 67"
    if any(k in lowered for k in ("sum", "price", "amount", "narx", "qiymat", "jami", "total")):
        return "150 000 000"
    if any(k in lowered for k in ("area", "maydon", "gektar", "ha", "ploshad")):
        return "25.5"
    if any(k in lowered for k in ("company", "korxona", "tashkilot", "firm", "org")):
        return '"AGRO BARAKA KLASTER" MCHJ'
    if any(k in lowered for k in ("farmer", "fermer")):
        return '"OLTIN VODI ZAMIN" Fermer Xo\'jaligi'
    if any(k in lowered for k in ("director", "rahbar", "fio", "boshliq", "signer", "rukovoditel")):
        return "Karimov Alisher Bahromovich"
    if any(k in lowered for k in ("region", "viloyat", "oblast")):
        return "Toshkent viloyati"
    if any(k in lowered for k in ("district", "tuman", "rayon")):
        return "Qibray tumani"
    if any(k in lowered for k in ("address", "manzil", "adres")):
        return "Toshkent viloyati, Qibray tumani, Navoiy ko'chasi 12-uy"
    if any(k in lowered for k in ("bank", "bank_name")):
        return 'ATB "Agrobank" Qibray filiali'
    if any(k in lowered for k in ("mfo", "bank_code", "bik")):
        return "00456"
    if any(k in lowered for k in ("account", "hisob", "schet", "rs")):
        return "20208000100000001234"
    if any(k in lowered for k in ("doc_num", "number", "num", "raqam", "nomer", "contract")):
        return "№ AG-2026/88"
    if any(k in lowered for k in ("crop", "ekin")):
        return "Paxta (G'o'za)"

    return f"Namuna: {key}"


def extract_template_variables(docx_path: str) -> set[str]:
    """
    Extracts undeclared Jinja2 and dollar-brace variables from a .docx template.
    Uses docxtpl inspection and regex fallback across paragraphs and tables.
    """
    variables: set[str] = set()

    if not os.path.exists(docx_path):
        return variables

    # 1. docxtpl Jinja2 introspection
    try:
        tpl = DocxTemplate(docx_path)
        undeclared = tpl.get_undeclared_template_variables()
        if undeclared:
            variables.update(undeclared)
    except Exception as exc:
        logger.debug("docxtpl introspection notice: %s", exc)

    # 2. Regex scan for both {{ var }} and ${var} patterns
    try:
        doc = PythonDocx(docx_path)
        pattern = re.compile(r"(?:\{\{|\$\{)\s*([a-zA-Z0-9_\.]+)\s*(?:\}\}|\})")

        for p in doc.paragraphs:
            for match in pattern.findall(p.text):
                clean_name = match.split(".")[0]
                variables.add(clean_name)

        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    for match in pattern.findall(cell.text):
                        clean_name = match.split(".")[0]
                        variables.add(clean_name)
    except Exception as exc:
        logger.debug("regex docx scan notice: %s", exc)

    return variables - RESERVED_VARIABLES


def build_dynamic_mock_context(docx_path: str) -> dict[str, Any]:
    """
    Builds a key-value dictionary with smart mock values for a template.
    If no variables are found, provides sensible default mock keys.
    """
    variables = extract_template_variables(docx_path)
    context: dict[str, Any] = {}

    for var in sorted(variables):
        context[var] = generate_mock_value_for_key(var)

    if not context:
        context = {
            "document_number": "№ 001-DEMO",
            "contract_date": datetime.now().strftime("%d.%m.%Y"),
            "farmer_name": '"OLTIN VODI ZAMIN" Fermer Xo\'jaligi',
            "farmer_tin": "301234567",
            "farmer_director": "Karimov Alisher Bahromovich",
            "company_name": '"AGRO BARKAMOL KLASTER" MCHJ',
            "company_tin": "208765432",
            "region": "Toshkent viloyati",
            "district": "Qibray tumani",
            "total_amount": "150 000 000 UZS",
        }

    return context
