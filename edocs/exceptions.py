class EDocsException(Exception):
    """Base exception for django-edocs."""
    pass


class DocumentGenerationError(EDocsException):
    """Raised when document rendering or compilation fails."""
    pass


class EImzoVerificationError(EDocsException):
    """Raised when E-IMZO PKCS#7 signature verification fails."""
    pass


class SigningOrderError(EDocsException):
    """Raised when an out-of-order signature is attempted."""
    pass
