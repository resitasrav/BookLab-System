# Bu dosya views.py dosyasindan ayrildi.
# TURKCE ARAMA ANAHTARLARI: view, sayfa, islem, BookLab

import json
import logging
from datetime import datetime, timedelta
import json as json_lib

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.html import strip_tags
from django.utils.http import urlsafe_base64_encode, url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import (
    KullaniciGuncellemeFormu,
    ProfilGuncellemeFormu,
    ArizaFormu,
    KayitFormu,
    EmailOrUsernameAuthenticationForm,
)
from .models import Laboratuvar, Cihaz, Randevu, Profil, Duyuru, Ariza
from .utils import render_to_pdf
from .view_helpers import (
    EMAIL_DOGRULAMA_KOD_SURESI_DAKIKA,
    IPTAL_MIN_SURE_SAAT,
    dogrulama_kodu_uret,
    kod_suresi_doldu_mu,
    dogrulama_maili_gonder,
    check_overlap,
)

logger = logging.getLogger(__name__)

# TURKCE ARAMA: ana sayfa, laboratuvar detay, duyuru
def anasayfa(request):
    labs = Laboratuvar.objects.all()
    duyurular = Duyuru.objects.filter(aktif_mi=True).order_by("-tarih")
    duyurular = Duyuru.objects.filter(aktif_mi=True).order_by("-tarih")
    
    context = {
        "labs": labs, 
        "duyurular": duyurular,
        "bugun": timezone.now().date() # tarih bazlı filtreleme 
    }

    if request.user.is_authenticated:
        aktif_sorgu = Randevu.objects.filter(
            kullanici=request.user,
            tarih__gte=timezone.now().date(),
            durum__in=[Randevu.ONAYLANDI, Randevu.ONAY_BEKLENIYOR]
        )
        context["aktif_randevu_sayisi"] = aktif_sorgu.count()
        context["siradaki_randevu"] = aktif_sorgu.order_by("tarih", "baslangic_saati").first()

    return render(request, "index.html", context)

@login_required
def lab_detay(request, lab_id):
    secilen_lab = get_object_or_404(Laboratuvar, id=lab_id)
    cihaz_listesi = Cihaz.objects.filter(lab=secilen_lab)
    return render(request, "lab_detay.html", {"lab": secilen_lab, "cihazlar": cihaz_listesi})


# ========================================================
# İSTATİSTİKLER - MODÜLER VE KOLAYCA KALDIRILAB İLİR
# ========================================================
def _istatistikler_verisi_al():
    """
    İstatistikler verisini merkezi olarak hazırlar.
    Kolayca kaldırılabilir: bu fonksiyon + URL + template
    """
    bugun = timezone.now().date()
    ay_baslangici = timezone.now().replace(day=1).date()
    
    # Genel İstatistikler
    toplam_lab = Laboratuvar.objects.count()
    toplam_cihaz = Cihaz.objects.count()
    aktif_cihaz = Cihaz.objects.filter(aktif_mi=True).count()
    ariza_cihaz = Cihaz.objects.filter(aktif_mi=False).count()
    
    # Kullanıcı İstatistikleri
    toplam_kullanici = User.objects.count()
    aktif_kullanici = Profil.objects.filter(status='aktif_kullanici').count()
    onay_bekleyen = Profil.objects.filter(status='pasif_kullanici').count()
    
    # Randevu İstatistikleri
    toplam_randevu = Randevu.objects.count()
    now = timezone.now()
    ay_randevusu = Randevu.objects.filter(
        tarih__year=now.year,
        tarih__month=now.month,
    ).count()
    onaylanan_randevu = Randevu.objects.filter(durum=Randevu.ONAYLANDI).count()
    onay_bekleme_randevu = Randevu.objects.filter(durum=Randevu.ONAY_BEKLENIYOR).count()
    tamamlanan_randevu = Randevu.objects.filter(durum=Randevu.GELDI).count()
    iptal_randevu = Randevu.objects.filter(durum=Randevu.IPTAL).count()
    
    # Arıza İstatistikleri
    toplam_ariza = Ariza.objects.count()
    acik_ariza = Ariza.objects.filter(cozuldu_mu=False).count()
    cozulen_ariza = Ariza.objects.filter(cozuldu_mu=True).count()
    
    return {
        'lab': {
            'toplam': toplam_lab,
            'toplam_cihaz': toplam_cihaz,
            'aktif_cihaz': aktif_cihaz,
            'ariza_cihaz': ariza_cihaz,
        },
        'kullanici': {
            'toplam': toplam_kullanici,
            'aktif': aktif_kullanici,
            'onay_bekleyen': onay_bekleyen,
        },
        'randevu': {
            'toplam': toplam_randevu,
            'bu_ay': ay_randevusu,
            'onaylanan': onaylanan_randevu,
            'onay_bekleme': onay_bekleme_randevu,
            'tamamlanan': tamamlanan_randevu,
            'iptal': iptal_randevu,
        },
        'ariza': {
            'toplam': toplam_ariza,
            'acik': acik_ariza,
            'cozulen': cozulen_ariza,
        }
    }

@login_required
def istatistikler(request):
    """
    Herkese açık istatistikler sayfası.
    Admin ise detaylı tabloları + grafikleri görür, diğerleri genel istatistikleri görür.
    """
    veriler = _istatistikler_verisi_al()
    r = veriler['randevu']

    # Randevu durum chart'ı için JSON (herkese açık)
    randevu_chart_json = json_lib.dumps({
        'labels': ['Onaylanan', 'Onay Bekleyen', 'Tamamlanan', 'İptal'],
        'data': [r['onaylanan'], r['onay_bekleme'], r['tamamlanan'], r['iptal']],
        'colors': ['#198754', '#ffc107', '#0dcaf0', '#dc3545'],
    })

    context = {
        "veriler": veriler,
        "is_staff": request.user.is_staff,
        "randevu_chart_json": randevu_chart_json,
    }

    # Admin için detaylı veriler ve ek grafikler
    if request.user.is_staff:
        lab_randevular = list(
            Randevu.objects.values('cihaz__lab__isim')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        cihaz_randevular = list(
            Randevu.objects.values('cihaz__isim')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )
        kullanicilar = list(Profil.objects.values('status').annotate(count=Count('id')))
        en_aktif_kullanicilar = (
            User.objects.annotate(randevu_count=Count('randevu'))
            .select_related('profil')
            .order_by('-randevu_count')[:10]
        )

        veriler['admin'] = {
            'lab_randevular': lab_randevular,
            'cihaz_randevular': cihaz_randevular,
            'kullanicilar': kullanicilar,
            'en_aktif_kullanicilar': en_aktif_kullanicilar,
        }

        # Lab dağılımı chart JSON
        context['lab_chart_json'] = json_lib.dumps({
            'labels': [item['cihaz__lab__isim'] or 'Bilinmeyen' for item in lab_randevular],
            'data': [item['count'] for item in lab_randevular],
        })

        # Cihaz top 10 chart JSON
        context['cihaz_chart_json'] = json_lib.dumps({
            'labels': [item['cihaz__isim'] or 'Bilinmeyen' for item in cihaz_randevular],
            'data': [item['count'] for item in cihaz_randevular],
        })

    return render(request, "istatistikler.html", context)
