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

# TURKCE ARAMA: takvim, fullcalendar, event api, cihaz takvimi
@login_required
def genel_takvim(request):
    """Tüm laboratuvarların ortak takvimi"""
    cihazlar_sorgu = Cihaz.objects.filter(aktif_mi=True).values('id', 'isim', 'lab__isim')
    cihazlar = [{'id': c['id'], 'isim': f"{c['lab__isim']} ➝ {c['isim']}"} for c in cihazlar_sorgu]
    cihazlar_json = json.dumps(cihazlar, cls=DjangoJSONEncoder)
    return render(request, "genel_takvim.html", {"cihazlar_json": cihazlar_json})


@login_required
def tum_events_api(request):
    """
    Genel Takvim API: Geçmiş sonuçlananlar ve Gelecek planlılar.
    Çift ikon ve taşma sorununu önlemek için sadeleştirilmiştir.
    """
    color_map = {
        Randevu.ONAYLANDI: "#28a745", Randevu.ONAY_BEKLENIYOR: "#ffc107",
        Randevu.GELDI: "#0d6efd", Randevu.GELMEDI: "#6c757d", Randevu.REDDEDILDI: "#dc3545",
    }

    # Durum filtresi DB tarafında; cihaz/lab/kullanici JOIN ile tek sorguda (N+1 önlenir).
    randevular = (
        Randevu.objects
        .filter(durum__in=[Randevu.ONAY_BEKLENIYOR, Randevu.ONAYLANDI, Randevu.GELDI])
        .select_related("cihaz__lab", "kullanici")
    )

    events = [
        {
            'id': r.id,
            'title': f"{r.cihaz.isim} • {r.baslangic_saati.strftime('%H:%M')}-{r.bitis_saati.strftime('%H:%M')}",
            'start': f"{r.tarih.isoformat()}T{r.baslangic_saati.strftime('%H:%M:%S')}",
            'end': f"{r.tarih.isoformat()}T{r.bitis_saati.strftime('%H:%M:%S')}",
            'color': color_map.get(r.durum, "#3788d8"),
            'extendedProps': {
                'lab_adi': r.cihaz.lab.isim,
                'kullanici': r.kullanici.username,
                'durum': r.get_durum_display(),
            },
        }
        for r in randevular
    ]
    return JsonResponse(events, safe=False)


@login_required
def lab_takvim(request, lab_id):
    lab = get_object_or_404(Laboratuvar, id=lab_id)
    cihazlar = list(Cihaz.objects.filter(lab=lab, aktif_mi=True).values('id', 'isim'))
    return render(request, "lab_takvim.html", {"lab": lab, "cihazlar_json": json.dumps(cihazlar, cls=DjangoJSONEncoder)})


@login_required
def lab_events_api(request, lab_id):
    # Durum filtresi DB tarafında; cihaz/kullanici JOIN ile tek sorguda (N+1 önlenir).
    randevular = (
        Randevu.objects
        .filter(
            cihaz__lab_id=lab_id,
            durum__in=[Randevu.ONAY_BEKLENIYOR, Randevu.ONAYLANDI, Randevu.GELDI],
        )
        .select_related("cihaz", "kullanici")
    )
    events = [
        {
            'title': f"{r.cihaz.isim} • {r.baslangic_saati.strftime('%H:%M')}-{r.bitis_saati.strftime('%H:%M')}",
            'start': f"{r.tarih.isoformat()}T{r.baslangic_saati.strftime('%H:%M:%S')}",
            'end': f"{r.tarih.isoformat()}T{r.bitis_saati.strftime('%H:%M:%S')}",
            'color': "#28a745" if r.durum == Randevu.ONAYLANDI else "#ffc107",
            'extendedProps': {'kullanici': r.kullanici.username, 'durum': r.get_durum_display()},
        }
        for r in randevular
    ]
    return JsonResponse(events, safe=False)
