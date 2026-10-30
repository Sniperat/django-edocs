from edocs.services.mock_extractor import (
    RESERVED_VARIABLES,
    build_dynamic_mock_context,
    generate_mock_value_for_key,
)


def test_mock_value_heuristics():
    date_val = generate_mock_value_for_key("contract_date")
    assert "." in date_val

    time_val = generate_mock_value_for_key("created_time")
    assert ":" in time_val

    tin_val = generate_mock_value_for_key("stir")
    assert tin_val == "301234567"

    pinfl_val = generate_mock_value_for_key("jshshir")
    assert len(pinfl_val) == 14

    amount_val = generate_mock_value_for_key("total_amount")
    assert "150 000 000" in amount_val

    company_val = generate_mock_value_for_key("company_name")
    assert "MCHJ" in company_val

    farmer_val = generate_mock_value_for_key("farmer_title")
    assert "Fermer Xo'jaligi" in farmer_val

    fallback_val = generate_mock_value_for_key("arbitrary_field")
    assert "Namuna: arbitrary_field" in fallback_val


def test_reserved_variables_filtering():
    assert "qrcode" in RESERVED_VARIABLES
    assert "guid" in RESERVED_VARIABLES
    assert "security_code" in RESERVED_VARIABLES
    assert "signers" in RESERVED_VARIABLES
    assert "imzolar" in RESERVED_VARIABLES


def test_build_dynamic_mock_context_fallback():
    ctx = build_dynamic_mock_context("/non/existent/path.docx")
    assert isinstance(ctx, dict)
    assert "document_number" in ctx
    assert "farmer_name" in ctx
    assert "total_amount" in ctx
