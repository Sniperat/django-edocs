from django.dispatch import Signal

# Sent when a new document is generated
document_created = Signal()

# Sent when an individual signer places an E-IMZO signature
document_signer_signed = Signal()

# Sent when all required signers have signed (document.is_signed becomes True)
document_fully_signed = Signal()

# Sent when a document is rejected by a signer in queue
document_rejected = Signal()

# Sent when a document is cancelled by its owner/creator
document_cancelled = Signal()
