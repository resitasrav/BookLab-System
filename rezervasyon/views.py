"""BookLab view uyumluluk kapisi.

TURKCE ARAMA: views ana giris, eski URL uyumlulugu.
Asil view kodlari konu bazli modullere ayrildi. `lab_sistemi.urls` halen
`from rezervasyon import views` kullandigi icin bu dosya public isimleri yeniden
aktarir.
"""

from .views_auth import CustomLoginView, kayit, email_dogrulama, sifre_sifirla_talep, kod_tekrar_gonder
from .views_public import anasayfa, lab_detay
from .views_calendar import genel_takvim, tum_events_api, lab_takvim, lab_events_api
from .views_randevu import randevu_al, randevularim, randevu_pdf_indir, randevu_iptal
from .views_profile import profil_duzenle, email_degisim_dogrulama
from .views_management import (
    onay_bekleyen_sayisi,
    egitmen_paneli,
    durum_guncelle,
    ariza_bildir,
    kullanici_listesi,
    arizali_cihaz_listesi,
    cihaz_durum_degistir,
    tum_randevular,
    toplu_islem,
    toplu_onay_ajax,
    ariza_bildir_genel,
)
