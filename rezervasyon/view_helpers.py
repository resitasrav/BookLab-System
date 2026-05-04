# TURKCE ARAMA: ortak view yardimcilari, dogrulama kodu, cakisma kontrolu

import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.html import strip_tags

from .models import Randevu

MAX_RANDEVU_SAATI = getattr(settings, "MAX_RANDEVU_SAATI", 24)
IPTAL_MIN_SURE_SAAT = getattr(settings, "IPTAL_MIN_SURE_SAAT", 0)
EMAIL_DOGRULAMA_KOD_SURESI_DAKIKA = getattr(settings, "EMAIL_DOGRULAMA_KOD_SURESI_DAKIKA", 10)


def dogrulama_kodu_uret():
    """TURKCE ARAMA: e-posta dogrulama kodu uretimi."""
    return f"{secrets.randbelow(900000) + 100000}"


def kod_suresi_doldu_mu(olusturma_str):
    """TURKCE ARAMA: dogrulama kodu sure kontrolu."""
    olusturma_tarihi = parse_datetime(olusturma_str) if olusturma_str else None
    if not olusturma_tarihi:
        return True
    return timezone.now() > olusturma_tarihi + timedelta(minutes=EMAIL_DOGRULAMA_KOD_SURESI_DAKIKA)


def dogrulama_maili_gonder(email, kod, isim=""):
    """TURKCE ARAMA: kayit ve email degisikligi dogrulama maili - HTML destekli."""
    ad = isim or "BookLab kullanıcısı"
    
    # HTML şablonu render et
    html_content = render_to_string(
        "emails/email_dogrulama.html",
        {
            "ad": ad,
            "kod": kod,
            "sure_dakika": EMAIL_DOGRULAMA_KOD_SURESI_DAKIKA,
        }
    )
    
    # Düz metin versiyonu oluştur
    text_content = strip_tags(html_content)
    
    # Email nesnesini oluştur
    email_obj = EmailMultiAlternatives(
        subject="BookLab - E-posta Doğrulama Kodu",
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[email],
    )
    
    # HTML versiyonunu ekle
    email_obj.attach_alternative(html_content, "text/html")
    email_obj.send(fail_silently=False)


def check_overlap(cihaz, tarih, baslangic, bitis, exclude_id=None):
    """TURKCE ARAMA: randevu cakisma kontrolu."""
    qs = Randevu.objects.filter(
        cihaz=cihaz,
        tarih=tarih,
        durum__in=[Randevu.ONAY_BEKLENIYOR, Randevu.ONAYLANDI, Randevu.GELDI],
        baslangic_saati__lt=bitis,
        bitis_saati__gt=baslangic,
    )
    if exclude_id:
        qs = qs.exclude(pk=exclude_id)
    return qs.exists()
