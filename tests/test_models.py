import pytest
from django.contrib.auth import get_user_model
from edocs.models import Document, DocumentSigner, DocumentTemplate
from edocs.services.simulation import simulate_mock_signing
from tests.models import SampleContract

User = get_user_model()


@pytest.mark.django_db
def test_document_creation_and_security_code():
    doc = Document.objects.create(name="Shartnoma №10")
    assert doc.guid is not None
    assert len(doc.security_code) == 4
    assert doc.security_code.isdigit()
    assert doc.is_signed is False
    assert doc.signers_count == 0


@pytest.mark.django_db
def test_document_signers_queue_ordering():
    user1 = User.objects.create_user(username="signer1", password="password1")
    user2 = User.objects.create_user(username="signer2", password="password2")

    doc = Document.objects.create(name="Ko'p tomonlama hujjat")
    s1 = DocumentSigner.objects.create(document=doc, signer=user1, order=0, last_one=False)
    s2 = DocumentSigner.objects.create(document=doc, signer=user2, order=1, last_one=True)

    assert doc.get_current_signer() == s1
    assert doc.is_current_signer(user1) is True
    assert doc.is_current_signer(user2) is False

    # Simulate signing by first signer
    doc.mark_signed_step(signer_obj=user1, pkcs7="mock_pkcs7_1", cert_info={"name": "Signer 1"})
    assert doc.is_signed is False
    assert doc.signers_count == 1
    assert doc.get_current_signer() == s2
    assert doc.is_current_signer(user2) is True

    # Simulate signing by second (last) signer
    doc.mark_signed_step(signer_obj=user2, pkcs7="mock_pkcs7_2", cert_info={"name": "Signer 2"})
    assert doc.is_signed is True
    assert doc.signers_count == 2
    assert doc.get_current_signer() is None


@pytest.mark.django_db
def test_abstract_document_base_cancel_and_reject():
    creator = User.objects.create_user(username="creator", password="pwd")
    reviewer = User.objects.create_user(username="reviewer", password="pwd")
    stranger = User.objects.create_user(username="stranger", password="pwd")

    doc = Document.objects.create(name="Oldi-sotdi shartnomasi")
    DocumentSigner.objects.create(document=doc, signer=creator, order=0, last_one=False)
    DocumentSigner.objects.create(document=doc, signer=reviewer, order=1, last_one=True)

    contract = SampleContract.objects.create(title="Paxta xarid shartnomasi", creator=creator, document=doc)

    # Permissions check
    assert contract.can_cancel(creator) is True
    assert contract.can_cancel(reviewer) is False
    assert contract.can_cancel(stranger) is False

    assert contract.can_reject(creator) is True   # creator is current pending signer
    assert contract.can_reject(reviewer) is False  # not reviewer's turn yet

    # Reject contract
    contract.reject_me(creator, note="Shartlarda noaniqlik bor.")
    assert contract.status == "rejected"
    assert contract.rejected is True
    assert contract.who_rejected == creator
    assert contract.note == "Shartlarda noaniqlik bor."
