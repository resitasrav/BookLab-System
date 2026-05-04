# Bu dosya views.py dosyasindan ayrildi.
# TURKCE ARAMA ANAHTARLARI: view, sayfa, islem, BookLab

import json
import logging
from datetime import datetime, timedelta

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
