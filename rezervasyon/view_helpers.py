# TURKCE ARAMA: ortak view yardimcilari, dogrulama kodu, cakisma kontrolu

import secrets
from datetime import datetime, timedelta

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

# İŞ KURALI: Randevu bitiminden bu kadar saat sonra hâlâ "onaylandı" durumunda
# kalan (iptal/reddedilmemiş ve "gelmedi" işaretlenmemiş) randevular otomatik
# olarak "geldi" sayılır.
OTOMATIK_GELDI_SURESI_SAAT = getattr(settings, "OTOMATIK_GELDI_SURESI_SAAT", 48)
# Randevu saatlerinin yuvarlanacağı dilim (dakika). 10 => 09:00, 09:10, 09:20...
SLOT_DAKIKA = getattr(settings, "SLOT_DAKIKA", 10)


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
    """TURKCE ARAMA: randevu cakisma kontrolu.

    NOT: Cakisma SADECE cihaz bazlidir. Ayni kullanici ayni anda farkli
    cihazlara randevu alabilir; yalniz ayni cihaz icin tek randevu kuralidir.
    """
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


def saat_yuvarla(dt, slot_dakika=SLOT_DAKIKA):
    """TURKCE ARAMA: saat yuvarlama, 10 dakikalik dilim.

    Verilen datetime/time nesnesini en yakin `slot_dakika` katina yuvarlar.
    Ornek: 09:07 -> 09:10, 09:04 -> 09:00, 09:58 -> 10:00.
    """
    dakika = dt.minute
    yuvarlanmis = round(dakika / slot_dakika) * slot_dakika
    if yuvarlanmis >= 60:
        return (dt + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    return dt.replace(minute=yuvarlanmis, second=0, microsecond=0)


def otomatik_geldi_isaretle():
    """TURKCE ARAMA: otomatik geldi, 48 saat kurali.

    Bitiminden `OTOMATIK_GELDI_SURESI_SAAT` saatten fazla gecmis ve hala
    "onaylandi" durumunda kalan (iptal/reddedilmemis ve "gelmedi"
    isaretlenmemis) randevulari otomatik olarak "geldi" yapar.

    Yonetici daha sonra istedigi zaman "gelmedi"ye cevirebilir; bu fonksiyon
    yalnizca "onaylandi" durumundakilere dokunur, idempotenttir.

    Donus: guncellenen randevu sayisi (int).
    """
    simdi = timezone.now()
    sinir = simdi - timedelta(hours=OTOMATIK_GELDI_SURESI_SAAT)

    # Kaba on filtre: en gec sinir tarihinde ya da oncesinde olan randevular.
    # (Gun ici saat kontrolu Python tarafinda kesinlestirilir.)
    adaylar = Randevu.objects.filter(
        durum=Randevu.ONAYLANDI,
        tarih__lte=sinir.date(),
    ).only("id", "tarih", "bitis_saati")

    guncellenecek_ids = []
    for r in adaylar:
        bitis_dt = datetime.combine(r.tarih, r.bitis_saati)
        if timezone.is_naive(bitis_dt):
            bitis_dt = timezone.make_aware(bitis_dt)
        if bitis_dt + timedelta(hours=OTOMATIK_GELDI_SURESI_SAAT) <= simdi:
            guncellenecek_ids.append(r.id)

    if not guncellenecek_ids:
        return 0
    return Randevu.objects.filter(id__in=guncellenecek_ids).update(durum=Randevu.GELDI)
