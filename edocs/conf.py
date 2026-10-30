from django.conf import settings


class AppSettings:
    """
    Centralized configuration helper for django-edocs.
    Allows overriding defaults via django.conf.settings.
    """

    PREFIX = "EDOCS_"

    DEFAULTS = {
        "VERIFY_URL": "",
        "VERIFY_FRONTEND_URL": "",
        "LIBREOFFICE_PATH": "libreoffice",
        "ENABLE_LOCAL_FALLBACK": None,  # Defaults to settings.DEBUG if not set
        "SIGNER_MODEL": getattr(settings, "AUTH_USER_MODEL", "auth.User"),
        "DOCX_UPLOAD_TO": "edocs/docx/",
        "PDF_UPLOAD_TO": "edocs/pdf/",
        "TEMPLATES_UPLOAD_TO": "edocs/templates/",
    }

    def __getattr__(self, name):
        if name not in self.DEFAULTS:
            raise AttributeError(f"'AppSettings' object has no setting '{name}'")

        setting_name = f"{self.PREFIX}{name}"
        value = getattr(settings, setting_name, None)

        if value is None and name == "VERIFY_URL":
            value = getattr(settings, "EIMZO_VERIFY_URL", None)

        if value is None:
            default = self.DEFAULTS[name]
            if name == "ENABLE_LOCAL_FALLBACK" and default is None:
                return getattr(settings, "DEBUG", False)
            return default

        return value


edocs_settings = AppSettings()
