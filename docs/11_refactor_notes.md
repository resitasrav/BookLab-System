# Refactor Notlari

TURKCE ARAMA: eksikler, refactor raporu, buyuk dosya bolme, sonraki isler

## Yapilan Bolme

- `rezervasyon/views.py` uyumluluk kapisi olarak birakildi.
- View kodlari konu bazli dosyalara ayrildi:
  - `views_auth.py`: giris, kayit, e-posta dogrulama, sifre sifirlama
  - `views_public.py`: ana sayfa ve laboratuvar detay
  - `views_calendar.py`: takvim ekranlari ve event API'leri
  - `views_randevu.py`: randevu alma, iptal, PDF ve kullanici randevulari
  - `views_profile.py`: profil ve e-posta degisikligi dogrulama
  - `views_management.py`: yonetim paneli, ariza ve toplu islemler
  - `view_helpers.py`: ortak dogrulama ve cakisma yardimcilari
- `rezervasyon/admin.py` icindeki global admin aksiyonlari, mail mixin'i ve guvenli redirect yardimcilari `admin_helpers.py` dosyasina tasindi.
- Model admin siniflari da konu bazli dosyalara ayrildi:
  - `admin_laboratuvar.py`: laboratuvar ve cihaz yonetimi
  - `admin_randevu.py`: randevu listesi, onay ve yoklama islemleri
  - `admin_kullanici.py`: kullanici, profil ve onay bekleyen/aktif kullanici ekranlari
  - `admin_ariza_duyuru.py`: ariza ve duyuru yonetimi
- Sayfa ici `<style>` bloklari `static/css/pages/` altina tasindi. `base.html` artik `extra_css` blogu ile sayfa bazli CSS yukluyor.
- `base.html` icindeki ana layout CSS'i `static/css/booklab-base.css` dosyasina tasindi.

## Not Alinan Eksikler

- Template dosyalarinda hala bazi `style=""` inline attribute'lari var. Bunlar sonraki UI temizlik turunda class isimlerine donusturulebilir.
- `requirements.txt` MSYS Python ortaminda `cryptography` derlemesine takiliyor. Windows icin python.org Python + temiz `.venv` daha saglikli.
- Django `check` ve testler, bagimlilik kurulumu tamamlanmadan calistirilamiyor.
