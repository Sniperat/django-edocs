import json
import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse
from edocs.models import Document, DocumentSigner
from tests.models import SampleContract

User = get_user_model()


@pytest.fixture
def api_setup(db):
    user1 = User.objects.create_user(username="api_user1", password="password1")
    user2 = User.objects.create_user(username="api_user2", password="password2")

    doc = Document.objects.create(
        name="API Test Document",
        code="contract_cotton",
        security_code="7788",
        file_hash="dummy_hash_value_1234567890",
    )
    s1 = DocumentSigner.objects.create(document=doc, signer=user1, order=0, last_one=False)
    s2 = DocumentSigner.objects.create(document=doc, signer=user2, order=1, last_one=True)

    contract = SampleContract.objects.create(title="Cotton Contract", creator=user1, document=doc)

    return {
        "user1": user1,
        "user2": user2,
        "doc": doc,
        "s1": s1,
        "s2": s2,
        "contract": contract,
    }


@pytest.mark.django_db
def test_document_challenge_api(api_setup):
    client = Client()
    client.force_login(api_setup["user1"])

    url = reverse("edocs:challenge", kwargs={"guid": api_setup["doc"].guid})
    res = client.get(url)

    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["security_code"] == "7788"
    assert data["can_sign"] is True
    assert data["can_cancel"] is True


@pytest.mark.django_db
def test_document_sign_api(api_setup):
    client = Client()
    client.force_login(api_setup["user1"])

    url = reverse("edocs:sign", kwargs={"guid": api_setup["doc"].guid})
    payload = {
        "pkcs7": "MOCK_PKCS7_PAYLOAD",
        "certificate_info": {
            "CN": "Aliyev Vali",
            "TIN": "301234567",
        },
    }
    res = client.post(url, data=json.dumps(payload), content_type="application/json")

    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["is_signed"] is False  # 1st signer out of 2

    api_setup["doc"].refresh_from_db()
    assert api_setup["doc"].signers_count == 1


@pytest.mark.django_db
def test_document_cancel_and_reject_api(api_setup):
    client = Client()
    client.force_login(api_setup["user1"])

    # Cancel
    cancel_url = reverse("edocs:cancel", kwargs={"guid": api_setup["doc"].guid})
    res_cancel = client.post(cancel_url, data=json.dumps({"note": "Bekor qilindi"}), content_type="application/json")
    assert res_cancel.status_code == 200

    api_setup["contract"].refresh_from_db()
    assert api_setup["contract"].status == "cancelled"


@pytest.mark.django_db
def test_document_public_verify_api(api_setup):
    client = Client()
    verify_url = reverse("edocs:verify", kwargs={"guid": api_setup["doc"].guid})

    # JSON response
    res = client.get(verify_url, HTTP_ACCEPT="application/json")
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["document"]["guid"] == str(api_setup["doc"].guid)

    # HTML response
    res_html = client.get(verify_url, HTTP_ACCEPT="text/html")
    assert res_html.status_code == 200
    assert "text/html" in res_html["Content-Type"]
