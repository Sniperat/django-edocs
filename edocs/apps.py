from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class EdocsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "edocs"
    verbose_name = _("Elektron Hujjatlar (EDocs)")

    def ready(self):
        # Register checks or signal receivers if necessary
        pass
