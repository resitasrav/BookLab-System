# TURKCE ARAMA: admin giris dosyasi, admin modulleri yukleme

from django.contrib import admin

admin.site.site_header = "BookLab Yonetim Paneli"
admin.site.site_title = "BookLab Admin Portal"
admin.site.index_title = "Sistem Kontrol Merkezine Hos Geldiniz"

# Model admin siniflari konu bazli dosyalarda tutulur.
from . import admin_laboratuvar  # noqa: F401
from . import admin_randevu  # noqa: F401
from . import admin_ariza_duyuru  # noqa: F401
from . import admin_kullanici  # noqa: F401
