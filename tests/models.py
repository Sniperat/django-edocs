from django.db import models
from edocs.models.base import AbstractDocumentBase


class SampleContract(AbstractDocumentBase):
    """Host business model to verify AbstractDocumentBase attachment."""
    title = models.CharField(max_length=200, default="Demo Contract")
    creator = models.ForeignKey("auth.User", on_delete=models.CASCADE, related_name="created_contracts")

    def __str__(self):
        return self.title
