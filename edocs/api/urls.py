from django.urls import path
from edocs.api.views import (
    DocumentCancelAPIView,
    DocumentChallengeAPIView,
    DocumentPreviewAPIView,
    DocumentPublicVerifyAPIView,
    DocumentRejectAPIView,
    DocumentSignAPIView,
)

app_name = "edocs"

urlpatterns = [
    path("<uuid:guid>/challenge/", DocumentChallengeAPIView.as_view(), name="challenge"),
    path("<uuid:guid>/sign/", DocumentSignAPIView.as_view(), name="sign"),
    path("<uuid:guid>/reject/", DocumentRejectAPIView.as_view(), name="reject"),
    path("<uuid:guid>/cancel/", DocumentCancelAPIView.as_view(), name="cancel"),
    path("<uuid:guid>/preview/", DocumentPreviewAPIView.as_view(), name="preview"),
    path("verify/<uuid:guid>/", DocumentPublicVerifyAPIView.as_view(), name="verify"),
]
